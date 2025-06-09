"""Custom callback handler with YAML formatting for better tool output readability."""

from typing import Any

import yaml
from llmproc.cli.log_utils import CliCallbackHandler


class LiteralMultilineRepresenter:
    """Custom YAML representer that uses literal blocks for multi-line strings."""

    @staticmethod
    def represent_str(dumper, data):
        if "\n" in data:
            # Strip all trailing whitespace so PyYAML uses literal block
            # chomping (|-), even when the last line contains spaces.
            clean_data = data.rstrip()
            return dumper.represent_scalar(
                "tag:yaml.org,2002:str",
                clean_data,
                style="|",
            )
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)


class LiteralBlockDumper(yaml.SafeDumper):
    """YAML dumper that supports multi-line strings with literal blocks."""


LiteralBlockDumper.add_representer(str, LiteralMultilineRepresenter.represent_str)


def _format_yaml_block(data: Any) -> str:
    """Return YAML formatted string indented for logging."""
    yaml_str = yaml.dump(
        data,
        Dumper=LiteralBlockDumper,
        default_flow_style=False,
        allow_unicode=True,
    ).rstrip()
    return "\n".join(f"  {line}" for line in yaml_str.split("\n"))


class KodxCallbackHandler(CliCallbackHandler):
    """Enhanced CLI callback handler with YAML formatting for tool events."""

    def tool_start(self, tool_name: str, args: dict[str, Any]) -> None:
        """Log tool start with YAML formatted args."""
        indented_args = _format_yaml_block(args)
        self.logger.info(f"TOOL_USE {tool_name} ->\n{indented_args}")

    def tool_end(self, tool_name: str, result: Any) -> None:
        """Log tool completion with YAML formatted result."""
        # Extract relevant fields from ToolResult object
        result_dict = {"content": result.content, "is_error": result.is_error}

        # Convert result to YAML with proper multi-line handling
        indented_result = _format_yaml_block(result_dict)
        self.logger.info(f"TOOL_RESULT {tool_name} ->\n{indented_result}")
