"""Core execution logic for Kodx."""

import asyncio
import os
import sys
from pathlib import Path

from llmproc import LLMProgram
from llmproc.cli.log_utils import get_logger, log_program_info
from llmproc.cli.run import _get_provided_prompt, _resolve_prompt, run_with_prompt

from .kodx_callback import KodxCallbackHandler
from .models import CLIArgs, DockerConfig
from .tools import DockerCodexTools
from .utils import docker_cp as _docker_cp

DEFAULT_PROGRAM_PATH = Path(__file__).parent / "programs" / "default.yml"
DEFAULT_TIMEOUT = 20 * 60  # 20 minutes


async def execute_kodx(args: CLIArgs) -> None:
    """Core execution logic for Kodx.

    Args:
        args: CLI arguments and configuration
    """
    logger = get_logger(args.log_level)

    try:
        # Early validation: Check if we have a prompt before starting container
        provided_prompt = _get_provided_prompt(args.prompt, args.prompt_file, logger)

        # 1. Load program (use default if not provided)
        if args.program_path:
            program = LLMProgram.from_file(Path(args.program_path))
            logger.info(f"Loaded program from {args.program_path}")
        else:
            # Use default program bundled with Kodx
            program = LLMProgram.from_file(DEFAULT_PROGRAM_PATH)
            logger.info("Using default program")

        # Early prompt validation: Check if we have any way to get a prompt
        embedded_prompt = getattr(program, "user_prompt", "")
        if provided_prompt is None and not (embedded_prompt and embedded_prompt.strip()):
            logger.error("No prompt provided via command line, stdin, or configuration")
            sys.exit(1)

        # 2. Extract Docker configuration from program if present
        docker_dict = getattr(program, "docker", {})
        docker_config = DockerConfig(**docker_dict) if docker_dict else DockerConfig()

        # Override config with CLI flag if provided
        if args.disable_network_after_setup:
            docker_config.disable_network_after_setup = True

        # Use CLI image if provided, otherwise use from config
        docker_image = args.image or docker_config.image

        # Initialize container with configured image using context manager
        async with DockerCodexTools(container_image=docker_image) as docker_tools:
            logger.info(f"Initialized Docker container with image: {docker_image}")

            # 3. Copy local directory if specified
            if args.repo_dir is not None:  # Only skip if not provided at all
                if args.repo_dir and not os.path.exists(args.repo_dir):  # Empty string is valid for clean container
                    logger.error(f"Directory does not exist: {args.repo_dir}")
                    sys.exit(1)
                if args.repo_dir:  # Non-empty string = copy directory
                    await _copy_local_directory_to_container(docker_tools, args.repo_dir, logger)
                    logger.info(f"Copied {args.repo_dir} to /workspace/repo")
                else:
                    logger.info("Starting with clean container (no repository copied)")
            else:
                # When --repo-dir not provided, default to current directory
                logger.info("No --repo-dir specified, using current directory")
                await _copy_local_directory_to_container(docker_tools, ".", logger)
                logger.info("Copied current directory to /workspace/repo")

            # 4. Handle setup scripts (CLI has precedence over config)
            if args.setup_script:
                # Execute CLI-provided setup script
                logger.info(f"Executing setup script from CLI: {args.setup_script}")
                await docker_tools.execute_setup_script(
                    args.setup_script, disable_network_after=docker_config.disable_network_after_setup
                )
                logger.info("CLI setup script completed successfully")
            elif docker_config.setup_script:
                # Execute inline setup script from config
                logger.info("Executing setup script from config")
                await docker_tools.execute_setup_script_content(
                    docker_config.setup_script, disable_network_after=docker_config.disable_network_after_setup
                )
                logger.info("Config setup script completed successfully")

            # 5. Register tools with program
            program.register_tools([docker_tools.feed_chars, docker_tools.create_new_shell])

            # 6. Start process
            process = await program.start()

            # 7. Handle prompt resolution (same logic as llmproc)
            embedded_prompt = getattr(process, "user_prompt", "")
            final_prompt = _resolve_prompt(provided_prompt, embedded_prompt, args.append, logger)

            # 8. Set up callbacks and run
            callback_handler = KodxCallbackHandler(logger, cost_limit=args.cost_limit)
            process.add_callback(callback_handler)

            log_program_info(process, final_prompt, logger)

            effective_timeout = args.timeout if args.timeout is not None else DEFAULT_TIMEOUT
            try:
                run_result = await asyncio.wait_for(
                    run_with_prompt(
                        process,
                        final_prompt,
                        "kodx",
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

            # 9. Export container changes if requested
            if args.export_dir:
                await _export_container_to_host(docker_tools, args.export_dir, logger)

            # Handle JSON output (same as llmproc but with file option)
            if args.json_output or args.json_output_file:
                import json

                output = {
                    "api_calls": run_result.api_calls,
                    "last_message": process.get_last_message(),
                    "stderr": process.get_stderr_log(),
                }

                # Add cost information if available
                if hasattr(run_result, "usd_cost"):
                    output["usd_cost"] = run_result.usd_cost

                # Add stop reason if available
                if hasattr(run_result, "stop_reason"):
                    output["stop_reason"] = run_result.stop_reason

                # Add cost limit if it was specified and stop reason is cost-related
                if (
                    args.cost_limit is not None
                    and hasattr(run_result, "stop_reason")
                    and run_result.stop_reason == "cost_limit_exceeded"
                ):
                    output["cost_limit"] = args.cost_limit

                json_str = json.dumps(output)

                if args.json_output_file:
                    # Write to file
                    with open(args.json_output_file, "w") as f:
                        f.write(json_str)
                    logger.info(f"JSON output written to {args.json_output_file}")
                else:
                    # Write to stdout (original behavior)
                    import click

                    click.echo(json_str)

            await process.aclose()

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


async def _copy_local_directory_to_container(docker_tools, local_dir, logger):
    """Copy local directory to container workspace."""
    import subprocess

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
        raise RuntimeError(f"Failed to copy directory to container: {e}")


async def _export_container_to_host(docker_tools, export_dir, logger):
    """Export container workspace to host directory."""
    container_id = docker_tools.container_id
    if not container_id:
        raise RuntimeError("Container not initialized")

    # Create export directory if it doesn't exist
    os.makedirs(export_dir, exist_ok=True)

    # Try to copy /workspace/repo first, then fallback to /workspace
    result = _docker_cp(f"{container_id}:/workspace/repo/.", f"{export_dir}/", logger, check=False)
    if result.returncode == 0:
        logger.info(f"Successfully exported /workspace/repo to {export_dir}")
        return

    try:
        _docker_cp(f"{container_id}:/workspace/.", f"{export_dir}/", logger)
        logger.info(f"Successfully exported /workspace to {export_dir}")
    except RuntimeError as e:
        cause = e.__cause__
        stderr = cause.stderr.decode() if getattr(cause, "stderr", None) else ""
        if "No such file or directory" in stderr:
            logger.warning("No files to export - container workspace is empty")
        else:
            raise RuntimeError(f"Failed to export container changes: {e}")
