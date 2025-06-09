"""Workspace management for kodx operations."""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .git_utils import GitError, get_repo_root, resolve_ref
from .utils import docker_cp as _docker_cp

logger = logging.getLogger(__name__)


class WorkspaceError(Exception):
    """Workspace operation error."""

    pass


def _run_git_command(cmd: list[str], cwd: str, error_msg: str) -> subprocess.CompletedProcess:
    """Run a git command with error handling.

    Args:
        cmd: Git command as list
        cwd: Working directory
        error_msg: Error message prefix

    Returns:
        Completed process

    Raises:
        WorkspaceError: If command fails
    """
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        raise WorkspaceError(f"{error_msg}: {stderr}")
    except FileNotFoundError:
        raise WorkspaceError("Git not found. Make sure git is installed and in PATH")


def create_temporary_workspace() -> str:
    """Create a temporary workspace directory.

    Returns:
        Path to temporary workspace directory
    """
    return tempfile.mkdtemp(prefix="kodx-workspace-")


def setup_clean_checkout(workspace_dir: str, repo_path: str, commit_sha: str) -> str:
    """Set up a clean checkout of a specific commit in the workspace.

    Args:
        workspace_dir: Temporary workspace directory
        repo_path: Source repository path
        commit_sha: Commit SHA to checkout

    Returns:
        Path to the repository clone in workspace

    Raises:
        WorkspaceError: If setup fails
    """
    repo_dir = os.path.join(workspace_dir, "repo")

    # Clone the repository
    _run_git_command(["git", "clone", repo_path, repo_dir], workspace_dir, "Failed to clone repository")

    # Checkout the specific commit
    _run_git_command(["git", "checkout", commit_sha], repo_dir, f"Failed to checkout commit {commit_sha}")

    return repo_dir


def setup_dirty_copy(workspace_dir: str, repo_path: str) -> str:
    """Set up a copy including working directory changes.

    Args:
        workspace_dir: Temporary workspace directory
        repo_path: Source repository path

    Returns:
        Path to the repository copy in workspace

    Raises:
        WorkspaceError: If setup fails
    """
    repo_dir = os.path.join(workspace_dir, "repo")

    try:
        # Get the repository root to ensure we copy the whole repo
        repo_root = get_repo_root(repo_path)

        # Copy the entire repository including working directory
        shutil.copytree(repo_root, repo_dir, symlinks=True)

        return repo_dir
    except (shutil.Error, OSError) as e:
        raise WorkspaceError(f"Failed to copy repository: {e}")
    except GitError as e:
        raise WorkspaceError(f"Git error: {e}")


async def copy_to_container(docker_tools, workspace_repo_dir: str) -> None:
    """Copy workspace repository to container.

    Args:
        docker_tools: DockerCodexTools instance
        workspace_repo_dir: Path to repository in workspace

    Raises:
        WorkspaceError: If copy fails
    """
    try:
        # Create workspace directory in container
        await docker_tools.feed_chars("mkdir -p /workspace/repo")

        # Copy files using docker cp
        container_id = docker_tools.container_id
        if not container_id:
            raise WorkspaceError("Container not initialized")

        _docker_cp(
            f"{workspace_repo_dir}/.",
            f"{container_id}:/workspace/repo/",
            logger,
        )

        # Set working directory to repo
        await docker_tools.feed_chars("cd /workspace/repo")

    except Exception as e:
        raise WorkspaceError(f"Failed to copy to container: {e}")


def export_from_container(docker_tools, export_dir: str) -> bool:
    """Export changes from container to host directory.

    Args:
        docker_tools: DockerCodexTools instance
        export_dir: Host directory to export to

    Returns:
        True if export successful, False if no changes to export

    Raises:
        WorkspaceError: If export fails
    """
    container_id = docker_tools.container_id
    if not container_id:
        raise WorkspaceError("Container not initialized")

    # Create export directory if it doesn't exist
    os.makedirs(export_dir, exist_ok=True)

    try:
        # Try to copy /workspace/repo first, then fallback to /workspace
        result = _docker_cp(
            f"{container_id}:/workspace/repo/.",
            f"{export_dir}/",
            logger,
            check=False,
        )

        if result.returncode == 0:
            return True

        # Fallback to /workspace
        _docker_cp(
            f"{container_id}:/workspace/.",
            f"{export_dir}/",
            logger,
        )
        return True

    except RuntimeError as e:
        cause = e.__cause__
        stderr = cause.stderr.decode() if getattr(cause, "stderr", None) else ""
        if "No such file or directory" in stderr:
            return False  # No files to export
        raise WorkspaceError(f"Failed to export from container: {e}")


async def setup_git_environment(docker_tools) -> None:
    """Ensure git is available and properly configured in container.

    Args:
        docker_tools: DockerCodexTools instance

    Raises:
        WorkspaceError: If git setup fails
    """
    try:
        # Check if git is available
        git_check_result = await docker_tools.feed_chars("which git || echo 'GIT_NOT_FOUND'")
        if "GIT_NOT_FOUND" in git_check_result:
            # Install git
            install_result = await docker_tools.feed_chars("apt-get update && apt-get install -y git")
            if "unable to locate package git" in install_result.lower() or "error" in install_result.lower():
                raise WorkspaceError("Failed to install git in container")

        # Set up default gitconfig using docker cp
        module_dir = Path(__file__).parent
        gitconfig_path = module_dir / "container_files" / "gitconfig"
        if not gitconfig_path.exists():
            raise WorkspaceError(f"Gitconfig not found: {gitconfig_path}")

        container_id = docker_tools.container_id
        if not container_id:
            raise WorkspaceError("Container not initialized")

        _docker_cp(str(gitconfig_path), f"{container_id}:/root/.gitconfig", logger)

    except Exception as e:
        raise WorkspaceError(f"Failed to setup git environment: {e}")


def cleanup_workspace(workspace_dir: str) -> None:
    """Clean up temporary workspace directory.

    Args:
        workspace_dir: Workspace directory to remove
    """
    try:
        shutil.rmtree(workspace_dir)
    except OSError:
        # Don't fail if cleanup fails - just warn
        pass


def validate_files_exist(directory: str) -> bool:
    """Check if directory contains files that can be analyzed.

    Args:
        directory: Directory to check

    Returns:
        True if directory contains analyzable files, False otherwise
    """
    if not os.path.exists(directory):
        return False

    # Check for common code file extensions
    code_extensions = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".cs",
        ".rb",
        ".php",
        ".go",
        ".rs",
        ".swift",
        ".kt",
        ".scala",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".vue",
        ".svelte",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".sh",
        ".bash",
        ".ps1",
        ".bat",
        ".dockerfile",
    }

    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common build/cache directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in {"node_modules", "__pycache__", "build", "dist", "target"}
        ]

        for file in files:
            if not file.startswith("."):
                _, ext = os.path.splitext(file.lower())
                if ext in code_extensions or file.lower() in {"makefile", "dockerfile", "readme"}:
                    return True

    return False
