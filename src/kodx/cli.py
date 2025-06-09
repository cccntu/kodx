"""CLI entry point for Kodx."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from .cli_ask import ask
from .cli_code import code
from .cli_init import init
from .core import execute_kodx
from .models import CLIArgs


def get_builtin_program_path(program_name: str) -> Path:
    """Get the path to a built-in program file.

    Args:
        program_name: Name of the program (ask, code, etc.)

    Returns:
        Path to the program file
    """
    # Get the directory where this module is located
    module_dir = Path(__file__).parent
    program_path_yaml = module_dir / "programs" / f"{program_name}.yaml"
    program_path_yml = module_dir / "programs" / f"{program_name}.yml"

    if program_path_yaml.exists():
        return program_path_yaml
    if program_path_yml.exists():
        return program_path_yml

    raise FileNotFoundError(f"Built-in program not found: {program_path_yaml} or {program_path_yml}")


app = typer.Typer(
    help="Execute custom LLM programs with container isolation.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Add subcommands
app.command("ask")(ask)
app.command("code")(code)
app.command("init")(init)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    program: Optional[str] = typer.Option(
        None, help="Path to LLM program file (YAML/TOML). If omitted, uses built-in assistant"
    ),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Prompt text. If omitted, read from stdin"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", "-f", help="Read prompt from file"),
    append: bool = typer.Option(False, "--append", "-a", help="Append provided prompt to embedded prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    json_output_file: Optional[str] = typer.Option(None, help="Write JSON results to file instead of stdout"),
    repo_dir: Optional[str] = typer.Option(
        None, help="Local directory to copy into container (empty string for clean container)"
    ),
    image: str = typer.Option("python:3.11", help="Docker image to use"),
    setup_script: Optional[str] = typer.Option(None, help="Setup script to execute in container before task"),
    export_dir: Optional[str] = typer.Option(None, help="Host directory to export container changes"),
    disable_network_after_setup: bool = typer.Option(
        False, help="Disconnect container from networks after setup script"
    ),
    timeout: Optional[int] = typer.Option(None, help="Execution timeout in seconds"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress most output"),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    ),
    cost_limit: Optional[float] = typer.Option(
        None, metavar="USD", help="Stop execution when cost exceeds this limit in USD"
    ),
):
    """Execute custom LLM programs with container isolation."""
    # If no subcommand was invoked, run the original kodx behavior
    if ctx.invoked_subcommand is None:
        args = CLIArgs(
            program_path=program,
            prompt=prompt,
            prompt_file=prompt_file,
            append=append,
            json_output=json_output,
            json_output_file=json_output_file,
            quiet=quiet,
            log_level=log_level,
            repo_dir=repo_dir,
            image=image,
            setup_script=setup_script,
            export_dir=export_dir,
            cost_limit=cost_limit,
            timeout=timeout,
            disable_network_after_setup=disable_network_after_setup,
        )

        asyncio.run(execute_kodx(args))


if __name__ == "__main__":
    app()
