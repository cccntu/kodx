"""Utility functions for container operations."""

from __future__ import annotations

import subprocess


def docker_cp(src: str, dest: str, logger, check: bool = True):
    """Run ``docker cp`` command with consistent error handling."""
    cmd = ["docker", "cp", src, dest]
    try:
        return subprocess.run(cmd, check=check, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        logger.error(f"docker cp failed: {stderr}")
        raise RuntimeError(f"docker cp failed: {stderr}") from e
