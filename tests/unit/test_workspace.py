"""Unit tests for workspace utilities."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import subprocess

from kodx.workspace import (
    validate_files_exist,
    create_temporary_workspace,
    setup_clean_checkout,
    setup_dirty_copy,
    export_from_container,
    cleanup_workspace,
    WorkspaceError
)


class TestValidateFilesExist:
    """Test file validation for analysis."""
    
    def test_validate_files_exist_with_code_files(self):
        """Test validation with code files present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some code files
            (Path(temp_dir) / "main.py").write_text("print('hello')")
            (Path(temp_dir) / "script.js").write_text("console.log('test')")
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_with_config_files(self):
        """Test validation with config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config files
            (Path(temp_dir) / "config.yaml").write_text("key: value")
            (Path(temp_dir) / "package.json").write_text('{"name": "test"}')
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_with_docs(self):
        """Test validation with documentation files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create documentation files
            (Path(temp_dir) / "README.md").write_text("# Test")
            (Path(temp_dir) / "docs.txt").write_text("Documentation")
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_with_special_files(self):
        """Test validation with special files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create special files
            (Path(temp_dir) / "Makefile").write_text("all:\n\techo test")
            (Path(temp_dir) / "Dockerfile").write_text("FROM python:3.11")
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_empty_directory(self):
        """Test validation with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assert validate_files_exist(temp_dir) is False

    def test_validate_files_exist_only_hidden_files(self):
        """Test validation with only hidden files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create hidden files (should be ignored)
            (Path(temp_dir) / ".hidden").write_text("hidden")
            (Path(temp_dir) / ".env").write_text("SECRET=value")
            
            assert validate_files_exist(temp_dir) is False

    def test_validate_files_exist_only_build_artifacts(self):
        """Test validation with only build artifacts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create build directories (should be ignored)
            os.makedirs(Path(temp_dir) / "node_modules")
            os.makedirs(Path(temp_dir) / "__pycache__")
            os.makedirs(Path(temp_dir) / "build")
            
            # Add files in ignored directories
            (Path(temp_dir) / "node_modules" / "package.js").write_text("module")
            (Path(temp_dir) / "__pycache__" / "cache.pyc").write_text("cache")
            
            assert validate_files_exist(temp_dir) is False

    def test_validate_files_exist_mixed_valid_and_ignored(self):
        """Test validation with mix of valid and ignored files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid files
            (Path(temp_dir) / "main.py").write_text("print('hello')")
            
            # Create ignored files/directories
            os.makedirs(Path(temp_dir) / "node_modules")
            (Path(temp_dir) / ".hidden").write_text("hidden")
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_nonexistent_directory(self):
        """Test validation with non-existent directory."""
        assert validate_files_exist("/nonexistent/directory") is False

    def test_validate_files_exist_nested_structure(self):
        """Test validation with nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure with code files
            src_dir = Path(temp_dir) / "src" / "utils"
            src_dir.mkdir(parents=True)
            (src_dir / "helper.py").write_text("def helper(): pass")
            
            assert validate_files_exist(temp_dir) is True


class TestCreateTemporaryWorkspace:
    """Test temporary workspace creation."""
    
    def test_create_temporary_workspace(self):
        """Test temporary workspace creation."""
        workspace_dir = create_temporary_workspace()
        
        try:
            assert os.path.exists(workspace_dir)
            assert os.path.isdir(workspace_dir)
            assert "kodx-workspace-" in workspace_dir
        finally:
            # Cleanup
            if os.path.exists(workspace_dir):
                os.rmdir(workspace_dir)

    def test_create_multiple_workspaces_unique(self):
        """Test that multiple workspaces are unique."""
        workspace1 = create_temporary_workspace()
        workspace2 = create_temporary_workspace()
        
        try:
            assert workspace1 != workspace2
            assert os.path.exists(workspace1)
            assert os.path.exists(workspace2)
        finally:
            # Cleanup
            for workspace in [workspace1, workspace2]:
                if os.path.exists(workspace):
                    os.rmdir(workspace)


class TestSetupCleanCheckout:
    """Test clean checkout setup."""
    
    @patch('kodx.workspace._run_git_command')
    def test_setup_clean_checkout_success(self, mock_git_cmd):
        """Test successful clean checkout setup."""
        mock_git_cmd.return_value = Mock()
        
        with tempfile.TemporaryDirectory() as workspace_dir:
            repo_path = "/test/repo"
            commit_sha = "abc123"
            
            result = setup_clean_checkout(workspace_dir, repo_path, commit_sha)
            
            expected_repo_dir = os.path.join(workspace_dir, "repo")
            assert result == expected_repo_dir
            
            # Should call git clone and git checkout
            assert mock_git_cmd.call_count == 2
            
            # First call: git clone
            clone_call = mock_git_cmd.call_args_list[0]
            assert clone_call[0][0] == ["git", "clone", repo_path, expected_repo_dir]
            assert clone_call[0][1] == workspace_dir
            
            # Second call: git checkout
            checkout_call = mock_git_cmd.call_args_list[1]
            assert checkout_call[0][0] == ["git", "checkout", commit_sha]
            assert checkout_call[0][1] == expected_repo_dir

    @patch('kodx.workspace._run_git_command')
    def test_setup_clean_checkout_clone_failure(self, mock_git_cmd):
        """Test clean checkout setup with clone failure."""
        mock_git_cmd.side_effect = WorkspaceError("Clone failed")
        
        with tempfile.TemporaryDirectory() as workspace_dir:
            with pytest.raises(WorkspaceError, match="Clone failed"):
                setup_clean_checkout(workspace_dir, "/test/repo", "abc123")

    @patch('kodx.workspace._run_git_command')
    def test_setup_clean_checkout_checkout_failure(self, mock_git_cmd):
        """Test clean checkout setup with checkout failure."""
        # First call (clone) succeeds, second call (checkout) fails
        mock_git_cmd.side_effect = [Mock(), WorkspaceError("Checkout failed")]
        
        with tempfile.TemporaryDirectory() as workspace_dir:
            with pytest.raises(WorkspaceError, match="Checkout failed"):
                setup_clean_checkout(workspace_dir, "/test/repo", "abc123")


class TestSetupDirtyCopy:
    """Test dirty copy setup."""
    
    @patch('kodx.workspace.get_repo_root')
    @patch('shutil.copytree')
    def test_setup_dirty_copy_success(self, mock_copytree, mock_get_root):
        """Test successful dirty copy setup."""
        mock_get_root.return_value = "/real/repo/root"
        
        with tempfile.TemporaryDirectory() as workspace_dir:
            repo_path = "/test/repo"
            
            result = setup_dirty_copy(workspace_dir, repo_path)
            
            expected_repo_dir = os.path.join(workspace_dir, "repo")
            assert result == expected_repo_dir
            
            mock_get_root.assert_called_once_with(repo_path)
            mock_copytree.assert_called_once_with(
                "/real/repo/root", 
                expected_repo_dir, 
                symlinks=True
            )

    @patch('kodx.workspace.get_repo_root')
    @patch('shutil.copytree')
    def test_setup_dirty_copy_copytree_failure(self, mock_copytree, mock_get_root):
        """Test dirty copy setup with copytree failure."""
        mock_get_root.return_value = "/real/repo/root"
        mock_copytree.side_effect = OSError("Copy failed")
        
        with tempfile.TemporaryDirectory() as workspace_dir:
            with pytest.raises(WorkspaceError, match="Failed to copy repository"):
                setup_dirty_copy(workspace_dir, "/test/repo")

    @patch('kodx.workspace.get_repo_root')
    def test_setup_dirty_copy_git_error(self, mock_get_root):
        """Test dirty copy setup with git error."""
        from kodx.git_utils import GitError
        mock_get_root.side_effect = GitError("Not a git repo")
        
        with tempfile.TemporaryDirectory() as workspace_dir:
            with pytest.raises(WorkspaceError, match="Git error"):
                setup_dirty_copy(workspace_dir, "/test/repo")


class TestExportFromContainer:
    """Test container export functionality."""
    
    def test_export_from_container_success_repo(self):
        """Test successful export from container /workspace/repo."""
        mock_docker_tools = Mock()
        mock_docker_tools.container_id = "container123"
        
        with tempfile.TemporaryDirectory() as export_dir:
            with patch('subprocess.run') as mock_run:
                # First docker cp (repo) succeeds
                mock_run.return_value = Mock(returncode=0)
                
                result = export_from_container(mock_docker_tools, export_dir)
                
                assert result is True
                mock_run.assert_called_once_with(
                    ["docker", "cp", "container123:/workspace/repo/.", f"{export_dir}/"],
                    capture_output=True,
                    check=False
                )

    def test_export_from_container_fallback_workspace(self):
        """Test export fallback to /workspace."""
        mock_docker_tools = Mock()
        mock_docker_tools.container_id = "container123"
        
        with tempfile.TemporaryDirectory() as export_dir:
            with patch('subprocess.run') as mock_run:
                # First docker cp (repo) fails, second (workspace) succeeds
                mock_run.side_effect = [
                    Mock(returncode=1),  # repo fails
                    Mock(returncode=0)   # workspace succeeds
                ]
                
                result = export_from_container(mock_docker_tools, export_dir)
                
                assert result is True
                assert mock_run.call_count == 2
                
                # Check both calls
                calls = mock_run.call_args_list
                assert calls[0][0][0] == ["docker", "cp", "container123:/workspace/repo/.", f"{export_dir}/"]
                assert calls[1][0][0] == ["docker", "cp", "container123:/workspace/.", f"{export_dir}/"]

    def test_export_from_container_no_files(self):
        """Test export when no files exist."""
        mock_docker_tools = Mock()
        mock_docker_tools.container_id = "container123"
        
        with tempfile.TemporaryDirectory() as export_dir:
            with patch('subprocess.run') as mock_run:
                # Both docker cp commands fail with "No such file"
                error = subprocess.CalledProcessError(1, ["docker"])
                error.stderr = b"No such file or directory"
                mock_run.side_effect = [
                    Mock(returncode=1),  # repo fails
                    error                # workspace fails with no files
                ]
                
                result = export_from_container(mock_docker_tools, export_dir)
                
                assert result is False

    def test_export_from_container_other_error(self):
        """Test export with other docker error."""
        mock_docker_tools = Mock()
        mock_docker_tools.container_id = "container123"
        
        with tempfile.TemporaryDirectory() as export_dir:
            with patch('subprocess.run') as mock_run:
                # Both docker cp commands fail with other error
                error = subprocess.CalledProcessError(1, ["docker"])
                error.stderr = b"Permission denied"
                mock_run.side_effect = [
                    Mock(returncode=1),  # repo fails
                    error                # workspace fails with permission error
                ]
                
                with pytest.raises(WorkspaceError, match="Failed to export from container"):
                    export_from_container(mock_docker_tools, export_dir)

    def test_export_from_container_no_container_id(self):
        """Test export when container not initialized."""
        mock_docker_tools = Mock()
        mock_docker_tools.container_id = None
        
        with pytest.raises(WorkspaceError, match="Container not initialized"):
            export_from_container(mock_docker_tools, "/some/export/dir")

    def test_export_from_container_creates_export_dir(self):
        """Test that export directory is created if it doesn't exist."""
        mock_docker_tools = Mock()
        mock_docker_tools.container_id = "container123"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = os.path.join(temp_dir, "new_export_dir")
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                
                export_from_container(mock_docker_tools, export_dir)
                
                assert os.path.exists(export_dir)
                assert os.path.isdir(export_dir)


class TestCleanupWorkspace:
    """Test workspace cleanup."""
    
    def test_cleanup_workspace_success(self):
        """Test successful workspace cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test workspace directory
            workspace_dir = os.path.join(temp_dir, "test_workspace")
            os.makedirs(workspace_dir)
            
            # Add some files
            (Path(workspace_dir) / "test_file.txt").write_text("test")
            
            cleanup_workspace(workspace_dir)
            
            assert not os.path.exists(workspace_dir)

    def test_cleanup_workspace_nonexistent(self):
        """Test cleanup of non-existent workspace (should not fail)."""
        # Should not raise an exception
        cleanup_workspace("/nonexistent/workspace")

    def test_cleanup_workspace_permission_error(self):
        """Test cleanup with permission error (should not fail)."""
        with patch('shutil.rmtree') as mock_rmtree:
            mock_rmtree.side_effect = OSError("Permission denied")
            
            # Should not raise an exception
            cleanup_workspace("/some/workspace")
            
            mock_rmtree.assert_called_once_with("/some/workspace")


class TestWorkspaceEdgeCases:
    """Test edge cases in workspace utilities."""
    
    def test_validate_files_exist_file_extensions_case_insensitive(self):
        """Test that file extension matching is case insensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with uppercase extensions
            (Path(temp_dir) / "script.PY").write_text("print('test')")
            (Path(temp_dir) / "config.YAML").write_text("key: value")
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_with_subdirectories(self):
        """Test validation with nested subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            nested_dir = Path(temp_dir) / "deeply" / "nested" / "directory"
            nested_dir.mkdir(parents=True)
            (nested_dir / "deep_file.py").write_text("# deep file")
            
            assert validate_files_exist(temp_dir) is True

    def test_validate_files_exist_ignores_common_build_dirs(self):
        """Test that common build/cache directories are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create build directories with files
            for build_dir in ['node_modules', '__pycache__', 'build', 'dist', 'target']:
                dir_path = Path(temp_dir) / build_dir
                dir_path.mkdir()
                (dir_path / "file.txt").write_text("build artifact")
            
            # Should not find any valid files
            assert validate_files_exist(temp_dir) is False

    def test_validate_files_exist_with_readme_variants(self):
        """Test validation with README file variants."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "readme").write_text("# Readme")
            
            assert validate_files_exist(temp_dir) is True