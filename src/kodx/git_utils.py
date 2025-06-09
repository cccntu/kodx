"""Git utilities for kodx operations."""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Git operation error."""

    pass


def is_git_repo(path: str = ".") -> bool:
    """Check if the given path is within a git repository.

    Args:
        path: Directory path to check (default: current directory)

    Returns:
        True if path is within a git repository, False otherwise
    """
    try:
        result = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=path, capture_output=True, check=True, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def resolve_ref(ref: str, path: str = ".") -> str:
    """Resolve a git reference to a commit SHA.

    Args:
        ref: Git reference (branch, commit, tag, etc.)
        path: Repository path (default: current directory)

    Returns:
        Full commit SHA

    Raises:
        GitError: If reference cannot be resolved
    """
    try:
        result = subprocess.run(["git", "rev-parse", ref], cwd=path, capture_output=True, check=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        raise GitError(f"Invalid reference '{ref}': {stderr}")
    except FileNotFoundError:
        raise GitError("Git not found. Make sure git is installed and in PATH")


def get_current_commit(path: str = ".") -> str:
    """Get the current commit SHA.

    Args:
        path: Repository path (default: current directory)

    Returns:
        Current commit SHA

    Raises:
        GitError: If unable to get current commit
    """
    return resolve_ref("HEAD", path)


def generate_branch_name(commit_message: str, path: str = ".") -> str:
    """Generate a branch name from a commit message.

    Args:
        commit_message: Commit message to convert to branch name
        path: Repository path for conflict checking (default: current directory)

    Returns:
        Generated branch name with kodx/ prefix
    """
    # Clean and slug the commit message
    slug = re.sub(r"[^a-z0-9]+", "-", commit_message.lower()).strip("-")
    # Limit length to keep branch names reasonable
    slug = slug[:50].rstrip("-")

    base_name = f"kodx/{slug}"

    # Check for conflicts
    if branch_exists(base_name, path):
        # Append short commit hash to make it unique
        try:
            current_commit = get_current_commit(path)
            commit_hash = current_commit[:8]
            return f"{base_name}-{commit_hash}"
        except GitError:
            # Fallback to timestamp if we can't get commit
            import time

            timestamp = int(time.time())
            return f"{base_name}-{timestamp}"

    return base_name


def branch_exists(branch_name: str, path: str = ".") -> bool:
    """Check if a branch exists locally.

    Args:
        branch_name: Name of the branch to check
        path: Repository path (default: current directory)

    Returns:
        True if branch exists, False otherwise
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"], cwd=path, capture_output=True, check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def create_branch(branch_name: str, base_ref: Optional[str] = None, path: str = ".") -> None:
    """Create a new branch.

    Args:
        branch_name: Name of the new branch
        base_ref: Reference to branch from (default: current HEAD)
        path: Repository path (default: current directory)

    Raises:
        GitError: If branch creation fails
    """
    cmd = ["git", "checkout", "-b", branch_name]
    if base_ref:
        cmd.append(base_ref)

    try:
        subprocess.run(cmd, cwd=path, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise GitError(f"Failed to create branch '{branch_name}': {stderr}")


def fetch_branch(source_repo: str, branch_name: str, target_branch: str, path: str = ".") -> None:
    """Fetch a branch from another repository.

    Args:
        source_repo: Path to source repository
        branch_name: Branch name in source repository
        target_branch: Target branch name in current repository
        path: Current repository path (default: current directory)

    Raises:
        GitError: If fetch fails
    """
    try:
        subprocess.run(
            ["git", "fetch", source_repo, f"{branch_name}:{target_branch}"], cwd=path, capture_output=True, check=True
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise GitError(f"Failed to fetch branch '{branch_name}': {stderr}")


def get_repo_root(path: str = ".") -> str:
    """Get the root directory of the git repository.

    Args:
        path: Starting path (default: current directory)

    Returns:
        Absolute path to repository root

    Raises:
        GitError: If not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=path, capture_output=True, check=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise GitError(f"Not in a git repository: {os.path.abspath(path)}")


def is_dirty(path: str = ".") -> bool:
    """Check if the working directory has uncommitted changes.

    Args:
        path: Repository path (default: current directory)

    Returns:
        True if there are uncommitted changes, False otherwise
    """
    try:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=path, capture_output=True, check=True, text=True)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def has_new_commits(base_commit: str, path: str = ".") -> bool:
    """Check if repository has commits after the given base commit.

    Args:
        base_commit: Commit SHA or ref to compare against.
        path: Repository path (default: current directory)

    Returns:
        True if there are commits after ``base_commit``.

    Raises:
        GitError: If git command fails.
    """
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{base_commit}..HEAD"],
            cwd=path,
            capture_output=True,
            check=True,
            text=True,
        )
        return int(result.stdout.strip()) > 0
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        raise GitError(f"Failed to check commits: {stderr}")
