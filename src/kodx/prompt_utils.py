"""Utilities for prompt resolution and validation."""

from typing import Optional


class PromptResolutionError(Exception):
    """Error in prompt resolution"""

    pass


def resolve_prompt(prompt_pos: Optional[str], prompt_flag: Optional[str], prompt_file: Optional[str]) -> str:
    """Resolve prompt with priority: file > flag > positional.

    Args:
        prompt_pos: Positional prompt argument
        prompt_flag: --prompt flag value
        prompt_file: --prompt-file flag value

    Returns:
        Resolved prompt text

    Raises:
        PromptResolutionError: If no prompt provided or conflicting options
    """
    # Check for conflicting explicit options
    if prompt_flag is not None and prompt_file is not None:
        raise PromptResolutionError("Cannot specify both --prompt and --prompt-file. Choose one.")

    # Priority resolution: file > flag > positional
    if prompt_file is not None:
        try:
            with open(prompt_file) as f:
                content = f.read().strip()
                if not content:
                    raise PromptResolutionError(f"Prompt file '{prompt_file}' is empty")
                return content
        except FileNotFoundError:
            raise PromptResolutionError(f"Prompt file not found: {prompt_file}")
        except OSError as e:
            raise PromptResolutionError(f"Error reading prompt file '{prompt_file}': {e}")

    if prompt_flag is not None:
        if not prompt_flag.strip():
            raise PromptResolutionError("--prompt cannot be empty")
        return prompt_flag.strip()

    if prompt_pos is not None:
        if not prompt_pos.strip():
            raise PromptResolutionError("Positional prompt cannot be empty")
        return prompt_pos.strip()

    # No prompt provided
    raise PromptResolutionError("No prompt provided. Use positional argument, --prompt, or --prompt-file")
