"""Tests for repository analysis functionality."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from kodx.cli import app
from kodx.core import _copy_local_directory_to_container
from kodx.models import CLIArgs


@pytest.mark.unit
class TestRepositoryAnalysis:
    """Test repository analysis functionality."""

    @patch("kodx.cli.execute_kodx")
    def test_main_with_repo_dir(self, mock_execute_kodx):
        """Test main function with repo directory."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
model:
  name: claude-sonnet-4-20250514
  provider: anthropic

prompt:
  system: "You are a code analysis expert."
""")
            program_path = f.name

        try:

            runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt", "How does authentication work?"])

            mock_execute_kodx.assert_called_once()
            args = mock_execute_kodx.call_args.args[0]
            assert isinstance(args, CLIArgs)
            assert args.program_path == program_path
            assert args.prompt == "How does authentication work?"
            assert args.repo_dir == "."
        finally:
            Path(program_path).unlink(missing_ok=True)

    @patch("kodx.cli.execute_kodx")
    def test_main_with_clean_container(self, mock_execute_kodx):
        """Test main function with clean container."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
model:
  name: claude-sonnet-4-20250514
  provider: anthropic

prompt:
  system: "You are a Python expert."
""")
            program_path = f.name

        try:

            runner.invoke(app, ["--program", program_path, "--repo-dir", "", "--prompt", "Create a web server"])

            mock_execute_kodx.assert_called_once()
            args = mock_execute_kodx.call_args.args[0]
            assert isinstance(args, CLIArgs)
            assert args.program_path == program_path
            assert args.prompt == "Create a web server"
            assert args.repo_dir == ""  # empty repo_dir for clean container
        finally:
            Path(program_path).unlink(missing_ok=True)

    @patch("kodx.cli.execute_kodx")
    def test_main_with_custom_image(self, mock_execute_kodx):
        """Test main function with custom Docker image."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
model:
  name: claude-sonnet-4-20250514
  provider: anthropic

prompt:
  system: "You are a Node.js expert."
""")
            program_path = f.name

        try:

            runner.invoke(app, ["--program", program_path, "--repo-dir", "", "--image", "node:18", "--prompt", "Create a React app"])

            mock_execute_kodx.assert_called_once()
            args = mock_execute_kodx.call_args.args[0]
            assert isinstance(args, CLIArgs)
            assert args.program_path == program_path
            assert args.image == "node:18"  # custom image
        finally:
            Path(program_path).unlink(missing_ok=True)

    @patch("kodx.cli.execute_kodx")
    def test_main_with_json_output(self, mock_execute_kodx):
        """Test main function with JSON output."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
model:
  name: claude-sonnet-4-20250514
  provider: anthropic

prompt:
  system: "You are a security expert."
""")
            program_path = f.name

        try:

            runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt", "Find vulnerabilities", "--json"])

            mock_execute_kodx.assert_called_once()
            args = mock_execute_kodx.call_args.args[0]
            assert isinstance(args, CLIArgs)
            assert args.json_output is True
        finally:
            Path(program_path).unlink(missing_ok=True)

    def test_main_help(self):
        """Test that main command shows proper help."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Execute custom LLM programs with container isolation" in result.output
        assert "--repo-dir" in result.output
        assert "--prompt" in result.output
        assert "--image" in result.output

    @patch("subprocess.run")
    @pytest.mark.asyncio
    async def test_copy_local_directory_to_container(self, mock_run):
        """Test local directory copying functionality."""
        from llmproc.cli.log_utils import get_logger

        # Mock Docker tools
        docker_tools = Mock()
        docker_tools.container_id = "test_container_123"
        docker_tools.feed_chars = AsyncMock()

        # Mock successful docker cp
        mock_run.return_value = Mock(returncode=0)

        logger = get_logger("INFO")
        local_dir = "/tmp/test_repo"

        await _copy_local_directory_to_container(docker_tools, local_dir, logger)

        # Verify container setup commands
        docker_tools.feed_chars.assert_any_call("mkdir -p /workspace/repo")
        docker_tools.feed_chars.assert_any_call("cd /workspace/repo")

        # Verify docker cp was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "docker"
        assert args[1] == "cp"
        assert f"{local_dir}/." in args
        assert "test_container_123:/workspace/repo/" in args[-1]

    @patch("subprocess.run")
    @pytest.mark.asyncio
    async def test_copy_local_directory_failure(self, mock_run):
        """Test local directory copying failure handling."""
        import subprocess

        from llmproc.cli.log_utils import get_logger

        # Mock Docker tools
        docker_tools = Mock()
        docker_tools.container_id = "test_container_123"
        docker_tools.feed_chars = AsyncMock()

        # Mock failed docker cp
        mock_run.side_effect = subprocess.CalledProcessError(1, ["docker", "cp"], stderr="No such file or directory")

        logger = get_logger("INFO")

        with pytest.raises(RuntimeError, match="Failed to copy directory to container"):
            await _copy_local_directory_to_container(docker_tools, "/nonexistent/dir", logger)

    def test_main_missing_required_args(self):
        """Test main command behavior with optional arguments."""
        runner = CliRunner()

        # Program path is now optional - should use default program
        with patch("kodx.cli.execute_kodx") as mock_execute_kodx:
            result = runner.invoke(app, ["--repo-dir", ".", "--prompt", "test"])
            assert result.exit_code == 0  # Should succeed with default program
            mock_execute_kodx.assert_called_once()

        # repo-dir is now optional - should default to current directory
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: claude-sonnet-4-20250514\n  provider: anthropic\n")
            program_path = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:
                result = runner.invoke(app, ["--program", program_path, "--prompt", "test"])
                assert result.exit_code == 0  # Should succeed with default repo-dir
                mock_execute_kodx.assert_called_once()
                args = mock_execute_kodx.call_args.args[0]
                assert isinstance(args, CLIArgs)
                assert args.repo_dir is None  # repo_dir should be None (triggering default behavior)
        finally:
            Path(program_path).unlink(missing_ok=True)

    @patch("kodx.cli.execute_kodx")
    def test_main_with_prompt_file(self, mock_execute_kodx):
        """Test main command with prompt file."""
        runner = CliRunner()

        # Create temporary files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Analyze this codebase for security issues")
            prompt_file = f.name

        try:

            runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt-file", prompt_file])

            mock_execute_kodx.assert_called_once()
            args = mock_execute_kodx.call_args.args[0]
            assert isinstance(args, CLIArgs)
            assert args.prompt_file == prompt_file
        finally:
            Path(program_path).unlink(missing_ok=True)
            Path(prompt_file).unlink(missing_ok=True)

    def test_main_nonexistent_program_file(self):
        """Test main command with non-existent program file."""
        runner = CliRunner()

        result = runner.invoke(app, ["--program", "nonexistent.yaml", "--repo-dir", ".", "--prompt", "test"])

        assert result.exit_code != 0

    def test_main_nonexistent_prompt_file(self):
        """Test main command with non-existent prompt file."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            result = runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt-file", "nonexistent.txt"])

            assert result.exit_code != 0
        finally:
            Path(program_path).unlink(missing_ok=True)
