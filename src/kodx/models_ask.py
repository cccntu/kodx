"""Models for kodx ask command."""

from typing import Optional

from pydantic import BaseModel, Field

from .models import CLIInterfaceOptions, CommonOptions


class AskSpecificOptions(BaseModel):
    """Options specific to kodx ask command"""

    repo_dir: Optional[str] = Field(None, description="Directory to analyze (default: current directory)")


class AskArgs(CLIInterfaceOptions, CommonOptions, AskSpecificOptions):
    """Arguments for kodx ask command"""

    prompt: str = Field(..., description="Question about the codebase")

    model_config = {"extra": "forbid"}
