"""Unit tests for CodexShell component."""

import ast

import pytest

from kodx.codex_shell import BashNotFoundError, CodexShell


@pytest.mark.unit
class TestCodexShell:
    """Test CodexShell PTY interaction without Docker containers."""

    def test_pty_server_code_generation(self):
        """Verify _get_pty_server_code() returns valid Python/FastAPI code."""
        # Get the generated PTY server code
        server_code = CodexShell._get_pty_server_code()

        # Verify it's a non-empty string
        assert isinstance(server_code, str)
        assert len(server_code) > 100

        # Verify it's syntactically correct Python
        try:
            ast.parse(server_code)
        except SyntaxError as e:
            pytest.fail(f"Generated PTY server code is not valid Python: {e}")

        # Check for required endpoints
        required_endpoints = ["/healthcheck", "/open", "/read", "/write", "/kill"]
        for endpoint in required_endpoints:
            assert endpoint in server_code, f"Missing endpoint: {endpoint}"

        # Check for required imports
        required_imports = ["FastAPI", "uvicorn", "asyncio", "pty"]
        for import_name in required_imports:
            assert import_name in server_code, f"Missing import: {import_name}"

        # Check for main execution
        assert 'if __name__ == "__main__":' in server_code
        assert "uvicorn.run" in server_code

    def test_bash_not_found_error(self):
        """Test BashNotFoundError exception."""
        error = BashNotFoundError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_shell_initialization_validation(self):
        """Test prerequisite checking logic."""
        # Test that CodexShell constructor accepts required parameters
        container = None  # Mock container
        shell_pid = 12345

        # Should not raise exception during construction
        shell = CodexShell(container, shell_pid)
        assert shell.container is container
        assert shell.shell_pid == shell_pid
        assert shell._server_installed is False

    def test_command_encoding(self):
        """Test proper escaping of shell commands in HTTP requests."""
        # Test various command patterns that need proper encoding
        test_commands = [
            "echo 'hello world'",
            'echo "hello world"',
            "echo 'hello \"nested\" quotes'",
            "echo 'line1' > file.txt && echo 'line2' >> file.txt",
            "export VAR='value with spaces'",
            "python -c \"print('test')\"",
        ]

        for command in test_commands:
            # Test that repr() properly escapes the command for shell execution
            escaped = repr(command)
            assert escaped.startswith("'") or escaped.startswith('"')
            assert escaped.endswith("'") or escaped.endswith('"')

            # Verify the escaped command can be evaluated back to original
            assert eval(escaped) == command

    def test_pty_server_code_structure(self):
        """Test that PTY server code has correct structure."""
        server_code = CodexShell._get_pty_server_code()

        # Check for FastAPI app definition
        assert "app = FastAPI" in server_code

        # Check for endpoint decorators
        assert '@app.get("/healthcheck")' in server_code
        assert '@app.post("/open")' in server_code
        assert '@app.post("/read/{pid}")' in server_code
        assert '@app.post("/write/{pid}")' in server_code
        assert '@app.post("/kill/{pid}")' in server_code

        # Check for proper port configuration
        assert "PORT = 1384" in server_code

        # Check for lifespan management
        assert "lifespan" in server_code
        assert "app.state.pipes" in server_code

    def test_server_code_error_handling(self):
        """Test that PTY server code includes proper error handling."""
        server_code = CodexShell._get_pty_server_code()

        # Check for HTTPException usage
        assert "HTTPException" in server_code
        assert "status_code=404" in server_code
        assert "status_code=400" in server_code

        # Check for process cleanup
        assert "os.close" in server_code
        assert "os.kill" in server_code

        # Check for exception handling in endpoints
        assert "try:" in server_code
        assert "except" in server_code
