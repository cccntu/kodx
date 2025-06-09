"""Data models for Kodx configuration."""

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


class DockerConfig(BaseModel):
    """Docker container configuration for Kodx."""

    model_config = {"extra": "forbid"}
    """Docker container configuration for Kodx."""

    image: str = Field(default="python:3.11", description="Docker image to use for the container")

    setup_script: Optional[str] = Field(
        default=None, description="Bash script to execute after container initialization"
    )

    disable_network_after_setup: bool = Field(
        default=False, description="Disconnect container from networks after setup script completes"
    )


# Shared CLI option models
class CLIInterfaceOptions(BaseModel):
    """User-facing CLI options that should be exposed across commands"""

    prompt_file: Optional[str] = Field(None, description="Read prompt from file")
    json_output: bool = Field(False, description="Output results as JSON")
    json_output_file: Optional[str] = Field(None, description="Write JSON results to file")


class CommonOptions(BaseModel):
    """Common options available to all commands"""

    quiet: bool = Field(False, description="Suppress most output")
    log_level: str = Field("INFO", description="Set logging level")
    cost_limit: Optional[float] = Field(None, description="Stop when cost exceeds limit")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds")
    program: Optional[str] = Field(None, description="Custom LLM program to use")
    dry_run: bool = Field(False, description="Print actions without executing")


class GitOptions(BaseModel):
    """Git-related options for targeting specific repository states"""

    base_ref: Optional[str] = Field(None, description="Git reference to work from (default: current HEAD)")
    dirty: bool = Field(False, description="Include uncommitted changes")


class CommandResult(BaseModel):
    """Unified result structure for all commands"""

    command: str  # "ask" | "code" | "core"
    prompt: str
    api_calls: int
    usd_cost: float
    last_message: str
    stderr: list[str]
    stop_reason: str
    # Command-specific fields
    branch_created: Optional[str] = None  # For code command
    analysis_summary: Optional[str] = None  # For ask command
    implementation_summary: Optional[str] = None  # For code command


# Legacy CLI args for core command (dataclass for backwards compatibility)
@dataclass
class CLIArgs:
    """Collected CLI arguments for Kodx core command."""

    program_path: Optional[str]
    prompt: Optional[str]
    prompt_file: Optional[str]
    append: bool = False
    json_output: bool = False
    json_output_file: Optional[str] = None
    quiet: bool = False
    log_level: str = "INFO"
    repo_dir: Optional[str] = None
    image: str = "python:3.11"
    setup_script: Optional[str] = None
    export_dir: Optional[str] = None
    cost_limit: Optional[float] = None
    timeout: Optional[int] = None
    disable_network_after_setup: bool = False
