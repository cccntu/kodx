"""CLI for kodx ask command."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from llmproc import LLMProgram
from llmproc.cli.log_utils import get_logger, log_program_info
from llmproc.cli.run import run_with_prompt

from .config import get_command_config
from .kodx_callback import KodxCallbackHandler
from .models import DockerConfig
from .models_ask import AskArgs
from .prompt_utils import PromptResolutionError, resolve_prompt
from .tools import DockerCodexTools
from .utils import docker_cp as _docker_cp
from .workspace import WorkspaceError, validate_files_exist

DEFAULT_TIMEOUT = 20 * 60  # 20 minutes


def get_builtin_program_path(program_name: str) -> Path:
    """Get the path to a built-in program file.

    Args:
        program_name: Name of the program (ask, code, etc.)

    Returns:
        Path to the program file
    """
    # Get the directory where this module is located
    module_dir = Path(__file__).parent
    program_path = module_dir / "programs" / f"{program_name}.yaml"

    if not program_path.exists():
        raise FileNotFoundError(f"Built-in program not found: {program_path}")

    return program_path


async def _copy_local_directory_to_container(docker_tools, local_dir, logger):
    """Copy local directory to container workspace."""
    # Create workspace directory in container
    await docker_tools.feed_chars("mkdir -p /workspace/repo")

    # Copy files using docker cp
    container_id = docker_tools.container_id
    if not container_id:
        raise RuntimeError("Container not initialized")

    # Copy all files from local directory
    try:
        _docker_cp(f"{local_dir}/.", f"{container_id}:/workspace/repo/", logger)
        logger.info(f"Successfully copied {local_dir} to container")

        # Set working directory to repo
        await docker_tools.feed_chars("cd /workspace/repo")

    except RuntimeError as e:
        logger.error(str(e))
        raise RuntimeError(f"Failed to copy directory to container: {e}")


async def execute_ask(args: AskArgs):
    """Execute kodx ask command.

    Args:
        args: Validated ask command arguments
    """
    # Load configuration early to get program path and defaults
    config = get_command_config("ask")

    # Apply config defaults where CLI args are None
    effective_cost_limit = args.cost_limit if args.cost_limit is not None else config.cost_limit
    effective_log_level = args.log_level if args.log_level != "INFO" else (config.log_level or "INFO")

    logger = get_logger(effective_log_level)

    try:
        # 1. Determine directory to analyze
        analysis_dir = args.repo_dir if args.repo_dir is not None else "."

        # 2. Validate that directory has files to analyze
        if not validate_files_exist(analysis_dir):
            logger.error(f"No files found to analyze in {os.path.abspath(analysis_dir)}")
            logger.error("kodx ask requires code files to analyze")
            sys.exit(1)

        # 3. Load program (custom or configured ask program)
        if args.program:
            ask_program = LLMProgram.from_file(Path(args.program))
            logger.info(f"Loaded custom program from {args.program}")
        else:
            # Use configured program path
            ask_program = LLMProgram.from_file(config.program_path)
            if config.program_path.name == "ask.yaml" and config.program_path.parent.name == ".kodx":
                logger.info("Using local ask program from .kodx/ask.yaml")
            elif config.program_path.parent.name == "programs":
                logger.info("Using built-in ask program")
            else:
                logger.info(f"Using configured ask program from {config.program_path}")

        if args.dry_run:
            logger.info("Dry run mode - container actions will be skipped")
            logger.info(f"Prompt: {args.prompt}")
            logger.info(f"Analysis directory: {analysis_dir}")
            logger.info(f"Program: {args.program or 'builtin ask'}")
            return

        # 4. Extract Docker configuration from program if present
        docker_dict = getattr(ask_program, "docker", {})
        docker_config = DockerConfig(**docker_dict) if docker_dict else DockerConfig()

        # 5. Initialize container with configured image
        async with DockerCodexTools(container_image=docker_config.image) as docker_tools:
            logger.info(f"Initialized Docker container with image: {docker_config.image}")

            # 6. Copy analysis directory to container
            if analysis_dir and os.path.exists(analysis_dir):
                await _copy_local_directory_to_container(docker_tools, analysis_dir, logger)
                logger.info(f"Copied {analysis_dir} to /workspace/repo for analysis")
            else:
                logger.info("Starting with clean container (no directory copied)")

            # 7. Handle setup scripts from config only (ask doesn't support CLI setup scripts)
            if docker_config.setup_script:
                logger.info("Executing setup script from config")
                await docker_tools.execute_setup_script_content(
                    docker_config.setup_script, disable_network_after=docker_config.disable_network_after_setup
                )
                logger.info("Config setup script completed successfully")

            # 8. Register tools with program
            ask_program.register_tools([docker_tools.feed_chars, docker_tools.create_new_shell])

            # 9. Start process
            process = await ask_program.start()

            # 10. Use resolved prompt
            final_prompt = args.prompt

            # 11. Set up callbacks and run
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
                        "kodx ask",
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

            # Handle JSON output if requested
            if args.json_output or args.json_output_file:
                _handle_json_output(run_result, process, args, logger)

            await process.aclose()

    except WorkspaceError as e:
        logger.error(f"Workspace error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _handle_json_output(run_result, process, args: AskArgs, logger):
    """Handle JSON output for ask command."""
    import json

    from .models import CommandResult

    # Create structured result
    result = CommandResult(
        command="ask",
        prompt=args.prompt,
        api_calls=run_result.api_calls,
        usd_cost=getattr(run_result, "usd_cost", 0.0),
        last_message=process.get_last_message(),
        stderr=process.get_stderr_log(),
        stop_reason=getattr(run_result, "stop_reason", "end_turn"),
        analysis_summary=process.get_last_message(),  # For ask command, the last message is the analysis
    )

    json_str = result.model_dump_json(indent=2)

    if args.json_output_file:
        with open(args.json_output_file, "w") as f:
            f.write(json_str)
        logger.info(f"JSON output written to {args.json_output_file}")
    else:
        typer.echo(json_str)


def ask(
    prompt_pos: Optional[str] = typer.Argument(None, help="Question about the codebase"),
    prompt_flag: Optional[str] = typer.Option(None, "--prompt", help="Question about the codebase"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="Read prompt from file"),
    repo_dir: Optional[str] = typer.Option(None, help="Directory to analyze (default: current directory)"),
    program: Optional[str] = typer.Option(None, help="Custom LLM program to use"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    json_output_file: Optional[str] = typer.Option(None, help="Write JSON results to file"),
    quiet: bool = typer.Option(False, "-q", help="Suppress most output"),
    log_level: str = typer.Option("INFO", help="Set logging level"),
    cost_limit: Optional[float] = typer.Option(None, help="Stop execution when cost exceeds this limit in USD"),
    timeout: Optional[int] = typer.Option(None, help="Execution timeout in seconds"),
    dry_run: bool = typer.Option(False, help="Print actions without executing"),
):
    """Ask questions about your code or directory."""
    try:
        # Resolve prompt with explicit error handling
        final_prompt = resolve_prompt(prompt_pos, prompt_flag, prompt_file)

        # Build args object
        args = AskArgs(
            prompt=final_prompt,
            prompt_file=prompt_file,
            json_output=json_output,
            json_output_file=json_output_file,
            repo_dir=repo_dir,
            program=program,
            quiet=quiet,
            log_level=log_level,
            cost_limit=cost_limit,
            timeout=timeout,
            dry_run=dry_run,
        )

        asyncio.run(execute_ask(args))

    except PromptResolutionError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    ask()
