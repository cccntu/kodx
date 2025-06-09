"""Unit tests for KodxCallbackHandler YAML formatting."""

import logging
from io import StringIO
from unittest.mock import MagicMock

import pytest

from kodx.kodx_callback import KodxCallbackHandler


class MockToolResult:
    """Mock ToolResult object for testing."""
    
    def __init__(self, content: str, is_error: bool = False):
        self.content = content
        self.is_error = is_error


@pytest.fixture
def callback_handler():
    """Create a KodxCallbackHandler with a string stream logger for testing."""
    # Create a logger that writes to a string stream
    logger = logging.getLogger("test_callback")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create a string stream handler
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Create the callback handler
    callback = KodxCallbackHandler(logger)
    callback._stream = stream  # Store reference for easy access
    
    return callback


class TestKodxCallbackHandler:
    """Test cases for KodxCallbackHandler."""
    
    def test_tool_start_formatting(self, callback_handler):
        """Test that tool_start formats args as multi-line YAML."""
        args = {"chars": "ls -la", "timeout": 30}

        callback_handler.tool_start("feed_chars", args)

        output = callback_handler._stream.getvalue()
        assert "TOOL_USE feed_chars ->" in output
        assert "chars: ls -la" in output
        assert "timeout: 30" in output
        # Output should not use flow style braces
        assert "{" not in output and "}" not in output
    
    def test_tool_end_single_line_content(self, callback_handler):
        """Test tool_end with single-line content."""
        result = MockToolResult("hello world", False)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        assert "TOOL_RESULT feed_chars ->" in output
        assert "content: hello world" in output
        assert "is_error: false" in output
        # Should not use literal block for single line
        assert "|-" not in output
    
    def test_tool_end_multiline_content_literal_block(self, callback_handler):
        """Test tool_end with multi-line content uses literal block style."""
        content = "line1\nline2\nline3"
        result = MockToolResult(content, False)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        assert "TOOL_RESULT feed_chars ->" in output
        assert "content: |-" in output  # Literal block indicator
        assert "line1" in output
        assert "line2" in output
        assert "line3" in output
        assert "is_error: false" in output
    
    def test_tool_end_empty_content(self, callback_handler):
        """Test tool_end with empty content."""
        result = MockToolResult("", False)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        assert "TOOL_RESULT feed_chars ->" in output
        assert "content: ''" in output or "content: " in output
        assert "is_error: false" in output
    
    def test_tool_end_error_result(self, callback_handler):
        """Test tool_end with error result."""
        result = MockToolResult("command not found", True)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        assert "TOOL_RESULT feed_chars ->" in output
        assert "content: command not found" in output
        assert "is_error: true" in output
    
    def test_tool_end_complex_multiline_content(self, callback_handler):
        """Test tool_end with complex multi-line content like file listings."""
        content = """total 112
drwxr-xr-x 2  501 dialout  4096 Jun  9 06:43 .
drwxr-xr-x 8 root root     4096 Jun  9 06:44 ..
-rw-r--r-- 1  501 dialout  5387 Jun  9 06:43 README.md"""
        result = MockToolResult(content, False)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        assert "TOOL_RESULT feed_chars ->" in output
        assert "content: |-" in output  # Literal block
        assert "total 112" in output
        assert "README.md" in output
        assert "is_error: false" in output

    def test_tool_end_multiline_with_trailing_newline(self, callback_handler):
        """Multiline content ending with newline should use literal block chomping."""
        content = "line1\nline2\n"
        result = MockToolResult(content, False)

        callback_handler.tool_end("feed_chars", result)

        output = callback_handler._stream.getvalue()
        assert "content: |-" in output
        assert "line1" in output
        assert "line2" in output

    def test_tool_end_multiline_with_trailing_spaces(self, callback_handler):
        """Multiline content ending with spaces should still use literal block."""
        content = "line1\nline2   "
        result = MockToolResult(content, False)

        callback_handler.tool_end("feed_chars", result)

        output = callback_handler._stream.getvalue()
        assert "content: |-" in output
        assert "line2" in output
    
    def test_tool_end_indentation(self, callback_handler):
        """Test that tool_end output is properly indented."""
        result = MockToolResult("test content", False)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        lines = output.split('\n')
        
        # Find the TOOL_RESULT line
        result_line_idx = None
        for i, line in enumerate(lines):
            if "TOOL_RESULT" in line:
                result_line_idx = i
                break
        
        assert result_line_idx is not None
        
        # Check that subsequent lines are indented with 2 spaces
        for i in range(result_line_idx + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Skip empty lines
                assert line.startswith("  "), f"Line '{line}' should be indented with 2 spaces"
    
    def test_preserves_special_characters(self, callback_handler):
        """Test that special characters in content are handled correctly by YAML."""
        content = "Hello\tworld\nWith 'quotes' and \"double quotes\""
        result = MockToolResult(content, False)
        
        callback_handler.tool_end("feed_chars", result)
        
        output = callback_handler._stream.getvalue()
        # Content should be properly formatted (either quoted or literal block)
        assert "content:" in output
        assert "Hello" in output
        assert "world" in output
        assert "quotes" in output
        assert "is_error: false" in output
    
    def test_cost_limit_inheritance(self, callback_handler):
        """Test that cost_limit is properly passed to parent class."""
        # Create a new callback with cost limit
        logger = logging.getLogger("test_cost")
        callback_with_limit = KodxCallbackHandler(logger, cost_limit=1.50)
        
        # Verify the cost limit is set (this tests inheritance from CliCallbackHandler)
        assert callback_with_limit.cost_limit == 1.50
    
    def test_multiple_tool_calls(self, callback_handler):
        """Test multiple sequential tool calls."""
        # First tool call
        callback_handler.tool_start("feed_chars", {"chars": "ls"})
        callback_handler.tool_end("feed_chars", MockToolResult("file1.txt\nfile2.txt", False))
        
        # Second tool call
        callback_handler.tool_start("create_new_shell", {})
        callback_handler.tool_end("create_new_shell", MockToolResult("New shell created", False))
        
        output = callback_handler._stream.getvalue()
        
        # Should contain both tool sequences
        assert output.count("TOOL_USE") == 2
        assert output.count("TOOL_RESULT") == 2
        assert "feed_chars" in output
        assert "create_new_shell" in output
        assert "file1.txt" in output
        assert "New shell created" in output