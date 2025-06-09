"""Models for kodx code command."""

from typing import Optional

from pydantic import BaseModel, Field

from .models import CLIInterfaceOptions, CommonOptions, GitOptions


class CodeSpecificOptions(BaseModel):
    """Options specific to kodx code command"""

    branch: Optional[str] = Field(None, description="Custom branch name (default: auto-generated)")


class CodeArgs(CLIInterfaceOptions, CommonOptions, GitOptions, CodeSpecificOptions):
    """Arguments for kodx code command"""

    prompt: str = Field(..., description="Feature description or implementation request")

    model_config = {"extra": "forbid"}
