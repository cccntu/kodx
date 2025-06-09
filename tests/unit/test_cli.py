"""Unit tests for CLI argument parsing and validation."""

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from kodx.cli import app
from kodx.models import CLIArgs


@pytest.mark.unit
class TestCLI:
    """Test CLI argument parsing and validation without execution."""

    def test_argument_parsing(self):
        """Test all CLI flags and options."""
        runner = CliRunner()

        # Test help output
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Execute custom LLM programs with container isolation" in result.output
        assert "-p" in result.output  # prompt option (short form)
        assert "--repo-dir" in result.output
        assert "--image" in result.output
        assert "-l" in result.output  # log-level option (short form)

    def test_default_values(self):
        """Verify default values for CLI arguments."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            # Mock execute_kodx at the CLI module level 
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:
                # Test with minimal arguments
                result = runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt", "test"])

                # Verify execute_kodx was called
                mock_execute_kodx.assert_called_once()
                # Get the CLIArgs object that was passed
                args = mock_execute_kodx.call_args.args[0]

                # Check default values
                assert isinstance(args, CLIArgs)
                assert args.program_path == program_path
                assert args.prompt == "test"
                assert args.prompt_file is None
                assert args.append is False
                assert args.json_output is False
                assert args.json_output_file is None
                assert args.quiet is False
                assert args.log_level == "INFO"
                assert args.repo_dir == "."
                assert args.image == "python:3.11"
                assert args.timeout is None
        finally:
            os.unlink(program_path)

    def test_custom_arguments(self):
        """Test custom argument values."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                # Test with custom arguments
                runner.invoke(app, ["--program", program_path, "--repo-dir", "", "--prompt", "custom prompt", "--image", "ubuntu:22.04", "--log-level", "DEBUG", "--quiet", "--json"])

                mock_execute_kodx.assert_called_once()
                args = mock_execute_kodx.call_args.args[0]

                assert isinstance(args, CLIArgs)
                assert args.program_path == program_path
                assert args.prompt == "custom prompt"
                assert args.prompt_file is None
                assert args.append is False
                assert args.json_output is True
                assert args.json_output_file is None
                assert args.quiet is True
                assert args.log_level == "DEBUG"
                assert args.repo_dir == ""
                assert args.image == "ubuntu:22.04"
        finally:
            os.unlink(program_path)

    def test_program_path_validation(self):
        """Test program file validation."""
        runner = CliRunner()

        # Test with non-existent program file
        result = runner.invoke(app, ["--program", "non_existent.yaml", "--repo-dir", ".", "--prompt", "test"])
        # Should fail because file doesn't exist
        assert result.exit_code != 0
        # In the new implementation, the error goes to stderr via logging
        # but the important thing is that it exits with non-zero code

    def test_program_path_handling_with_existing_file(self):
        """Test program path handling with valid file."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
model:
  name: "test-model"
  provider: "test"

prompt:
  system: "test prompt"
""")
            temp_program = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                runner.invoke(app, ["--program", temp_program, "--repo-dir", ".", "--prompt", "test"])

                mock_execute_kodx.assert_called_once()
                args = mock_execute_kodx.call_args.args[0]

                assert isinstance(args, CLIArgs)
                assert args.program_path == temp_program
        finally:
            os.unlink(temp_program)

    def test_prompt_file_validation(self):
        """Test prompt file argument validation."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            # Test with non-existent prompt file
            result = runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt-file", "non_existent.txt"])
            # Should fail because file doesn't exist
            assert result.exit_code != 0
        finally:
            os.unlink(program_path)

    def test_prompt_file_with_existing_file(self):
        """Test prompt file with valid file."""
        runner = CliRunner()

        # Create temporary files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test prompt from file")
            temp_prompt = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt-file", temp_prompt])

                mock_execute_kodx.assert_called_once()
                args = mock_execute_kodx.call_args.args[0]

                assert isinstance(args, CLIArgs)
                assert args.prompt_file == temp_prompt
        finally:
            os.unlink(temp_prompt)
            os.unlink(program_path)

    def test_mutually_exclusive_options(self):
        """Test that certain options are handled correctly."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                # Test that both prompt and prompt-file can be specified (handled in _async_main)
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                    f.write("File prompt")
                    temp_prompt = f.name

                try:
                    runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt", "CLI prompt", "--prompt-file", temp_prompt])

                    # CLI should accept both (validation happens in _async_main)
                    mock_execute_kodx.assert_called_once()
                finally:
                    os.unlink(temp_prompt)
        finally:
            os.unlink(program_path)

    def test_append_flag(self):
        """Test append flag functionality."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt", "test", "--append"])

                mock_execute_kodx.assert_called_once()
                args = mock_execute_kodx.call_args.args[0]

                assert isinstance(args, CLIArgs)
                assert args.append is True
        finally:
            os.unlink(program_path)

    def test_image_parameter(self):
        """Test Docker image parameter."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                # Test custom image
                runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--image", "node:18", "--prompt", "test"])

                mock_execute_kodx.assert_called_once()
                args = mock_execute_kodx.call_args.args[0]

                assert isinstance(args, CLIArgs)
                assert args.image == "node:18"
        finally:
            os.unlink(program_path)

    def test_log_level_options(self):
        """Test log level parameter options."""
        runner = CliRunner()

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            for log_level in valid_log_levels:
                with patch("kodx.cli.execute_kodx") as mock_execute_kodx:

                    runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--log-level", log_level, "--prompt", "test"])

                    mock_execute_kodx.assert_called_once()
                    args = mock_execute_kodx.call_args.args[0]

                    assert isinstance(args, CLIArgs)
                    assert args.log_level == log_level
        finally:
            os.unlink(program_path)

    @patch("kodx.cli.execute_kodx")
    def test_error_handling_in_main(self, mock_execute_kodx):
        """Test error handling in main function."""
        runner = CliRunner()

        # Create temporary program file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model:\n  name: test\n  provider: test\n")
            program_path = f.name

        try:
            # Simulate an exception in _async_main
            mock_execute_kodx.side_effect = Exception("Test error")

            result = runner.invoke(app, ["--program", program_path, "--repo-dir", ".", "--prompt", "test"])

            # Should handle the exception gracefully
            assert result.exit_code != 0
        finally:
            os.unlink(program_path)
