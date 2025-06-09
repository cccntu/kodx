"""Unit tests for CLI argument validation and interactions."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from kodx.cli import app


class TestCLIStructure:
    """Test basic CLI structure and help output."""
    
    def test_main_help(self):
        """Test main command help shows subcommands."""
        runner = CliRunner()
        result = runner.invoke(app, ['--help'])
        
        assert result.exit_code == 0
        assert 'ask' in result.output
        assert 'code' in result.output
        assert 'Ask questions about your code or directory.' in result.output
        assert 'Code in a container and export changes to a branch.' in result.output

    def test_ask_help(self):
        """Test ask command help."""
        runner = CliRunner()
        result = runner.invoke(app, ['ask', '--help'])

        assert result.exit_code == 0
        assert 'prompt_pos' in result.output.lower() or 'prompt' in result.output.lower()
        assert '--repo-dir' in result.output
        assert '--program' in result.output
        assert '--cost-limit' in result.output
        # Ensure git-specific flags are not present
        assert '--dirty' not in result.output
        assert '--base-ref' not in result.output

    def test_code_help(self):
        """Test code command help."""
        runner = CliRunner()
        result = runner.invoke(app, ['code', '--help'])

        assert result.exit_code == 0
        assert 'prompt_pos' in result.output.lower() or 'feature description' in result.output.lower()
        assert '--base-ref' in result.output
        assert '--dirty' in result.output
        assert '--branch' in result.output
        assert '--program' in result.output


class TestCodeCommandValidation:
    """Test kodx code command argument validation."""
    
    def test_dirty_and_base_ref_conflict(self):
        """Test that --dirty and --base-ref cannot be used together."""
        runner = CliRunner()
        result = runner.invoke(app, ['code', 'test request', '--dirty', '--base-ref', 'main'])
        
        assert result.exit_code == 1
        assert 'ERROR: --dirty cannot be used with --base-ref' in result.output
        assert '--dirty only applies when branching from current commit' in result.output

    def test_dirty_without_base_ref_accepted(self):
        """Test that --dirty alone is accepted (but will fail later for other reasons)."""
        runner = CliRunner()
        with patch('kodx.git_utils.is_git_repo', return_value=False), \
             patch('kodx.cli_code.execute_code') as mock_execute:
            result = runner.invoke(app, ['code', 'test request', '--dirty'])
            
            # Should not fail on argument validation, but will fail on git repo check
            assert 'ERROR: --dirty cannot be used with --base-ref' not in result.output

    def test_base_ref_without_dirty_accepted(self):
        """Test that --base-ref alone is accepted."""
        runner = CliRunner()
        with patch('kodx.git_utils.is_git_repo', return_value=False), \
             patch('kodx.cli_code.execute_code') as mock_execute:
            result = runner.invoke(app, ['code', 'test request', '--base-ref', 'main'])
            
            # Should not fail on argument validation
            assert 'ERROR: --dirty cannot be used with --base-ref' not in result.output

    def test_neither_flag_accepted(self):
        """Test that neither flag is fine."""
        runner = CliRunner()
        with patch('kodx.git_utils.is_git_repo', return_value=False), \
             patch('kodx.cli_code.execute_code') as mock_execute:
            result = runner.invoke(app, ['code', 'test request'])
            
            # Should not fail on argument validation
            assert 'ERROR: --dirty cannot be used with --base-ref' not in result.output

    @patch('kodx.git_utils.is_git_repo')
    @patch('kodx.cli_code.execute_code')
    def test_git_repo_requirement(self, mock_execute, mock_is_git_repo):
        """Test that kodx code requires git repository."""
        mock_is_git_repo.return_value = False
        
        runner = CliRunner()
        
        result = runner.invoke(app, ['code', 'test request'])
        
        # Should call execute_code which will check git repo
        mock_execute.assert_called_once()

    def test_missing_request_argument(self):
        """Test that request argument is required."""
        runner = CliRunner()
        result = runner.invoke(app, ['code'])

        assert result.exit_code != 0
        assert 'no prompt' in result.output.lower() or 'missing argument' in result.output.lower()


class TestAskCommandValidation:
    """Test kodx ask command argument validation."""
    
    def test_missing_query_argument(self):
        """Test that query argument is required."""
        runner = CliRunner()
        result = runner.invoke(app, ['ask'])

        assert result.exit_code != 0
        assert 'no prompt' in result.output.lower() or 'missing argument' in result.output.lower()

    def test_query_argument_accepted(self):
        """Test that query argument is accepted."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:
            # Mock _ask_main to avoid actual execution
            
            result = runner.invoke(app, ['ask', 'test query'])
            
            # Should call _ask_main
            mock_execute_ask.assert_called_once()

    def test_repo_dir_option(self):
        """Test --repo-dir option parsing."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:
            
            result = runner.invoke(app, ['ask', 'test query', '--repo-dir', '/some/path'])

            # Should pass repo_dir to _ask_main
            args, kwargs = mock_execute_ask.call_args
            assert args[0].repo_dir == '/some/path'

    def test_program_option(self):
        """Test --program option parsing."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:
            
            # Create a temporary file for the program option
            with runner.isolated_filesystem():
                Path('test_program.yaml').write_text('test: content')
                
                result = runner.invoke(app, ['ask', 'test query', '--program', 'test_program.yaml'])

                # Should pass program to _ask_main
                args, kwargs = mock_execute_ask.call_args
                assert args[0].program == 'test_program.yaml'

    def test_git_flags_not_available(self):
        """Test that git-specific flags are not available in ask command."""
        runner = CliRunner()
        
        # Test --dirty flag is rejected
        result = runner.invoke(app, ['ask', 'test query', '--dirty'])
        assert result.exit_code != 0
        # The error message may vary, but it should fail
        
        # Test --base-ref flag is rejected  
        result = runner.invoke(app, ['ask', 'test query', '--base-ref', 'main'])
        assert result.exit_code != 0
        # The error message may vary, but it should fail


class TestMainCommandBehavior:
    """Test original kodx main command behavior."""
    
    def test_main_without_subcommand(self):
        """Test that main command without subcommand works (original behavior)."""
        runner = CliRunner()
        with patch('kodx.cli.execute_kodx') as mock_execute_kodx:
            
            result = runner.invoke(app, ['--prompt', 'test prompt'])
            
            # Should call _async_main (original behavior)
            mock_execute_kodx.assert_called_once()

    def test_main_with_program_file(self):
        """Test main command with program file."""
        runner = CliRunner()
        with patch('kodx.cli.execute_kodx') as mock_execute_kodx:
            
            with runner.isolated_filesystem():
                Path('test_program.yaml').write_text('test: content')
                
                result = runner.invoke(app, ['--program', 'test_program.yaml', '--prompt', 'test'])
                
                # Should call _async_main with program
                mock_execute_kodx.assert_called_once()


class TestBuiltinProgramPath:
    """Test built-in program path resolution."""
    
    def test_get_builtin_program_path_ask(self):
        """Test getting built-in ask program path."""
        from kodx.cli_ask import get_builtin_program_path
        
        path = get_builtin_program_path('ask')
        assert path.name == 'ask.yaml'
        assert 'programs' in str(path)
        assert path.exists()

    def test_get_builtin_program_path_code(self):
        """Test getting built-in code program path."""
        from kodx.cli_ask import get_builtin_program_path
        
        path = get_builtin_program_path('code')
        assert path.name == 'code.yaml'
        assert 'programs' in str(path)
        assert path.exists()

    def test_get_builtin_program_path_nonexistent(self):
        """Test getting non-existent built-in program."""
        from kodx.cli_ask import get_builtin_program_path
        
        with pytest.raises(FileNotFoundError, match="Built-in program not found"):
            get_builtin_program_path('nonexistent')


class TestCommonOptions:
    """Test common options across commands."""
    
    def test_cost_limit_option_ask(self):
        """Test --cost-limit option on ask command."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:
            
            result = runner.invoke(app, ['ask', 'test', '--cost-limit', '1.5'])

            # Should pass cost_limit to _ask_main
            args, kwargs = mock_execute_ask.call_args
            assert args[0].cost_limit == 1.5

    def test_cost_limit_option_code(self):
        """Test --cost-limit option on code command."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:
            
            result = runner.invoke(app, ['code', 'test', '--cost-limit', '2.0'])

            # Should pass cost_limit to _code_main
            args, kwargs = mock_execute_code.call_args
            assert args[0].cost_limit == 2.0

    def test_timeout_option_ask(self):
        """Test --timeout option on ask command."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:
            runner.invoke(app, ['ask', 'test', '--timeout', '30'])
            args, _ = mock_execute_ask.call_args
            assert args[0].timeout == 30

    def test_timeout_option_code(self):
        """Test --timeout option on code command."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:
            runner.invoke(app, ['code', 'test', '--timeout', '45'])
            args, _ = mock_execute_code.call_args
            assert args[0].timeout == 45

    def test_quiet_option(self):
        """Test --quiet option."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:
            
            result = runner.invoke(app, ['ask', 'test', '-q'])

            # Should pass quiet=True to _ask_main
            args, kwargs = mock_execute_ask.call_args
            assert args[0].quiet is True

    def test_log_level_option(self):
        """Test --log-level option."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:

            result = runner.invoke(app, ['ask', 'test', '--log-level', 'DEBUG'])

            # Should pass log_level to _ask_main
            args, kwargs = mock_execute_ask.call_args
            assert args[0].log_level == 'DEBUG'

    def test_dry_run_option_ask(self):
        """Test --dry-run option on ask command."""
        runner = CliRunner()
        with patch('kodx.cli_ask.execute_ask') as mock_execute_ask:

            result = runner.invoke(app, ['ask', 'test', '--dry-run'])

            args, kwargs = mock_execute_ask.call_args
            assert args[0].dry_run is True


class TestCodeCommandArguments:
    """Test specific kodx code command argument parsing."""
    
    def test_base_ref_parsing(self):
        """Test --base-ref argument parsing."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:
            
            result = runner.invoke(app, ['code', 'test', '--base-ref', 'develop'])

            # Should pass base_ref to _code_main
            args, kwargs = mock_execute_code.call_args
            assert args[0].base_ref == 'develop'

    def test_dirty_flag_parsing(self):
        """Test --dirty flag parsing."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:
            
            result = runner.invoke(app, ['code', 'test', '--dirty'])

            # Should pass dirty=True to _code_main
            args, kwargs = mock_execute_code.call_args
            assert args[0].dirty is True

    def test_branch_option_parsing(self):
        """Test --branch option parsing."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:
            
            result = runner.invoke(app, ['code', 'test', '--branch', 'feature/custom'])

            # Should pass branch to _code_main
            args, kwargs = mock_execute_code.call_args
            assert args[0].branch == 'feature/custom'

    def test_program_option_code(self):
        """Test --program option on code command."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:
            
            with runner.isolated_filesystem():
                Path('custom_program.yaml').write_text('test: content')
                
                result = runner.invoke(app, ['code', 'test', '--program', 'custom_program.yaml'])

                # Should pass program to _code_main
                args, kwargs = mock_execute_code.call_args
                assert args[0].program == 'custom_program.yaml'

    def test_dry_run_option_code(self):
        """Test --dry-run option on code command."""
        runner = CliRunner()
        with patch('kodx.cli_code.execute_code') as mock_execute_code:

            result = runner.invoke(app, ['code', 'test', '--dry-run'])

            args, kwargs = mock_execute_code.call_args
            assert args[0].dry_run is True
