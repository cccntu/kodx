"""Docker container tools for Kodx."""

import logging
import os
import re
import tempfile

import docker
from llmproc.tools.function_tools import register_tool

from .codex_shell import CodexShell
from .utils import docker_cp as _docker_cp


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from PTY output."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def strip_carriage_returns(text: str) -> str:
    """Normalize line endings by removing carriage returns."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def clean_pty_output(raw_output: str) -> str:
    """Clean PTY server output for easier processing."""
    cleaned = strip_ansi_codes(raw_output)
    cleaned = strip_carriage_returns(cleaned)
    return cleaned


logger = logging.getLogger(__name__)


class SetupError(Exception):
    """Raised when setup script execution fails."""

    pass


class DockerCodexTools:
    """Container tools using CodexShell for enhanced shell interaction."""

    def __init__(self, container_image: str = "python:3.11", container_name: str = None):
        self.container_image = container_image
        self.container_name = container_name or f"kodx-{id(self)}"
        self.container = None
        self.shell = None
        self.shells = {}
        self.docker_client = docker.from_env()

    async def __aenter__(self):
        """Initialize container when entering async context."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Ensure cleanup when exiting async context."""
        await self.cleanup()

    async def initialize(self):
        """Initialize Docker container and CodexShell."""
        try:
            # Create and start container
            self.container = self.docker_client.containers.run(
                self.container_image,
                command="sleep infinity",
                detach=True,
                remove=True,
                name=self.container_name,
                network_mode="bridge",
            )

            # Initialize CodexShell
            self.shell = await CodexShell.create(self.container)
            self.shells["default"] = self.shell

            # Set up basic environment
            await self.shell.run("cd /workspace || mkdir -p /workspace && cd /workspace")
        except Exception:
            # Clean up if initialization fails
            await self.cleanup()
            raise

    @register_tool(
        description=(
            "Feed characters to a session's STDIN. After feeding characters, "
            "wait some amount of time, flush STDOUT/STDERR, and show the "
            "results. Note that a minimum of 250 ms is enforced, so if a "
            "smaller value is provided, it will be overridden with 250 ms."
        ),
        param_descriptions={
            "chars": "Characters to feed; may be empty",
            "shell_name": "Session to feed characters to",
            "yield_time_ms": "How long to wait before reading output in milliseconds",
        },
    )
    async def feed_chars(
        self,
        chars: str,
        shell_name: str = "default",
        yield_time_ms: int = 1000,
    ) -> str:
        r"""Send characters or commands to a shell session.

        Args:
            chars: Characters to feed; may be empty
            shell_name: Session to feed characters to
            yield_time_ms: How long to wait before reading output in milliseconds

        Returns:
            Shell output from the command
        """
        if not self.shells:
            return "Error: Container not initialized"

        shell = self.shells.get(shell_name)
        if not shell:
            return f"Error: Shell '{shell_name}' not found"

        timeout = max(yield_time_ms, 250) / 1000
        raw_output = await shell.run(chars, timeout=timeout)
        return clean_pty_output(raw_output)

    @register_tool(
        name="new_session",
        description="Create a new shell session",
        param_descriptions={
            "shell_name": "Name for the new shell session. Defaults to 'default' which replaces the main session. Use unique names to create additional parallel shell sessions"
        },
    )
    async def create_new_shell(self, shell_name: str = "default") -> str:
        """Create a fresh shell session, resetting the environment.

        Returns:
            Status message about the new shell creation
        """
        if not self.container:
            return "Error: Container not initialized"

        try:
            # Close existing shell with same name
            if shell_name in self.shells:
                await self.shells[shell_name].close()

            # Create new shell session
            new_shell = await CodexShell.create(self.container)
            self.shells[shell_name] = new_shell
            if shell_name == "default":
                self.shell = new_shell

            # Set up basic environment again
            await new_shell.run("cd /workspace || mkdir -p /workspace && cd /workspace")

            return f"New shell '{shell_name}' session created successfully. Working directory: /workspace"
        except Exception as e:
            return f"Error creating new shell: {e}"

    async def execute_setup_script(self, setup_path: str, disable_network_after: bool = False) -> str:
        """Execute setup script in container with clean isolation.

        Args:
            setup_path: Path to setup script on host
            disable_network_after: Disconnect container from networks after setup

        Returns:
            Setup script output

        Raises:
            SetupError: If setup script fails
        """
        if not self.shell:
            raise SetupError("Container not initialized")

        # 1. Validate setup file exists on host
        if not os.path.exists(setup_path):
            raise SetupError(f"Setup script not found: {setup_path}")

        # 2. Read setup script content
        with open(setup_path, encoding="utf-8") as f:
            script_content = f.read()

        # Execute the script content
        return await self.execute_setup_script_content(script_content, disable_network_after)

    async def execute_setup_script_content(self, script_content: str, disable_network_after: bool = False) -> str:
        """Execute setup script content in container with clean isolation.

        Args:
            script_content: Content of the setup script
            disable_network_after: Disconnect container from networks after setup

        Returns:
            Setup script output

        Raises:
            SetupError: If setup script fails
        """
        if not self.shell:
            raise SetupError("Container not initialized")

        # 1. Copy script to /tmp using docker cp (simpler and more reliable)

        # Create a temporary file on host
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write(script_content)
            temp_file_path = temp_file.name

        try:
            # Copy temp file directly to container /tmp/setup.sh
            _docker_cp(temp_file_path, f"{self.container.id}:/tmp/setup.sh", logger)

        except RuntimeError as e:
            raise SetupError(f"Failed to copy setup script to container: {e}") from e
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)

        # 2. Make executable and execute from /workspace
        setup_command = """chmod +x /tmp/setup.sh
cd /workspace && bash /tmp/setup.sh"""

        # 3. Execute setup script
        result = await self.shell.run(setup_command)

        # 4. Check for failure and fail fast
        if self._setup_failed(result):
            raise SetupError(f"Setup script failed: {result}")

        # 5. Disconnect network if requested and setup succeeded
        if disable_network_after:
            await self.disconnect_network()

        return result

    def _setup_failed(self, output: str) -> bool:
        """Detect if setup script failed based on output."""
        if not output:
            return False

        output_lower = output.lower()
        failure_indicators = [
            "command not found",
            "permission denied",
            "no such file",
            "error:",
            "failed",
            "cannot",
            "bash: line",  # Bash syntax errors
            "syntax error",
        ]
        return any(indicator in output_lower for indicator in failure_indicators)

    async def disconnect_network(self) -> None:
        """Disconnect container from all networks after setup is complete."""
        if not self.container:
            return

        try:
            # Reload container to get current network state
            self.container.reload()

            # Disconnect from all networks
            for net in self.container.attrs["NetworkSettings"]["Networks"]:
                network = self.docker_client.networks.get(net)
                network.disconnect(self.container)

        except Exception as e:  # noqa: BLE001
            # Fail fast if network disconnection fails
            logger.exception("Failed to disconnect networks: %s", e)
            raise SetupError(f"Network disconnection failed: {e}") from e

    def copy_text_to_container(self, text: str, dest_path: str) -> None:
        """Copy the given text to a file inside the container."""
        if not self.container:
            raise RuntimeError("Container not initialized")

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        try:
            _docker_cp(tmp_path, f"{self.container.id}:{dest_path}", logger)
        finally:
            os.unlink(tmp_path)

    @property
    def container_id(self) -> str:
        """Get the container ID for docker cp operations."""
        return self.container.id if self.container else None

    async def cleanup(self):
        """Clean up container and shell resources."""
        for sh in list(self.shells.values()) or ([self.shell] if self.shell else []):
            if not sh:
                continue
            try:
                await sh.close()
            except Exception:
                pass  # Ignore cleanup errors
        self.shells.clear()
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
            except Exception:
                pass  # Ignore cleanup errors
