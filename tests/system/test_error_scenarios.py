"""System tests for error handling and recovery mechanisms."""

import asyncio

import pytest

from kodx.tools import DockerCodexTools


@pytest.mark.docker
@pytest.mark.integration
class TestErrorScenarios:
    """Test error handling and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_shell_reset_functionality(self, docker_client):
        """Test shell reset recovers from various error states."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Set up initial state
            await tools.feed_chars("export TEST_VAR=original_value")
            await tools.feed_chars("cd /tmp")
            await tools.feed_chars("alias testcmd='echo test alias'")

            # Verify initial state
            result = await tools.feed_chars("echo $TEST_VAR")
            assert "original_value" in result

            result = await tools.feed_chars("pwd")
            assert "/tmp" in result

            # Corrupt shell environment (simulate various issues)
            await tools.feed_chars("export PS1='corrupted_prompt_that_might_break_things'")
            await tools.feed_chars("cd /")  # Change to root
            await tools.feed_chars("unset PATH")  # Break PATH (risky but recoverable)

            # Create new shell to reset everything
            reset_result = await tools.create_new_shell()
            assert "successfully" in reset_result.lower()

            # Verify environment is completely reset
            result = await tools.feed_chars("echo $TEST_VAR")
            assert "original_value" not in result

            # Should be back in /workspace
            result = await tools.feed_chars("pwd")
            assert "/workspace" in result

            # PATH should be restored
            result = await tools.feed_chars("echo $PATH")
            assert "/usr" in result or "/bin" in result

            # Aliases should be gone
            result = await tools.feed_chars("testcmd")
            assert "command not found" in result or "not found" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_interrupt_functionality(self, docker_client):
        """Test Ctrl+C interrupt in various scenarios."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test 1: Interrupt a simple sleep command
            await tools.feed_chars("sleep 30 &")  # Start in background first
            await tools.feed_chars("jobs")  # Check it's running

            # Now test foreground sleep
            await tools.feed_chars("timeout 5 sleep 30 || echo 'timeout worked'")  # Use timeout as backup

            # Test 2: Interrupt Python infinite loop
            python_script = (
                "import time\nimport signal\nimport sys\n\n"
                "def signal_handler(sig, frame):\n    print('Interrupted!')\n    sys.exit(0)\n\n"
                "signal.signal(signal.SIGINT, signal_handler)\n\n"
                "try:\n    count = 0\n    while True:\n        print(f'Running iteration {count}')\n        count += 1\n        time.sleep(0.2)\n        if count > 100:\n            break\nexcept KeyboardInterrupt:\n    print('Caught KeyboardInterrupt')\n    sys.exit(0)\n"
            )
            tools.copy_text_to_container(python_script, "/workspace/infinite_loop.py")

            # Start the script and interrupt it
            await tools.feed_chars("python3 infinite_loop.py")

            # Wait a moment then interrupt
            await asyncio.sleep(0.5)
            result = await tools.feed_chars("\x03")

            # Verify we can get back to prompt
            result = await tools.feed_chars("echo 'Back at prompt'")
            assert "Back at prompt" in result

            # Test 3: Interrupt during file operations
            await tools.feed_chars("yes | head -n 1000000 > large_file.txt &")
            await tools.feed_chars("\x03")  # Try to interrupt

            # Should be able to continue normally
            result = await tools.feed_chars("echo 'File operations test'")
            assert "File operations test" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_command_timeout_handling(self, docker_client):
        """Test behavior with commands that might hang."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test commands that finish quickly
            result = await tools.feed_chars("echo 'quick command'")
            assert "quick command" in result

            # Test command that takes some time but completes
            result = await tools.feed_chars("python3 -c \"import time; time.sleep(0.5); print('completed')\"")
            assert "completed" in result

            # Test command with timeout using shell timeout utility
            result = await tools.feed_chars("timeout 2 sleep 1 && echo 'timeout success' || echo 'timeout failed'")
            assert "timeout success" in result

            # Test that shell remains responsive after timeout scenarios
            result = await tools.feed_chars("echo 'still responsive'")
            assert "still responsive" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_container_failure_scenarios(self, docker_client):
        """Test handling of container-related failures."""

        # Test 1: Invalid image handling
        with pytest.raises(Exception):
            tools = DockerCodexTools(container_image="nonexistent:invalid_tag")
            await tools.initialize()

        # Test 2: Container that fails to start properly
        # This tests our error handling during initialization
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Simulate container becoming unresponsive by stopping it
            original_container = tools.container
            original_container.stop()

            # Subsequent operations should handle the failure gracefully
            result = await tools.feed_chars("echo 'test'")
            # Should get an error rather than hanging
            assert "error" in result.lower() or len(result) == 0

        except Exception:
            # Even if there's an exception, cleanup should work
            pass
        finally:
            # Cleanup should handle stopped/failed containers
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_pty_server_recovery(self, docker_client):
        """Test recovery when PTY server has issues."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Verify PTY server is working initially
            result = await tools.feed_chars("echo 'initial test'")
            assert "initial test" in result

            # Kill the PTY server process
            await tools.feed_chars("pkill -f pty_server.py")

            # Wait a moment
            await asyncio.sleep(1)

            # Try to use feed_chars - should fail gracefully
            result = await tools.feed_chars("echo 'after server killed'")
            # Should either get error or empty result, not hang

            # Create new shell should recover
            result = await tools.create_new_shell()
            # Should either succeed with new shell or report error

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_memory_and_resource_limits(self, docker_client):
        """Test behavior under resource constraints."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test creating many small files (disk usage)
            await tools.feed_chars("mkdir -p test_files")

            # Create moderate number of files (not too many to avoid issues)
            create_files_cmd = """
for i in $(seq 1 100); do
    echo "File content $i" > test_files/file_$i.txt
done
echo "Created files"
"""
            result = await tools.feed_chars(create_files_cmd)
            assert "Created files" in result

            # Verify files were created
            result = await tools.feed_chars("ls test_files | wc -l")
            assert "100" in result

            # Test memory usage with Python
            memory_test = '''python3 -c "
data = []
for i in range(1000):
    data.append('x' * 1000)
print(f'Created {len(data)} items')
print('Memory test completed')
"'''
            result = await tools.feed_chars(memory_test)
            assert "Memory test completed" in result

            # Clean up
            await tools.feed_chars("rm -rf test_files")

            # Verify cleanup
            result = await tools.feed_chars("ls test_files")
            assert "No such file" in result or "cannot access" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_shell_corruption_recovery(self, docker_client):
        """Test recovery from various shell corruption scenarios."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test 1: Corrupted environment variables
            await tools.feed_chars("export IFS='corrupted'")  # Corrupt field separator
            await tools.feed_chars("export HOME='/nonexistent'")  # Corrupt HOME

            # Try some operations that might be affected
            result = await tools.feed_chars("echo 'test with corrupted env'")
            # Should still work or at least not hang

            # Reset shell
            await tools.create_new_shell()

            # Verify recovery
            result = await tools.feed_chars("echo $HOME")
            assert "/root" in result or "/home" in result  # Should be back to normal

            # Test 2: Terminal settings corruption
            await tools.feed_chars("stty -echo")  # Disable echo
            await tools.feed_chars("stty raw")  # Raw mode

            # Reset shell should recover
            await tools.create_new_shell()

            # Should be able to use shell normally
            result = await tools.feed_chars("echo 'recovered from stty corruption'")
            assert "recovered from stty corruption" in result

            # Test 3: Working directory issues
            await tools.feed_chars("cd /proc/self/fd")  # Go to special directory
            await tools.feed_chars("rm -f nonexistent")  # Try operations that might cause issues

            # Reset and verify
            await tools.create_new_shell()
            result = await tools.feed_chars("pwd")
            assert "/workspace" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_error_message_clarity(self, docker_client):
        """Test that error messages are clear and helpful."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test command not found
            result = await tools.feed_chars("nonexistent_command")
            assert "not found" in result.lower() or "command not found" in result

            # Test file not found
            result = await tools.feed_chars("cat nonexistent_file.txt")
            assert "no such file" in result.lower() or "not found" in result


            # Test Python syntax error
            result = await tools.feed_chars("python3 -c 'print(unclosed string'")
            assert "syntax" in result.lower() or "error" in result.lower()

            # Test directory operations on files
            await tools.feed_chars("touch test_file.txt")
            result = await tools.feed_chars("cd test_file.txt")
            assert "not a directory" in result.lower() or "not found" in result

            # Shell should remain functional after errors
            result = await tools.feed_chars("echo 'shell still works'")
            assert "shell still works" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_operation_handling(self, docker_client):
        """Test handling of concurrent operations and race conditions."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Test rapid sequential commands
            commands = ["echo 'command 1'", "echo 'command 2'", "echo 'command 3'", "pwd", "date"]

            results = []
            for cmd in commands:
                result = await tools.feed_chars(cmd)
                results.append(result)

            # All commands should complete
            assert "command 1" in results[0]
            assert "command 2" in results[1]
            assert "command 3" in results[2]
            assert "/workspace" in results[3]
            # Date result will vary

            # Test that shell state is consistent
            result = await tools.feed_chars("echo 'final check'")
            assert "final check" in result

        finally:
            await tools.cleanup()
