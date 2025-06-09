"""Configuration loading utilities for kodx."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class CommandConfig:
    """Configuration for a command including program path and defaults."""

    program_path: Path
    cost_limit: Optional[float] = None
    log_level: Optional[str] = None
    timeout: Optional[int] = None


def get_program_path(program_name: str) -> Path:
    """Get the path to the program file for the given command.

    Resolution order:
    1. .kodx/config.toml [command] program setting
    2. .kodx/{command}.yaml (local copy)
    3. Built-in src/kodx/programs/{command}.yaml

    Args:
        program_name: Name of the program (ask, code, etc.)

    Returns:
        Path to the program file to use

    Raises:
        FileNotFoundError: If no program file can be found
    """
    # 1. Check .kodx/config.toml for custom program path
    config_file = Path(".kodx/config.toml")
    if config_file.exists():
        try:
            with open(config_file, "rb") as f:
                config = tomllib.load(f)

            # Check if this command has a custom program specified
            if program_name in config and "program" in config[program_name]:
                custom_path = Path(config[program_name]["program"])
                if custom_path.exists():
                    return custom_path
                # If specified path doesn't exist, that's an error worth reporting
                raise FileNotFoundError(f"Program specified in .kodx/config.toml not found: {custom_path}")

        except tomllib.TOMLDecodeError as e:
            # If config is malformed, fall back to other options but warn
            # Don't fail hard here since user might want to fix config
            pass

    # 2. Check for local copy in .kodx/
    local_copy = Path(f".kodx/{program_name}.yaml")
    if local_copy.exists():
        return local_copy

    # 3. Fall back to built-in
    module_dir = Path(__file__).parent
    builtin_path = module_dir / "programs" / f"{program_name}.yaml"

    if not builtin_path.exists():
        raise FileNotFoundError(f"Built-in program not found: {builtin_path}")

    return builtin_path


def get_command_config(command_name: str) -> CommandConfig:
    """Get full configuration for a command including program path and defaults.

    Resolution order for config values:
    1. Command-specific config in .kodx/config.toml [command]
    2. Global config in .kodx/config.toml [global]
    3. Built-in defaults

    Args:
        command_name: Name of the command (ask, code, etc.)

    Returns:
        CommandConfig with program path and resolved defaults
    """
    # Get program path using existing logic
    program_path = get_program_path(command_name)

    # Initialize with None (will use CLI or hardcoded defaults)
    cost_limit = None
    log_level = None
    timeout = None

    # Load config.toml if it exists
    config_file = Path(".kodx/config.toml")
    if config_file.exists():
        try:
            with open(config_file, "rb") as f:
                config = tomllib.load(f)

            # Get global defaults first
            global_config = config.get("global", {})
            cost_limit = global_config.get("cost_limit")
            log_level = global_config.get("log_level")
            timeout = global_config.get("timeout")

            # Override with command-specific config
            command_config = config.get(command_name, {})
            if "cost_limit" in command_config:
                cost_limit = command_config["cost_limit"]
            if "log_level" in command_config:
                log_level = command_config["log_level"]
            if "timeout" in command_config:
                timeout = command_config["timeout"]

        except tomllib.TOMLDecodeError:
            # If config is malformed, fall back to no defaults
            pass

    return CommandConfig(
        program_path=program_path,
        cost_limit=cost_limit,
        log_level=log_level,
        timeout=timeout,
    )
