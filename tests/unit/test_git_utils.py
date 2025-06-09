"""Unit tests for git utilities."""

import pytest
from unittest.mock import patch, Mock
import subprocess

from kodx.git_utils import (
    is_git_repo,
    resolve_ref,
    get_current_commit,
    generate_branch_name,
    branch_exists,
    has_new_commits,
    GitError
)


class TestIsGitRepo:
    """Test git repository detection."""
    
    @patch('subprocess.run')
    def test_is_git_repo_true(self, mock_run):
        """Test positive git repo detection."""
        mock_run.return_value = Mock(returncode=0)
        
        assert is_git_repo() is True
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--git-dir"],
            cwd=".",
            capture_output=True,
            check=True,
            text=True
        )

    @patch('subprocess.run')
    def test_is_git_repo_false_not_repo(self, mock_run):
        """Test negative git repo detection - not a repo."""
        mock_run.side_effect = subprocess.CalledProcessError(128, ["git"])
        
        assert is_git_repo() is False

    @patch('subprocess.run')
    def test_is_git_repo_false_git_not_found(self, mock_run):
        """Test negative git repo detection - git not found."""
        mock_run.side_effect = FileNotFoundError()
        
        assert is_git_repo() is False

    @patch('subprocess.run')
    def test_is_git_repo_custom_path(self, mock_run):
        """Test git repo detection with custom path."""
        mock_run.return_value = Mock(returncode=0)
        
        is_git_repo("/custom/path")
        
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--git-dir"],
            cwd="/custom/path",
            capture_output=True,
            check=True,
            text=True
        )


class TestResolveRef:
    """Test git reference resolution."""
    
    @patch('subprocess.run')
    def test_resolve_ref_success(self, mock_run):
        """Test successful reference resolution."""
        mock_run.return_value = Mock(
            stdout="abc123def456\n",
            returncode=0
        )
        
        result = resolve_ref("main")
        
        assert result == "abc123def456"
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "main"],
            cwd=".",
            capture_output=True,
            check=True,
            text=True
        )

    @patch('subprocess.run')
    def test_resolve_ref_invalid_ref(self, mock_run):
        """Test invalid reference resolution."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git"], stderr="fatal: bad revision 'invalid'\n"
        )
        
        with pytest.raises(GitError, match="Invalid reference 'invalid'"):
            resolve_ref("invalid")

    @patch('subprocess.run')
    def test_resolve_ref_git_not_found(self, mock_run):
        """Test reference resolution when git not found."""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(GitError, match="Git not found"):
            resolve_ref("main")

    @patch('subprocess.run')
    def test_resolve_ref_custom_path(self, mock_run):
        """Test reference resolution with custom path."""
        mock_run.return_value = Mock(stdout="abc123\n", returncode=0)
        
        resolve_ref("HEAD", "/custom/path")
        
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "HEAD"],
            cwd="/custom/path",
            capture_output=True,
            check=True,
            text=True
        )


class TestGetCurrentCommit:
    """Test current commit retrieval."""
    
    @patch('kodx.git_utils.resolve_ref')
    def test_get_current_commit(self, mock_resolve):
        """Test getting current commit."""
        mock_resolve.return_value = "abc123def456"
        
        result = get_current_commit()
        
        assert result == "abc123def456"
        mock_resolve.assert_called_once_with("HEAD", ".")

    @patch('kodx.git_utils.resolve_ref')
    def test_get_current_commit_custom_path(self, mock_resolve):
        """Test getting current commit with custom path."""
        mock_resolve.return_value = "def456abc123"
        
        result = get_current_commit("/custom/path")
        
        assert result == "def456abc123"
        mock_resolve.assert_called_once_with("HEAD", "/custom/path")


class TestGenerateBranchName:
    """Test branch name generation."""
    
    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_generate_branch_name_simple(self, mock_get_commit, mock_branch_exists):
        """Test simple branch name generation."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("Add user authentication")
        
        assert result == "kodx/add-user-authentication"
        mock_branch_exists.assert_called_once_with("kodx/add-user-authentication", ".")

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_generate_branch_name_special_chars(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with special characters."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("Fix bug: memory leak & performance!")
        
        assert result == "kodx/fix-bug-memory-leak-performance"
        mock_branch_exists.assert_called_once()

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_generate_branch_name_conflict_with_hash(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with conflict resolution using hash."""
        mock_branch_exists.return_value = True
        mock_get_commit.return_value = "abc123def456789"
        
        result = generate_branch_name("Add feature")
        
        assert result == "kodx/add-feature-abc123de"
        mock_branch_exists.assert_called_once_with("kodx/add-feature", ".")
        mock_get_commit.assert_called_once_with(".")

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_generate_branch_name_conflict_git_error(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with conflict and git error fallback."""
        mock_branch_exists.return_value = True
        mock_get_commit.side_effect = GitError("Git error")
        
        with patch('time.time', return_value=1234567890):
            result = generate_branch_name("Add feature")
            
            assert result == "kodx/add-feature-1234567890"

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_generate_branch_name_length_limit(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with length limiting."""
        mock_branch_exists.return_value = False
        
        long_message = "A" * 100  # Very long commit message
        result = generate_branch_name(long_message)
        
        # Should be limited and have kodx/ prefix
        assert result.startswith("kodx/")
        assert len(result) <= len("kodx/") + 50  # 50 char limit for slug

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_generate_branch_name_custom_path(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with custom path."""
        mock_branch_exists.return_value = False
        
        generate_branch_name("Add feature", "/custom/path")
        
        mock_branch_exists.assert_called_once_with("kodx/add-feature", "/custom/path")


class TestBranchExists:
    """Test branch existence checking."""
    
    @patch('subprocess.run')
    def test_branch_exists_true(self, mock_run):
        """Test positive branch existence check."""
        mock_run.return_value = Mock(returncode=0)
        
        assert branch_exists("feature-branch") is True
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--verify", "refs/heads/feature-branch"],
            cwd=".",
            capture_output=True,
            check=True
        )

    @patch('subprocess.run')
    def test_branch_exists_false(self, mock_run):
        """Test negative branch existence check."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
        
        assert branch_exists("nonexistent-branch") is False

    @patch('subprocess.run')
    def test_branch_exists_custom_path(self, mock_run):
        """Test branch existence check with custom path."""
        mock_run.return_value = Mock(returncode=0)
        
        branch_exists("feature-branch", "/custom/path")
        
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--verify", "refs/heads/feature-branch"],
            cwd="/custom/path",
            capture_output=True,
            check=True
        )


class TestBranchNameEdgeCases:
    """Test edge cases in branch name generation."""
    
    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_empty_commit_message(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with empty commit message."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("")
        
        assert result == "kodx/"  # Just the prefix

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_only_special_chars(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with only special characters."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("!@#$%^&*()")
        
        assert result == "kodx/"  # Should strip to empty

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_leading_trailing_spaces(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with leading/trailing spaces."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("  add feature  ")
        
        assert result == "kodx/add-feature"

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_multiple_separators(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with multiple consecutive separators."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("add---feature___with   spaces")
        
        assert result == "kodx/add-feature-with-spaces"

    @patch('kodx.git_utils.branch_exists')
    @patch('kodx.git_utils.get_current_commit')
    def test_unicode_characters(self, mock_get_commit, mock_branch_exists):
        """Test branch name generation with unicode characters."""
        mock_branch_exists.return_value = False
        
        result = generate_branch_name("Add feature 🚀 with émojis")

        assert result == "kodx/add-feature-with-mojis"
        assert all(c.isascii() for c in result)  # Should be ASCII only


class TestHasNewCommits:
    """Test checking for new commits."""

    @patch('subprocess.run')
    def test_has_new_commits_true(self, mock_run):
        """Return True when commits exist after base."""
        mock_run.return_value = Mock(stdout='1\n', returncode=0)

        assert has_new_commits('abc123') is True
        mock_run.assert_called_once_with(
            ['git', 'rev-list', '--count', 'abc123..HEAD'],
            cwd='.',
            capture_output=True,
            check=True,
            text=True
        )

    @patch('subprocess.run')
    def test_has_new_commits_false(self, mock_run):
        """Return False when no new commits."""
        mock_run.return_value = Mock(stdout='0\n', returncode=0)

        assert has_new_commits('abc123') is False

    @patch('subprocess.run')
    def test_has_new_commits_error(self, mock_run):
        """Raise GitError on git failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ['git'], stderr=b'error')

        with pytest.raises(GitError, match='Failed to check commits'):
            has_new_commits('abc123')
