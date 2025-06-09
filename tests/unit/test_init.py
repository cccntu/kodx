"""Tests for kodx init command."""

import tempfile
from pathlib import Path

import pytest

from kodx.cli_init import copy_builtin_programs, create_kodx_config


class TestKodxInit:
    """Test kodx init functionality."""

    def test_create_kodx_config(self, tmp_path):
        """Test config.toml creation."""
        kodx_dir = tmp_path / ".kodx"
        kodx_dir.mkdir()
        
        create_kodx_config(kodx_dir)
        
        config_file = kodx_dir / "config.toml"
        assert config_file.exists()
        
        content = config_file.read_text()
        assert "[version]" in content
        assert 'kodx = "0.1.0"' in content
        assert 'llmproc = "' in content  # Version should be detected
        assert "[ask]" in content
        assert 'program = ".kodx/ask.yaml"' in content
        assert "[code]" in content
        assert 'program = ".kodx/code.yaml"' in content

    def test_copy_builtin_programs(self, tmp_path):
        """Test copying built-in programs."""
        kodx_dir = tmp_path / ".kodx"
        kodx_dir.mkdir()
        
        copy_builtin_programs(kodx_dir)
        
        ask_file = kodx_dir / "ask.yaml"
        code_file = kodx_dir / "code.yaml"
        
        assert ask_file.exists()
        assert code_file.exists()
        
        # Check content was copied
        ask_content = ask_file.read_text()
        code_content = code_file.read_text()
        
        assert "model:" in ask_content
        assert "claude-sonnet-4" in ask_content
        assert "model:" in code_content
        assert "claude-sonnet-4" in code_content

    def test_copy_builtin_programs_missing_source(self, tmp_path, monkeypatch):
        """Test error handling when built-in programs are missing."""
        # Mock get_builtin_programs_dir to return non-existent directory
        def mock_get_builtin_programs_dir():
            return tmp_path / "nonexistent"
        
        from kodx import cli_init
        monkeypatch.setattr(cli_init, "get_builtin_programs_dir", mock_get_builtin_programs_dir)
        
        kodx_dir = tmp_path / ".kodx"
        kodx_dir.mkdir()
        
        with pytest.raises(FileNotFoundError, match="Built-in program not found"):
            copy_builtin_programs(kodx_dir)