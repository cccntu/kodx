"""Shared test fixtures and configuration for Kodx tests."""

import docker
import pytest

from kodx.tools import DockerCodexTools


@pytest.fixture(scope="session")
def docker_client():
    """Provide Docker client for tests."""
    try:
        client = docker.from_env()
        client.ping()  # Verify Docker is available
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture
async def docker_tools():
    """Provide initialized DockerCodexTools instance."""
    tools = DockerCodexTools(container_image="python:3.11")
    await tools.initialize()
    yield tools
    await tools.cleanup()


@pytest.fixture(params=["python:3.11", "python:3.12"])
def multi_image_tools(request):
    """Test with multiple Docker images."""
    return DockerCodexTools(container_image=request.param)


# Remove deprecated event_loop fixture - use pytest-asyncio defaults


# Test markers
pytestmark = pytest.mark.asyncio
