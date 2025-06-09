"""Integration tests for setup script functionality."""

import os
import tempfile

import pytest

from kodx.tools import DockerCodexTools, SetupError


@pytest.mark.docker
class TestSetupScript:
    """Test setup script execution."""

    @pytest.mark.asyncio
    async def test_basic_setup_script(self, docker_client):
        """Test basic setup script execution."""
        tools = DockerCodexTools(container_image="python:3.11")

        # Create a temporary setup script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("""#!/bin/bash
echo "Setup starting..."
touch setup_test.txt
echo "Setup completed successfully" > setup_test.txt
echo "Current directory: $(pwd)"
ls -la setup_test.txt
""")
            setup_script_path = f.name

        try:
            await tools.initialize()

            # Execute setup script
            result = await tools.execute_setup_script(setup_script_path)

            # Verify setup executed
            assert "Setup starting..." in result
            assert "setup_test.txt" in result

            # Verify the file was created in the container
            check_result = await tools.feed_chars("cat setup_test.txt")
            assert "Setup completed successfully" in check_result

        finally:
            await tools.cleanup()
            os.unlink(setup_script_path)

    @pytest.mark.asyncio
    async def test_setup_script_failure(self, docker_client):
        """Test setup script failure handling."""
        tools = DockerCodexTools(container_image="python:3.11")

        # Create a setup script that will fail
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("""#!/bin/bash
echo "Setup starting..."
nonexistent_command_that_will_fail
echo "This should not appear"
""")
            setup_script_path = f.name

        try:
            await tools.initialize()

            # Setup script should raise SetupError
            with pytest.raises(SetupError) as exc_info:
                await tools.execute_setup_script(setup_script_path)

            assert "Setup script failed" in str(exc_info.value)

        finally:
            await tools.cleanup()
            os.unlink(setup_script_path)

    @pytest.mark.asyncio
    async def test_setup_script_working_directory(self, docker_client):
        """Test that setup script runs in /workspace directory."""
        tools = DockerCodexTools(container_image="python:3.11")

        # Create a setup script that checks working directory
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("""#!/bin/bash
echo "Current working directory: $(pwd)"
echo "Creating file in current directory..."
echo "test content" > workspace_file.txt
ls -la workspace_file.txt
""")
            setup_script_path = f.name

        try:
            await tools.initialize()

            # Execute setup script
            result = await tools.execute_setup_script(setup_script_path)

            # Verify it ran in /workspace
            assert "/workspace" in result
            assert "workspace_file.txt" in result

            # Verify we can access the file from normal shell
            check_result = await tools.feed_chars("cat workspace_file.txt")
            assert "test content" in check_result

        finally:
            await tools.cleanup()
            os.unlink(setup_script_path)

    @pytest.mark.asyncio
    async def test_setup_script_not_found(self, docker_client):
        """Test error handling for non-existent setup script."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Try to execute non-existent setup script
            with pytest.raises(SetupError) as exc_info:
                await tools.execute_setup_script("/nonexistent/setup.sh")

            assert "Setup script not found" in str(exc_info.value)

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_setup_script_package_installation(self, docker_client):
        """Test setup script that installs packages."""
        tools = DockerCodexTools(container_image="python:3.11")

        # Create a setup script that installs a package
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("""#!/bin/bash
echo "Installing requests package..."
pip install requests
echo "Package installation completed"
python3 -c "import requests; print('Requests version:', requests.__version__)"
""")
            setup_script_path = f.name

        try:
            await tools.initialize()

            # Execute setup script
            result = await tools.execute_setup_script(setup_script_path)

            # Verify package was installed
            assert "Installing requests package..." in result
            assert "Successfully installed" in result or "already satisfied" in result

            # Verify package works
            check_result = await tools.feed_chars("python3 -c 'import requests; print(\"Package available\")'")
            assert "Package available" in check_result

        finally:
            await tools.cleanup()
            os.unlink(setup_script_path)
