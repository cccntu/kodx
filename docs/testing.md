# Kodx Testing Documentation

## Testing Strategy Overview

This document outlines the non-LLM functional testing strategy for Kodx. We focus on testing the core infrastructure components without involving actual LLM API calls.

## Test Categories

### 1. Unit Tests
Test individual components in isolation with mocked dependencies.

### 2. Integration Tests  
Test component interactions with real Docker containers but without LLM calls.

### 3. System Tests
Test complete workflows by directly calling tool methods.

## Test Structure

```
tests/
├── unit/
│   ├── test_codex_shell.py        # CodexShell component tests
│   ├── test_docker_tools.py       # DockerCodexTools tests
│   ├── test_config.py             # Configuration generation tests
│   └── test_cli.py                # CLI argument parsing tests
├── integration/
│   ├── test_container_lifecycle.py # Docker container management
│   ├── test_pty_server.py          # PTY server deployment and communication
│   └── test_shell_interaction.py   # End-to-end shell command execution
├── system/
│   ├── test_workflows.py           # Complete development workflows
│   └── test_error_scenarios.py     # Error handling and recovery
└── conftest.py                     # Shared fixtures and configuration
```

## Detailed Test Specifications

### Unit Tests

#### `test_codex_shell.py`
**Purpose**: Test CodexShell PTY interaction without Docker containers.

**Test Cases**:
- **`test_pty_server_code_generation()`**
  - Verify `_get_pty_server_code()` reads `pty_server.py` and returns valid Python code
  - Check that code contains required endpoints (/open, /read, /write, /kill, /healthcheck)
  - Validate that code is syntactically correct Python

- **`test_shell_initialization_validation()`**
  - Test prerequisite checking logic (bash, python3, curl detection)
  - Verify error handling for missing prerequisites
  - Test command construction for curl installation

- **`test_command_encoding()`**
  - Test proper escaping of shell commands in HTTP requests
  - Verify handling of special characters (quotes, newlines, control chars)
  - Test encoding/decoding of command output

#### `test_docker_tools.py`
**Purpose**: Test DockerCodexTools class functionality with mocked Docker.

**Test Cases**:
- **`test_tool_registration()`**
  - Verify `@register_tool` decorators work on class methods
  - Check tool metadata is properly attached
  - Validate tool names and descriptions

- **`test_initialization_parameters()`**
  - Test container image parameter handling
  - Verify container naming logic
  - Test Docker client configuration
  - Test network isolation parameter (`disable_network_after_setup`)

- **`test_cleanup_logic()`**
  - Test resource cleanup order (shell → container)
  - Verify cleanup handles missing resources gracefully
  - Test cleanup during error conditions

#### `test_config.py`
**Purpose**: Test configuration generation and validation.

**Test Cases**:
- **`test_default_config_generation()`**
  - Verify `create_default_config()` produces valid TOML
  - Test configuration with different Docker images
  - Validate required sections are present (model, prompt, parameters)

- **`test_config_template_substitution()`**
  - Test Docker image name substitution in system prompt
  - Verify tool descriptions are included correctly
  - Test temporary file creation and cleanup

#### `test_cli.py`
**Purpose**: Test CLI argument parsing and validation without execution.

**Test Cases**:
- **`test_argument_parsing()`**
  - Test all CLI flags and options
  - Verify default values
  - Test argument validation (file existence, etc.)

- **`test_config_path_handling()`**
  - Test default config creation when no path provided
  - Test custom config loading
  - Verify error handling for invalid config paths

### Integration Tests

#### `test_container_lifecycle.py`
**Purpose**: Test Docker container management with real Docker daemon.

**Test Cases**:
- **`test_container_creation_and_cleanup()`**
  ```python
  async def test_container_creation_and_cleanup():
      tools = DockerCodexTools(container_image="python:3.11-slim")

      # Test container creation
      await tools.initialize()
      assert tools.container is not None
      assert tools.container.status == "running"

      # Test cleanup
      await tools.cleanup()
      # Verify container is stopped and removed
  ```

- **`test_multiple_containers()`**
  - Test creating multiple DockerCodexTools instances
  - Verify containers don't conflict (unique names)
  - Test parallel initialization and cleanup

- **`test_container_with_different_images()`**
  - Test with python:3.11, ubuntu:22.04, node:18
  - Verify image pulling if not present
  - Test error handling for invalid images

- **`test_network_isolation()`**
  - Test container with `disable_network_after_setup=True`
  - Verify network access during setup phase
  - Verify network disconnection after setup completes
  - Test that localhost communication (PTY server) still works

#### `test_pty_server.py`
**Purpose**: Test PTY server deployment and HTTP communication.

**Test Cases**:
- **`test_pty_server_deployment()`**
  ```python
  async def test_pty_server_deployment():
      tools = DockerCodexTools()
      await tools.initialize()

      try:
          # Verify PTY server is running
          result = tools.container.exec_run("curl -s http://localhost:1384/healthcheck")
          assert result.exit_code == 0
          assert b"ok" in result.output
      finally:
          await tools.cleanup()
  ```

- **`test_dependency_installation()`**
  - Test fastapi and uvicorn installation
  - Verify curl installation on images that lack it
  - Test handling of pip installation failures

- **`test_server_endpoints()`**
  - Test each PTY server endpoint directly via curl
  - Verify /open creates process and returns PID
  - Test /write and /read for basic communication
  - Test /kill terminates processes correctly

#### `test_shell_interaction.py`
**Purpose**: Test end-to-end shell command execution.

**Test Cases**:
- **`test_basic_command_execution()`**
  ```python
  async def test_basic_command_execution():
      tools = DockerCodexTools()
      await tools.initialize()

      try:
          # Test simple command
          result = await tools.feed_chars("echo 'hello world'")
          assert "hello world" in result

          # Test command with output
          result = await tools.feed_chars("pwd")
          assert "/workspace" in result
      finally:
          await tools.cleanup()
  ```

- **`test_shell_state_persistence()`**
  - Set environment variables, verify they persist
  - Change directory, verify it persists
  - Create files, verify they exist in subsequent commands

- **`test_multiline_commands()`**
  - Test commands with newlines
  - Test file creation using `copy_text_to_container`
  - Test script execution

### System Tests

#### `test_workflows.py`
**Purpose**: Test complete development workflows without LLM involvement.

**Test Cases**:
- **`test_python_development_workflow()`**
  ```python
  async def test_python_development_workflow():
      tools = DockerCodexTools()
      await tools.initialize()

      try:
          # Install package
          result = await tools.feed_chars("pip install requests")
          assert "Successfully installed" in result or "already satisfied" in result

          # Create Python script
          script = """
  import requests
  print("Testing requests library")
  response = requests.get("https://httpbin.org/get")
  print(f"Status: {response.status_code}")
  """

          tools.copy_text_to_container(script, "/workspace/test_script.py")

          # Run script
          result = await tools.feed_chars("python test_script.py")
          assert "Status: 200" in result

          # Verify file was created
          result = await tools.feed_chars("ls -la test_script.py")
          assert "test_script.py" in result
      finally:
          await tools.cleanup()
  ```

- **`test_file_operations_workflow()`**
  - Create, read, modify, delete files
  - Test directory operations
  - Test file permissions

- **`test_package_management_workflow()`**
  - Install packages with pip
  - Test package usage
  - Verify installation persistence

#### `test_error_scenarios.py`
**Purpose**: Test error handling and recovery mechanisms.

**Test Cases**:
- **`test_shell_reset_functionality()`**
  ```python
  async def test_shell_reset_functionality():
      tools = DockerCodexTools()
      await tools.initialize()

      try:
          # Set environment variable
          await tools.feed_chars("export TEST_VAR=original")
          result = await tools.feed_chars("echo $TEST_VAR")
          assert "original" in result

          # Reset shell
          reset_result = await tools.create_new_shell()
          assert "successfully" in reset_result.lower()

          # Verify environment is reset
          result = await tools.feed_chars("echo $TEST_VAR")
          assert "original" not in result
      finally:
          await tools.cleanup()
  ```

- **`test_interrupt_functionality()`**
  - Start long-running process
  - Send Ctrl+C via feed_chars("\x03")
  - Verify process terminates and prompt returns

- **`test_command_timeout_handling()`**
  - Test commands that hang
  - Verify timeout behavior
  - Test recovery after timeouts

- **`test_container_failure_scenarios()`**
  - Test behavior when Docker daemon is unavailable
  - Test handling of container startup failures
  - Test network connectivity issues
  - Test network isolation edge cases (network already disconnected, etc.)

## Test Configuration

### Test Environment Setup

```python
# conftest.py
import pytest
import docker
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
    tools = DockerCodexTools(container_image="python:3.11-slim")
    await tools.initialize()
    yield tools
    await tools.cleanup()

@pytest.fixture(params=["python:3.11-slim", "ubuntu:22.04"])
def multi_image_tools(request):
    """Test with multiple Docker images."""
    return DockerCodexTools(container_image=request.param)
```

### Test Execution

```bash
# Run all unit tests (fast, no Docker required)
pytest tests/unit/ -v

# Run integration tests (requires Docker)
pytest tests/integration/ -v --tb=short

# Run system tests (full workflows)
pytest tests/system/ -v -s

# Run with specific image
pytest tests/integration/ --image python:3.11

# Run with coverage
pytest tests/ --cov=kodx --cov-report=html

# Run specific test categories
pytest tests/ -m "not slow"  # Skip slow tests
pytest tests/ -k "test_basic"  # Run only basic tests
```

### Test Markers

```python
# pytest.ini
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    docker: marks tests that require Docker
    network: marks tests that require network access
    integration: marks integration tests
    unit: marks unit tests
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/ -v
      - run: pytest tests/system/ -v
```

## Performance Testing

### Benchmarks to Track

- **Container startup time** (target: <30 seconds)
- **Command execution latency** (target: <1 second for simple commands)
- **Memory usage** (baseline container + overhead)
- **PTY server response time** (target: <100ms for HTTP requests)

### Performance Test Implementation

```python
# tests/performance/test_benchmarks.py
import time
import pytest

@pytest.mark.slow
async def test_container_startup_time():
    """Measure container initialization time."""
    start_time = time.time()

    tools = DockerCodexTools()
    await tools.initialize()

    startup_time = time.time() - start_time
    await tools.cleanup()

    # Should start within 30 seconds
    assert startup_time < 30, f"Startup took {startup_time:.2f}s"

@pytest.mark.slow  
async def test_command_execution_speed():
    """Measure command execution latency."""
    tools = DockerCodexTools()
    await tools.initialize()

    try:
        # Warm up
        await tools.feed_chars("echo 'warmup'")

        # Measure simple command
        start_time = time.time()
        await tools.feed_chars("echo 'test'")
        execution_time = time.time() - start_time

        assert execution_time < 1.0, f"Command took {execution_time:.2f}s"
    finally:
        await tools.cleanup()
```

This testing strategy ensures Kodx's core functionality works correctly across different environments and usage patterns without requiring LLM API calls.

---

## Documentation Navigation

[Back to Documentation Index](index.md)
