"""Integration tests for export functionality."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from kodx.tools import DockerCodexTools


@pytest.mark.docker
class TestExportFunctionality:
    """Test export functionality for GitHub automation."""

    @pytest.mark.asyncio
    async def test_export_clean_container(self, docker_client):
        """Test export from clean container (no repo-dir)."""
        tools = DockerCodexTools(container_image="python:3.11")

        with tempfile.TemporaryDirectory() as export_dir:
            try:
                await tools.initialize()

                # Create a test file in clean container
                await tools.feed_chars("echo 'Hello from clean container' > test_clean.txt")
                await asyncio.sleep(0.2)

                # Test the export function from CLI module
                from kodx.core import _export_container_to_host
                import logging
                logger = logging.getLogger(__name__)

                await _export_container_to_host(tools, export_dir, logger)

                # Verify file was exported
                exported_file = Path(export_dir) / "test_clean.txt"
                assert exported_file.exists()

                content = exported_file.read_text().strip()
                assert content == "Hello from clean container"

            finally:
                await tools.cleanup()

    @pytest.mark.asyncio
    async def test_export_with_repo_dir(self, docker_client):
        """Test export with existing repository."""
        tools = DockerCodexTools(container_image="python:3.11")

        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as export_dir:
            try:
                # Create a fake repository structure
                repo_dir = Path(temp_dir) / "fake_repo"
                repo_dir.mkdir()
                (repo_dir / "original.txt").write_text("Original file")

                await tools.initialize()

                # Copy fake repo to container using docker cp
                import subprocess
                cmd = ["docker", "cp", f"{repo_dir}/.", f"{tools.container_id}:/workspace/repo/"]
                subprocess.run(cmd, check=True)

                # Make changes in the container
                await tools.feed_chars("cd /workspace/repo")
                await tools.feed_chars("echo 'Modified content' > modified.txt")
                await tools.feed_chars("echo 'Additional line' >> original.txt")
                await asyncio.sleep(0.5)

                # Test export
                from kodx.core import _export_container_to_host
                import logging
                logger = logging.getLogger(__name__)

                await _export_container_to_host(tools, export_dir, logger)

                # Verify original and new files were exported
                original_file = Path(export_dir) / "original.txt"
                modified_file = Path(export_dir) / "modified.txt"

                assert original_file.exists()
                assert modified_file.exists()

                # Check content
                assert "Original file" in original_file.read_text()
                assert "Additional line" in original_file.read_text()
                assert modified_file.read_text().strip() == "Modified content"

            finally:
                await tools.cleanup()

    @pytest.mark.asyncio
    async def test_export_empty_workspace(self, docker_client):
        """Test export when workspace is empty (should not fail)."""
        tools = DockerCodexTools(container_image="python:3.11")

        with tempfile.TemporaryDirectory() as export_dir:
            try:
                await tools.initialize()

                # Don't create any files

                from kodx.core import _export_container_to_host
                import logging
                logger = logging.getLogger(__name__)

                # Should not raise exception even with empty workspace
                await _export_container_to_host(tools, export_dir, logger)

                # Export directory should exist but might be empty
                assert Path(export_dir).exists()

            finally:
                await tools.cleanup()

    @pytest.mark.asyncio
    async def test_export_creates_directory(self, docker_client):
        """Test that export creates the target directory if it doesn't exist."""
        tools = DockerCodexTools(container_image="python:3.11")

        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "nested" / "export" / "path"

            try:
                await tools.initialize()

                # Create a test file
                await tools.feed_chars("echo 'Test content' > test.txt")
                await asyncio.sleep(0.2)

                from kodx.core import _export_container_to_host
                import logging
                logger = logging.getLogger(__name__)

                await _export_container_to_host(tools, str(export_dir), logger)

                # Verify directory was created and file exported
                assert export_dir.exists()
                test_file = export_dir / "test.txt"
                assert test_file.exists()
                assert test_file.read_text().strip() == "Test content"

            finally:
                await tools.cleanup()
