"""CLI for kodx code command."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from llmproc import LLMProgram
from llmproc.cli.log_utils import get_logger, log_program_info
from llmproc.cli.run import run_with_prompt

from .config import get_command_config
from .git_utils import (
    GitError,
    fetch_branch,
    generate_branch_name,
    get_current_commit,
    get_repo_root,
    has_new_commits,
    is_git_repo,
    resolve_ref,
)
from .kodx_callback import KodxCallbackHandler
from .models import DockerConfig
from .models_code import CodeArgs
from .prompt_utils import PromptResolutionError, resolve_prompt
from .tools import DockerCodexTools
from .workspace import (
    WorkspaceError,
    cleanup_workspace,
    copy_to_container,
    create_temporary_workspace,
    export_from_container,
    setup_clean_checkout,
    setup_dirty_copy,
    setup_git_environment,
)

DEFAULT_TIMEOUT = 20 * 60  # 20 minutes


def get_builtin_program_path(program_name: str) -> Path:
    """Get the path to a built-in program file.

    Args:
        program_name: Name of the program (ask, code, etc.)

    Returns:
        Path to the program file

    Note: This function is deprecated. Use config.get_program_path() instead.
    """
    # Get the directory where this module is located
    module_dir = Path(__file__).parent
    program_path = module_dir / "programs" / f"{program_name}.yaml"

    if not program_path.exists():
        raise FileNotFoundError(f"Built-in program not found: {program_path}")

    return program_path


async def execute_code(args: CodeArgs):
    """Execute kodx code command.

    Args:
        args: Validated code command arguments
    """
    # Load configuration early to get program path and defaults
    config = get_command_config("code")

    # Apply config defaults where CLI args are None
    effective_cost_limit = args.cost_limit if args.cost_limit is not None else config.cost_limit
    effective_log_level = args.log_level if args.log_level != "INFO" else (config.log_level or "INFO")

    logger = get_logger(effective_log_level)
    workspace_dir = None

    try:
        # 1. Validate git repository
        if not is_git_repo():
            logger.error("kodx code requires a git repository")
            logger.error("Current directory is not in a git repository")
            sys.exit(1)

        repo_root = get_repo_root()
        logger.info(f"Working in git repository: {repo_root}")

        # 2. Load program (custom or configured code program)
        if args.program:
            code_program = LLMProgram.from_file(Path(args.program))
            logger.info(f"Loaded custom program from {args.program}")
        else:
            # Use configured program path
            code_program = LLMProgram.from_file(config.program_path)
            if config.program_path.name == "code.yaml" and config.program_path.parent.name == ".kodx":
                logger.info("Using local code program from .kodx/code.yaml")
            elif config.program_path.parent.name == "programs":
                logger.info("Using built-in code program")
            else:
                logger.info(f"Using configured code program from {config.program_path}")

        # 3. Determine base commit
        if args.base_ref:
            base_commit = resolve_ref(args.base_ref)
            logger.info(f"Branching from {args.base_ref} ({base_commit[:8]})")
        else:
            base_commit = get_current_commit()
            logger.info(f"Branching from current commit ({base_commit[:8]})")

        if args.dry_run:
            logger.info("Dry run mode - container actions will be skipped")
            logger.info(f"Prompt: {args.prompt}")
            logger.info(f"Base commit: {base_commit[:8]}")
            logger.info(f"Program: {args.program or 'builtin code'}")
            return

        # 4. Create temporary workspace
        workspace_dir = create_temporary_workspace()
        logger.info(f"Created temporary workspace: {workspace_dir}")

        # 5. Setup workspace based on dirty flag
        if args.dirty and not args.base_ref:
            # Include working directory changes
            workspace_repo_dir = setup_dirty_copy(workspace_dir, repo_root)
            logger.info("Copied repository with working directory changes")
        else:
            # Clean checkout of base commit
            workspace_repo_dir = setup_clean_checkout(workspace_dir, repo_root, base_commit)
            logger.info(f"Clean checkout of commit {base_commit[:8]}")

        # 6. Extract Docker configuration from program
        docker_dict = getattr(code_program, "docker", {})
        docker_config = DockerConfig(**docker_dict) if docker_dict else DockerConfig()

        # 7. Initialize container and copy workspace
        async with DockerCodexTools(container_image=docker_config.image) as docker_tools:
            logger.info(f"Initialized Docker container with image: {docker_config.image}")

            # Setup git environment for kodx code workflow
            await setup_git_environment(docker_tools)
            logger.info("Git environment configured")

            # Copy workspace to container
            await copy_to_container(docker_tools, workspace_repo_dir)
            logger.info("Copied workspace to container")

            # 8. Handle setup scripts from config
            if docker_config.setup_script:
                logger.info("Executing setup script from config")
                await docker_tools.execute_setup_script_content(
                    docker_config.setup_script, disable_network_after=docker_config.disable_network_after_setup
                )
                logger.info("Config setup script completed successfully")

            # 9. Register tools with program
            code_program.register_tools([docker_tools.feed_chars, docker_tools.create_new_shell])

            # 10. Start process
            process = await code_program.start()

            # 11. Use resolved prompt
            final_prompt = args.prompt

            # 12. Set up callbacks and run
            callback_handler = KodxCallbackHandler(logger, cost_limit=effective_cost_limit)
            process.add_callback(callback_handler)

            log_program_info(process, final_prompt, logger)

            effective_timeout = (
                args.timeout
                if args.timeout is not None
                else config.timeout
                if config.timeout is not None
                else DEFAULT_TIMEOUT
            )
            try:
                run_result = await asyncio.wait_for(
                    run_with_prompt(
                        process,
                        final_prompt,
                        "kodx code",
                        logger,
                        callback_handler,
                        args.quiet,
                        args.json_output,
                    ),
                    timeout=effective_timeout,
                )
            except TimeoutError:
                logger.error(f"Execution timed out after {effective_timeout} seconds")
                sys.exit(1)

            # 13. Export container changes
            export_dir = os.path.join(workspace_dir, "export")
            has_changes = export_from_container(docker_tools, export_dir)
            new_commit = has_new_commits(base_commit, export_dir) if has_changes else False

            if has_changes and new_commit:
                logger.info("Exported container changes")

                # 14. Generate branch name if not provided
                effective_branch = args.branch
                if not effective_branch:
                    # Use the last commit message from export to generate branch name
                    try:
                        # Try to get the last commit message from exported repo
                        result = subprocess.run(
                            ["git", "log", "-1", "--format=%s"],
                            cwd=export_dir,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        last_commit_msg = result.stdout.strip()
                        effective_branch = generate_branch_name(last_commit_msg)
                        logger.info(f"Generated branch name: {effective_branch}")
                    except subprocess.CalledProcessError:
                        # Fallback to request-based name
                        effective_branch = generate_branch_name(args.prompt)
                        logger.info(f"Fallback branch name: {effective_branch}")

                # 15. Fetch the branch into the main repository
                try:
                    fetch_branch(export_dir, "HEAD", effective_branch, repo_root)
                    logger.info(f"✅ Created branch '{effective_branch}' in main repository")
                    logger.info(f"Review changes: git checkout {effective_branch}")

                    # Handle JSON output if requested
                    if args.json_output or args.json_output_file:
                        _handle_json_output(run_result, process, args, effective_branch, logger)
                    else:
                        typer.echo("\n🎉 Feature implemented successfully!")
                        typer.echo(f"📋 Created branch: {effective_branch}")
                        typer.echo(f"🔍 Review changes: git checkout {effective_branch}")
                        typer.echo(f"🚀 Merge when ready: git checkout main && git merge {effective_branch}")

                except GitError as e:
                    logger.error(f"Failed to fetch branch: {e}")
                    logger.info(f"Export directory available at: {export_dir}")
                    sys.exit(1)
            else:
                if not has_changes:
                    logger.info("No changes were made in the container")
                else:
                    logger.info("Exported repository contains no new commit")
                if args.json_output or args.json_output_file:
                    _handle_json_output(run_result, process, args, None, logger)
                else:
                    typer.echo("ℹ️ No changes were made during implementation")

            await process.aclose()

    except GitError as e:
        logger.error(f"Git error: {e}")
        sys.exit(1)
    except WorkspaceError as e:
        logger.error(f"Workspace error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        # Cleanup workspace
        if workspace_dir:
            cleanup_workspace(workspace_dir)


def code(
    prompt_pos: Optional[str] = typer.Argument(None, help="Feature description or implementation request"),
    prompt_flag: Optional[str] = typer.Option(None, "--prompt", help="Feature description or implementation request"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="Read prompt from file"),
    base_ref: Optional[str] = typer.Option(None, help="Git reference to branch from (default: current HEAD)"),
    dirty: bool = typer.Option(False, help="Include working directory changes"),
    branch: Optional[str] = typer.Option(None, help="Custom branch name (default: auto-generated)"),
    program: Optional[str] = typer.Option(None, help="Custom LLM program to use"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    json_output_file: Optional[str] = typer.Option(None, help="Write JSON results to file"),
    quiet: bool = typer.Option(False, "-q", help="Suppress most output"),
    log_level: str = typer.Option("INFO", help="Set logging level"),
    cost_limit: Optional[float] = typer.Option(None, help="Stop execution when cost exceeds this limit in USD"),
    timeout: Optional[int] = typer.Option(None, help="Execution timeout in seconds"),
    dry_run: bool = typer.Option(False, help="Print actions without executing"),
):
    """Code in a container and export changes to a branch."""
    # Validate flag combination early
    if base_ref and dirty:
        typer.echo("❌ ERROR: --dirty cannot be used with --base-ref", err=True)
        typer.echo("   --dirty only applies when branching from current commit", err=True)
        raise typer.Exit(1)

    try:
        # Resolve prompt with explicit error handling
        final_prompt = resolve_prompt(prompt_pos, prompt_flag, prompt_file)

        # Build args object
        args = CodeArgs(
            prompt=final_prompt,
            prompt_file=prompt_file,
            json_output=json_output,
            json_output_file=json_output_file,
            base_ref=base_ref,
            dirty=dirty,
            branch=branch,
            program=program,
            quiet=quiet,
            log_level=log_level,
            cost_limit=cost_limit,
            timeout=timeout,
            dry_run=dry_run,
        )

        asyncio.run(execute_code(args))

    except PromptResolutionError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _handle_json_output(run_result, process, args: CodeArgs, branch_name: Optional[str], logger):
    """Handle JSON output for code command."""
    from .models import CommandResult

    # Create structured result
    result = CommandResult(
        command="code",
        prompt=args.prompt,
        api_calls=run_result.api_calls,
        usd_cost=getattr(run_result, "usd_cost", 0.0),
        last_message=process.get_last_message(),
        stderr=process.get_stderr_log(),
        stop_reason=getattr(run_result, "stop_reason", "end_turn"),
        branch_created=branch_name,
        implementation_summary=process.get_last_message(),  # For code command, the last message is the implementation
    )

    json_str = result.model_dump_json(indent=2)

    if args.json_output_file:
        with open(args.json_output_file, "w") as f:
            f.write(json_str)
        logger.info(f"JSON output written to {args.json_output_file}")
    else:
        typer.echo(json_str)


if __name__ == "__main__":
    code()
