"""Tests for configuration loading."""

import tempfile
from pathlib import Path

import pytest

from kodx.config import get_command_config, get_program_path


class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_builtin_fallback_when_no_config(self, tmp_path):
        """Test that built-in programs are used when no .kodx config exists."""
        # Change to temporary directory without .kodx
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Should fall back to built-in
            program_path = get_program_path("ask")
            assert program_path.name == "ask.yaml"
            assert program_path.parent.name == "programs"
            
        finally:
            os.chdir(original_cwd)

    def test_local_config_used_when_exists(self, tmp_path):
        """Test that local .kodx config is used when it exists."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .kodx directory and files
            kodx_dir = tmp_path / ".kodx"
            kodx_dir.mkdir()
            
            # Create local ask.yaml
            local_ask = kodx_dir / "ask.yaml"
            local_ask.write_text("# Local ask program")
            
            # Should use local copy
            program_path = get_program_path("ask")
            assert program_path.resolve() == local_ask.resolve()
            
        finally:
            os.chdir(original_cwd)

    def test_config_toml_program_path(self, tmp_path):
        """Test that config.toml program paths are respected."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .kodx directory
            kodx_dir = tmp_path / ".kodx"
            kodx_dir.mkdir()
            
            # Create custom program file
            custom_program = tmp_path / "custom-ask.yaml"
            custom_program.write_text("# Custom ask program")
            
            # Create config.toml pointing to custom program
            config_file = kodx_dir / "config.toml"
            config_file.write_text("""
[ask]
program = "custom-ask.yaml"
""")
            
            # Should use custom program
            program_path = get_program_path("ask")
            assert program_path.resolve() == custom_program.resolve()
            
        finally:
            os.chdir(original_cwd)

    def test_missing_custom_program_raises_error(self, tmp_path):
        """Test that missing custom program raises FileNotFoundError."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .kodx directory
            kodx_dir = tmp_path / ".kodx"
            kodx_dir.mkdir()
            
            # Create config.toml pointing to non-existent program
            config_file = kodx_dir / "config.toml"
            config_file.write_text("""
[ask]
program = "nonexistent.yaml"
""")
            
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="Program specified in .kodx/config.toml not found"):
                get_program_path("ask")
                
        finally:
            os.chdir(original_cwd)

    def test_malformed_toml_falls_back(self, tmp_path):
        """Test that malformed TOML falls back to local or built-in."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .kodx directory
            kodx_dir = tmp_path / ".kodx"
            kodx_dir.mkdir()
            
            # Create local program
            local_ask = kodx_dir / "ask.yaml"
            local_ask.write_text("# Local ask program")
            
            # Create malformed config.toml
            config_file = kodx_dir / "config.toml"
            config_file.write_text("invalid toml content [[[")
            
            # Should fall back to local program
            program_path = get_program_path("ask")
            assert program_path.resolve() == local_ask.resolve()
            
        finally:
            os.chdir(original_cwd)

    def test_command_config_with_defaults(self, tmp_path):
        """Test command config loading with cost_limit and log_level defaults."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .kodx directory and files
            kodx_dir = tmp_path / ".kodx"
            kodx_dir.mkdir()
            
            # Create local ask.yaml and code.yaml
            local_ask = kodx_dir / "ask.yaml"
            local_ask.write_text("# Local ask program")
            local_code = kodx_dir / "code.yaml"
            local_code.write_text("# Local code program")
            
            # Create config.toml with global and command-specific defaults
            config_file = kodx_dir / "config.toml"
            config_file.write_text("""
[global]
cost_limit = 1.0
log_level = "INFO"
timeout = 600

[ask]
program = ".kodx/ask.yaml"
cost_limit = 0.5
log_level = "DEBUG"
timeout = 300

[code]
program = ".kodx/code.yaml"
# Inherits global defaults
""")
            
            # Test ask config - should use command-specific overrides
            ask_config = get_command_config("ask")
            assert ask_config.program_path.resolve() == local_ask.resolve()
            assert ask_config.cost_limit == 0.5
            assert ask_config.log_level == "DEBUG"
            assert ask_config.timeout == 300
            
            # Test code config - should inherit global defaults
            code_config = get_command_config("code")
            assert code_config.cost_limit == 1.0  # From global
            assert code_config.log_level == "INFO"  # From global
            assert code_config.timeout == 600  # From global
            
        finally:
            os.chdir(original_cwd)

    def test_command_config_no_global_section(self, tmp_path):
        """Test command config when no global section exists."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            
            # Create .kodx directory
            kodx_dir = tmp_path / ".kodx"
            kodx_dir.mkdir()
            
            # Create config.toml without global section
            config_file = kodx_dir / "config.toml"
            config_file.write_text("""
[ask]
program = ".kodx/ask.yaml"
cost_limit = 0.75
timeout = 500
""")
            
            # Create local ask.yaml
            local_ask = kodx_dir / "ask.yaml"
            local_ask.write_text("# Local ask program")
            
            config = get_command_config("ask")
            assert config.cost_limit == 0.75
            assert config.log_level is None  # No default
            assert config.timeout == 500

        finally:
            os.chdir(original_cwd)
