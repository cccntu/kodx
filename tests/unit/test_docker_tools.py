"""Unit tests for DockerCodexTools class functionality with mocked Docker."""

import asyncio
from unittest.mock import Mock, patch, AsyncMock, ANY

import pytest

from llmproc.common.metadata import get_tool_meta
from kodx.tools import DockerCodexTools


@pytest.mark.unit
class TestDockerCodexTools:
    """Test DockerCodexTools class functionality with mocked Docker."""

    @pytest.fixture(autouse=True)
    def _mock_docker(self):
        with patch("kodx.tools.docker") as mock_docker:
            mock_docker.from_env.return_value = Mock()
            yield

    def test_tool_registration(self):
        """Verify @register_tool decorators work on class methods."""
        tools = DockerCodexTools()

        # Test that methods have @register_tool metadata
        feed_chars_meta = get_tool_meta(tools.feed_chars.__func__)
        create_new_shell_meta = get_tool_meta(tools.create_new_shell.__func__)

        # Verify metadata exists and is correct
        assert feed_chars_meta.name == "feed_chars"
        assert "feed characters" in feed_chars_meta.description.lower()

        assert create_new_shell_meta.name == "new_session"
        assert "shell session" in create_new_shell_meta.description.lower()

        # Verify methods are callable
        assert callable(tools.feed_chars)
        assert callable(tools.create_new_shell)

    def test_initialization_parameters(self):
        """Test container image parameter handling."""
        # Test default parameters
        tools1 = DockerCodexTools()
        assert tools1.container_image == "python:3.11"
        assert tools1.container_name.startswith("kodx-")
        assert tools1.container is None
        assert tools1.shell is None

        # Test custom parameters
        custom_image = "ubuntu:22.04"
        custom_name = "test-container"
        tools2 = DockerCodexTools(container_image=custom_image, container_name=custom_name)
        assert tools2.container_image == custom_image
        assert tools2.container_name == custom_name

    @patch("kodx.tools.docker")
    def test_docker_client_configuration(self, mock_docker):
        """Test Docker client configuration."""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client

        tools = DockerCodexTools()
        assert tools.docker_client == mock_client
        mock_docker.from_env.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_logic(self):
        """Test resource cleanup order and error handling."""
        tools = DockerCodexTools()

        # Mock shell and container with async methods
        mock_shell = Mock()
        mock_shell.close = Mock(return_value=asyncio.Future())
        mock_shell.close.return_value.set_result(None)

        mock_container = Mock()
        tools.shell = mock_shell
        tools.container = mock_container

        # Test cleanup calls shell.close() then container.stop()
        await tools.cleanup()
        mock_shell.close.assert_called_once()
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    def test_cleanup_handles_missing_resources(self):
        """Verify cleanup handles missing resources gracefully."""
        tools = DockerCodexTools()

        # Test cleanup with no shell or container
        import asyncio

        async def test_cleanup_empty():
            # Should not raise exception
            await tools.cleanup()

        asyncio.run(test_cleanup_empty())

    @pytest.mark.asyncio
    async def test_cleanup_during_error_conditions(self):
        """Test cleanup during error conditions."""
        tools = DockerCodexTools()

        # Mock shell and container with failing methods
        mock_shell = Mock()
        mock_shell.close = Mock(side_effect=Exception("Shell close error"))

        mock_container = Mock()
        mock_container.stop.side_effect = Exception("Container stop error")

        tools.shell = mock_shell
        tools.container = mock_container

        # Should not raise exception even if cleanup methods fail
        await tools.cleanup()
        mock_shell.close.assert_called_once()
        mock_container.stop.assert_called_once()

    def test_container_naming_logic(self):
        """Test container naming logic generates unique names."""
        tools1 = DockerCodexTools()
        tools2 = DockerCodexTools()

        # Should generate different names for different instances
        assert tools1.container_name != tools2.container_name
        assert tools1.container_name.startswith("kodx-")
        assert tools2.container_name.startswith("kodx-")

    def test_tool_method_signatures(self):
        """Test that tool methods have correct signatures."""
        tools = DockerCodexTools()

        # Test feed_chars signature
        import inspect

        feed_chars_sig = inspect.signature(tools.feed_chars)
        params = list(feed_chars_sig.parameters.keys())
        assert "chars" in params
        assert "shell_name" in params
        assert "yield_time_ms" in params

        # Test create_new_shell signature
        create_new_shell_sig = inspect.signature(tools.create_new_shell)
        # Should have no required parameters (besides self)
        required_params = [name for name, param in create_new_shell_sig.parameters.items() if param.default == param.empty and name != "self"]
        assert len(required_params) == 0

    @pytest.mark.asyncio
    async def test_feed_chars_error_handling(self):
        """Test feed_chars handles missing shell gracefully."""
        tools = DockerCodexTools()
        # Don't initialize - shell should be None

        result = await tools.feed_chars("test command")
        assert "Error: Container not initialized" in result

    @pytest.mark.asyncio
    async def test_create_new_shell_error_handling(self):
        """Test create_new_shell handles missing container gracefully."""
        tools = DockerCodexTools()
        # Don't initialize - container should be None

        result = await tools.create_new_shell()
        assert "Error: Container not initialized" in result

    @pytest.mark.asyncio
    async def test_multiple_shell_sessions(self):
        """Test feed_chars with multiple named shells."""
        tools = DockerCodexTools()
        tools.container = Mock()

        shell_a = AsyncMock()
        shell_a.run.return_value = "out_a"
        shell_b = AsyncMock()
        shell_b.run.return_value = "out_b"

        with patch("kodx.tools.CodexShell.create", side_effect=[shell_a, shell_b]):
            await tools.create_new_shell("shell_a")
            await tools.create_new_shell("shell_b")

        result_a = await tools.feed_chars("cmd_a", shell_name="shell_a")
        result_b = await tools.feed_chars("cmd_b", shell_name="shell_b")

        shell_a.run.assert_called_with("cmd_a", timeout=ANY)
        shell_b.run.assert_called_with("cmd_b", timeout=ANY)
        assert result_a == "out_a"
        assert result_b == "out_b"
