"""Performance tests and benchmarks for Kodx."""

import statistics
import time

import pytest

from kodx.tools import DockerCodexTools


@pytest.mark.docker
@pytest.mark.slow
class TestBenchmarks:
    """Performance tests and benchmarks."""

    @pytest.mark.asyncio
    async def test_container_startup_time(self, docker_client):
        """Measure container initialization time."""
        # Test with lightweight image
        start_time = time.time()

        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        startup_time = time.time() - start_time

        try:
            # Should start within 30 seconds (including PTY server setup)
            assert startup_time < 30, f"Startup took {startup_time:.2f}s (target: <30s)"

            # Log performance info
            print(f"\nContainer startup time: {startup_time:.2f}s")

            # Verify container is actually functional
            result = await tools.feed_chars("echo 'startup test'")
            assert "startup test" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_command_execution_speed(self, docker_client):
        """Measure command execution latency."""
        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        try:
            # Warm up the connection
            await tools.feed_chars("echo 'warmup'")

            # Measure multiple simple commands
            execution_times = []
            test_commands = ["echo 'test'", "pwd", "whoami", "date", "echo $HOME"]

            for cmd in test_commands:
                start_time = time.time()
                result = await tools.feed_chars(cmd)
                execution_time = time.time() - start_time
                execution_times.append(execution_time)

                # Verify command actually worked
                assert len(result) > 0, f"Command '{cmd}' produced no output"

            # Calculate statistics
            avg_time = statistics.mean(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)

            print("\nCommand execution times:")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Min: {min_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")

            # Performance targets
            assert avg_time < 1.0, f"Average execution time {avg_time:.3f}s exceeds 1.0s target"
            assert max_time < 2.0, f"Max execution time {max_time:.3f}s exceeds 2.0s target"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_memory_usage_baseline(self, docker_client):
        """Measure baseline memory usage."""
        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        try:
            # Get memory usage after initialization
            result = await tools.feed_chars("cat /proc/meminfo | grep MemAvailable")
            mem_available = result.strip()

            # Get container memory stats via Docker API
            stats = tools.container.stats(stream=False)
            memory_usage = stats["memory_stats"]["usage"]
            memory_limit = stats["memory_stats"]["limit"]

            memory_usage_mb = memory_usage / (1024 * 1024)
            memory_limit_mb = memory_limit / (1024 * 1024)

            print("\nMemory usage:")
            print(f"  Container usage: {memory_usage_mb:.1f} MB")
            print(f"  Container limit: {memory_limit_mb:.1f} MB")
            print(f"  Available in container: {mem_available}")

            # Baseline check - should use reasonable amount of memory
            assert memory_usage_mb < 500, f"Memory usage {memory_usage_mb:.1f}MB seems excessive"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_pty_server_response_time(self, docker_client):
        """Measure PTY server HTTP response time."""
        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        try:
            # Measure direct PTY server response times
            response_times = []

            for i in range(10):
                start_time = time.time()
                result = tools.container.exec_run("curl -s http://localhost:1384/healthcheck")
                response_time = time.time() - start_time
                response_times.append(response_time)

                assert result.exit_code == 0
                assert b"ok" in result.output.lower()

            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)

            print("\nPTY server response times:")
            print(f"  Average: {avg_response_time:.3f}s")
            print(f"  Max: {max_response_time:.3f}s")

            # PTY server should respond quickly
            assert avg_response_time < 0.1, f"Average response time {avg_response_time:.3f}s exceeds 0.1s target"
            assert max_response_time < 0.5, f"Max response time {max_response_time:.3f}s exceeds 0.5s target"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_throughput_multiple_commands(self, docker_client):
        """Test throughput with multiple rapid commands."""
        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        try:
            # Measure throughput with many commands
            num_commands = 20
            commands = [f"echo 'command {i}'" for i in range(num_commands)]

            start_time = time.time()

            for i, cmd in enumerate(commands):
                result = await tools.feed_chars(cmd)
                assert f"command {i}" in result

            total_time = time.time() - start_time
            throughput = num_commands / total_time

            print("\nThroughput test:")
            print(f"  {num_commands} commands in {total_time:.2f}s")
            print(f"  Throughput: {throughput:.1f} commands/second")

            # Should handle at least 5 commands per second
            assert throughput > 5, f"Throughput {throughput:.1f} cmd/s is below 5 cmd/s target"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_shell_reset_performance(self, docker_client):
        """Measure performance of shell reset operation."""
        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        try:
            # Set up some shell state
            await tools.feed_chars("export TEST_VAR=value")
            await tools.feed_chars("cd /tmp")

            # Measure shell reset time
            reset_times = []

            for i in range(3):  # Test multiple resets
                start_time = time.time()
                result = await tools.create_new_shell()
                reset_time = time.time() - start_time
                reset_times.append(reset_time)

                assert "successfully" in result.lower()

                # Verify reset worked
                result = await tools.feed_chars("pwd")
                assert "/workspace" in result

            avg_reset_time = statistics.mean(reset_times)
            max_reset_time = max(reset_times)

            print("\nShell reset performance:")
            print(f"  Average: {avg_reset_time:.2f}s")
            print(f"  Max: {max_reset_time:.2f}s")

            # Shell reset should be reasonably fast
            assert avg_reset_time < 10, f"Average reset time {avg_reset_time:.2f}s exceeds 10s target"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_startup_time_different_images(self, docker_client):
        """Compare startup times across different images."""
        images_to_test = ["python:3.11", "python:3.12"]

        startup_times = {}

        for image in images_to_test:
            start_time = time.time()

            tools = DockerCodexTools(container_image=image)
            try:
                await tools.initialize()
                startup_time = time.time() - start_time
                startup_times[image] = startup_time

                # Verify functionality
                result = await tools.feed_chars("echo 'test'")
                assert "test" in result

                print(f"\nStartup time for {image}: {startup_time:.2f}s")

            finally:
                await tools.cleanup()

        # Compare startup times
        startup_times.get("python:3.11", 0)
        startup_times.get("python:3.12", 0)

        print("\nStartup time comparison:")
        for image, time_taken in startup_times.items():
            print(f"  {image}: {time_taken:.2f}s")

        # Both should complete within reasonable time
        for image, time_taken in startup_times.items():
            assert time_taken < 60, f"{image} startup took {time_taken:.2f}s (exceeds 60s)"

    @pytest.mark.asyncio
    async def test_large_output_handling(self, docker_client):
        """Test performance with large command outputs."""
        tools = DockerCodexTools(container_image="python:3.11")
        await tools.initialize()

        try:
            # Test progressively larger outputs
            output_sizes = [100, 500, 1000]  # Number of lines

            for size in output_sizes:
                start_time = time.time()

                # Generate output of specified size
                result = await tools.feed_chars(f"python3 -c \"for i in range({size}): print(f'Line {{i}}: This is a test line with some content')\"")

                execution_time = time.time() - start_time

                # Verify we got the expected amount of output
                line_count = len([line for line in result.split("\n") if line.strip()])

                print(f"\nLarge output test ({size} lines):")
                print(f"  Execution time: {execution_time:.2f}s")
                print(f"  Lines received: {line_count}")
                print(f"  Output size: {len(result)} characters")

                # Should handle large outputs reasonably well
                assert execution_time < 5, f"Large output ({size} lines) took {execution_time:.2f}s"
                assert line_count >= size * 0.8, f"Only received {line_count}/{size} lines"

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_performance(self, docker_client):
        """Measure cleanup operation performance."""
        cleanup_times = []

        for i in range(3):
            tools = DockerCodexTools(container_image="python:3.11")
            await tools.initialize()

            # Do some work to create state
            await tools.feed_chars("mkdir -p test_dir")
            await tools.feed_chars("echo 'test' > test_file.txt")

            # Measure cleanup time
            start_time = time.time()
            await tools.cleanup()
            cleanup_time = time.time() - start_time
            cleanup_times.append(cleanup_time)

        avg_cleanup_time = statistics.mean(cleanup_times)
        max_cleanup_time = max(cleanup_times)

        print("\nCleanup performance:")
        print(f"  Average: {avg_cleanup_time:.2f}s")
        print(f"  Max: {max_cleanup_time:.2f}s")

        # Cleanup should be fast
        assert avg_cleanup_time < 5, f"Average cleanup time {avg_cleanup_time:.2f}s exceeds 5s target"
        assert max_cleanup_time < 10, f"Max cleanup time {max_cleanup_time:.2f}s exceeds 10s target"
