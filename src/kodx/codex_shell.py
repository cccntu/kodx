"""CodexShell - PTY server shell for code execution environments"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path

from .utils import docker_cp as _docker_cp

logger = logging.getLogger(__name__)


class BashNotFoundError(Exception):
    """Raised when bash is not found in container."""

    pass


class CodexShell:
    """Shell with PTY server for enhanced program interaction.

    Features:
    - stdin: Clean input via HTTP (no echo)
    - stdout/stderr: PTY-enabled (shows REPL output)
    - Ctrl+C support via feed_chars() method
    - Network isolation resilient
    - Best for code execution environments
    """

    def __init__(self, container, shell_pid: int):
        self.container = container
        self.shell_pid = shell_pid
        self._server_installed = False

    @classmethod
    async def create(cls, container) -> "CodexShell":
        """Create a new CodexShell session with PTY server"""
        # Check prerequisites - fail fast with clear error messages
        prerequisites = [
            ("which bash", "bash"),
            ("which python3", "python3"),
            ("which pip3", "pip3"),
            ("which curl", "curl"),
        ]

        for cmd, name in prerequisites:
            result = container.exec_run(cmd)
            if result.exit_code != 0:
                raise BashNotFoundError(
                    f"{name} not found in container. "
                    f"Please use a Docker image with Python 3, pip, bash, and curl installed. "
                    f"Recommended: python:3.11 or python:3.12. "
                    f"For custom images, see documentation on image requirements."
                )

        # Install FastAPI and uvicorn
        logger.info("Installing PTY server dependencies...")
        result = container.exec_run("pip3 install -q fastapi uvicorn")
        if result.exit_code != 0:
            raise Exception(f"Failed to install dependencies: {result.output.decode()}")

        # Deploy PTY server code using docker cp for reliability
        server_file = Path(__file__).parent / "container_files" / "pty_server.py"
        _docker_cp(str(server_file), f"{container.id}:/root/pty_server.py", logger)

        # Start PTY server in background
        container.exec_run("python3 /root/pty_server.py > /dev/null 2>&1 &", detach=True)

        # Wait for server to start and be ready
        await asyncio.sleep(2.0)

        # Test server health with curl
        result = container.exec_run("curl -s http://localhost:1384/healthcheck")
        if result.exit_code != 0 or b"ok" not in result.output:
            raise Exception(f"PTY server health check failed: {result.output}")

        # Create bash session via PTY server
        open_req = {"cmd": ["/bin/bash"], "env": {"PS1": "\\w $ ", "TERM": "xterm", "PYTHONUNBUFFERED": "1"}}

        result = container.exec_run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:1384/open",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(open_req),
            ]
        )

        if result.exit_code != 0:
            raise Exception(f"Failed to create bash session: {result.output}")

        try:
            shell_pid = int(result.output.strip())
        except ValueError as e:
            raise Exception(f"Failed to parse shell PID from response: {result.output}, error: {e}")

        # Create shell instance
        shell = cls(container, shell_pid)
        shell._server_installed = True

        return shell

    async def run(self, chars: str = None, timeout: float = 1.0) -> str:
        """Send characters and read output via PTY server"""
        # Send characters if provided
        if chars is not None:
            # Escape the input properly for shell injection safety
            escaped_chars = chars.replace("'", "'\"'\"'")
            result = self.container.exec_run(
                [
                    "bash",
                    "-c",
                    f"printf '%s\\n' '{escaped_chars}' | curl -s -X POST http://localhost:1384/write/{self.shell_pid} --data-binary @-",
                ]
            )

            if result.exit_code != 0:
                logger.warning("Write failed: %s", result.output)

        # Read output multiple times to get all available output
        total_output = ""
        for i in range(3):  # Try multiple times
            await asyncio.sleep(0.3)

            result = self.container.exec_run(
                ["curl", "-s", "-X", "POST", f"http://localhost:1384/read/{self.shell_pid}", "-d", "8192"]
            )

            if result.exit_code == 0:
                chunk = result.output.decode(errors="replace")
                if chunk:
                    total_output += chunk
                elif i > 0:  # If no more output after first read, we're probably done
                    break

        return total_output

    async def close(self) -> None:
        """Close the shell session"""
        # Kill the bash process via PTY server
        if self._server_installed:
            try:
                self.container.exec_run(["curl", "-s", "-X", "POST", f"http://localhost:1384/kill/{self.shell_pid}"])
            except Exception:
                pass

    @staticmethod
    def _get_pty_server_code() -> str:
        """Return the PTY server code."""
        path = Path(__file__).parent / "container_files" / "pty_server.py"
        return path.read_text()
