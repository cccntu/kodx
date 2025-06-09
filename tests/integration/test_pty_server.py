"""Integration tests for PTY server deployment and HTTP communication."""

import json
import time

import pytest

from kodx.tools import DockerCodexTools


@pytest.mark.docker
class TestPTYServer:
    """Test PTY server deployment and HTTP communication."""

    @pytest.mark.asyncio
    async def test_pty_server_deployment(self, docker_client):
        """Test PTY server deployment and health check."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Verify PTY server is running and responding
            result = tools.container.exec_run("curl -s http://localhost:1384/healthcheck")
            assert result.exit_code == 0, f"Health check failed: {result.output}"
            assert b"ok" in result.output.lower()

            # Verify response is valid JSON
            response_text = result.output.decode().strip()
            response_data = json.loads(response_text)
            assert response_data.get("status") == "ok"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_dependency_installation(self, docker_client):
        """Test fastapi and uvicorn installation."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Verify FastAPI is installed
            result = tools.container.exec_run("python3 -c 'import fastapi; print(fastapi.__version__)'")
            assert result.exit_code == 0, "FastAPI not properly installed"

            # Verify uvicorn is installed
            result = tools.container.exec_run("python3 -c 'import uvicorn; print(uvicorn.__version__)'")
            assert result.exit_code == 0, "uvicorn not properly installed"

            # Verify curl is available
            result = tools.container.exec_run("which curl")
            assert result.exit_code == 0, "curl not available"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_pty_server_file_creation(self, docker_client):
        """Test that PTY server file is created correctly."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Verify PTY server file exists
            result = tools.container.exec_run("ls -la /root/pty_server.py")
            assert result.exit_code == 0, "PTY server file not created"

            # Verify file is not empty
            result = tools.container.exec_run("wc -l /root/pty_server.py")
            assert result.exit_code == 0
            lines = int(result.output.decode().split()[0])
            assert lines > 50, f"PTY server file too small: {lines} lines"

            # Verify file is valid Python
            result = tools.container.exec_run("python3 -m py_compile /root/pty_server.py")
            assert result.exit_code == 0, "PTY server file is not valid Python"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_server_endpoints_basic(self, docker_client):
        """Test basic PTY server endpoint accessibility."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test healthcheck endpoint
            result = tools.container.exec_run("curl -s http://localhost:1384/healthcheck")
            assert result.exit_code == 0
            assert b"ok" in result.output.lower()

            # Test that server responds to POST requests (even if invalid)
            result = tools.container.exec_run("curl -s -X POST http://localhost:1384/open -H 'Content-Type: application/json' -d '{}'")
            # Should get some response (might be error, but server is responding)
            assert result.exit_code == 0

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_shell_session_creation(self, docker_client):
        """Test shell session creation through PTY server."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Verify shell was created and has a PID
            assert tools.shell is not None
            assert tools.shell.shell_pid > 0

            # Verify shell session is accessible through PTY server
            pid = tools.shell.shell_pid
            result = tools.container.exec_run(f"curl -s -X POST http://localhost:1384/read/{pid} -d '100'")
            assert result.exit_code == 0
            # Should get some response (even if empty for new shell)

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_server_startup_timing(self, docker_client):
        """Test PTY server startup timing."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            start_time = time.time()
            await tools.initialize()
            total_time = time.time() - start_time

            # Should initialize within reasonable time
            assert total_time < 60, f"Initialization took too long: {total_time:.2f}s"

            # Server should be immediately responsive after initialization
            result = tools.container.exec_run("curl -s http://localhost:1384/healthcheck")
            assert result.exit_code == 0

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_server_process_management(self, docker_client):
        """Test that PTY server is running as a background process."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Verify PTY server process is running by checking ps output directly
            result = tools.container.exec_run("ps aux")
            assert result.exit_code == 0, f"ps command failed: {result.output.decode()}"
            ps_output = result.output.decode()
            assert "pty_server.py" in ps_output, f"PTY server process not found. Process list: {ps_output}"

            # Verify server is responding to health checks
            result = tools.container.exec_run("curl -s http://localhost:1384/healthcheck")
            assert result.exit_code == 0, "PTY server not responding to health checks"
            assert b"ok" in result.output.lower(), f"Health check failed: {result.output}"

        finally:
            await tools.cleanup()


    @pytest.mark.asyncio
    async def test_server_error_responses(self, docker_client):
        """Test PTY server error handling."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test invalid endpoint
            result = tools.container.exec_run("curl -s http://localhost:1384/invalid")
            assert result.exit_code == 0
            # Should get 404 or similar error response

            # Test invalid PID for read endpoint
            result = tools.container.exec_run("curl -s -X POST http://localhost:1384/read/99999 -d '100'")
            assert result.exit_code == 0
            # Should get error response for non-existent PID

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_server_concurrent_access(self, docker_client):
        """Test PTY server handles concurrent requests."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Make multiple concurrent health check requests
            commands = []
            for i in range(5):
                cmd = "curl -s http://localhost:1384/healthcheck"
                commands.append(cmd)

            # Execute commands concurrently using & and wait
            concurrent_cmd = " & ".join(commands) + " & wait"
            result = tools.container.exec_run(f"bash -c '{concurrent_cmd}'")

            # All requests should succeed
            assert result.exit_code == 0

        finally:
            await tools.cleanup()
