# Kodx Testing Guide

Kodx uses a tiered testing approach to allow for fast development cycles while maintaining comprehensive test coverage.

## Test Tiers

### Tier 1: Unit Tests (Fast)
**Command:** `make test`

- **Requirements:** None (no Docker, network, or API access required)
- **Duration:** ~0.2 seconds
- **Tests:** 39 unit tests
- **Coverage:** CLI parsing, tool registration, code generation, mocking

These tests run quickly and can be executed frequently during development. They test core functionality without external dependencies.

### Tier 2: Docker Integration Tests  
**Command:** `make test-docker`

- **Requirements:** Docker daemon running
- **Duration:** ~1-2 minutes (depending on image pulls)
- **Tests:** Container lifecycle, PTY server deployment, shell interaction
- **Coverage:** Real Docker container operations, network communication

These tests verify that Kodx works correctly with actual Docker containers.

### Tier 3: System & Workflow Tests
**Command:** `make test-system`

- **Requirements:** Docker daemon running  
- **Duration:** ~2-5 minutes
- **Tests:** Complete development workflows, error recovery, file operations
- **Coverage:** End-to-end scenarios, real development tasks

These tests simulate complete user workflows and test complex interactions.

### Tier 4: Performance Benchmarks
**Command:** `make test-perf`

- **Requirements:** Docker daemon running
- **Duration:** ~3-10 minutes  
- **Tests:** Startup time, throughput, memory usage, cleanup performance
- **Coverage:** Performance regression detection

These tests measure performance characteristics and can help identify regressions.

### All Tests
**Command:** `make test-all`

- **Requirements:** Docker daemon running
- **Duration:** ~5-15 minutes
- **Tests:** All test tiers combined

Runs the complete test suite.

## Development Workflow

### Quick Development Cycle
```bash
# Fast feedback loop during active development
make check && make test
```

### Pre-commit Checks  
```bash
# Before committing changes
make check && make test-docker
```

### Full Validation
```bash
# Before releasing or major changes
make test-all
```

## Code Quality

### Linting and Formatting
```bash
make lint      # Check code style
make format    # Auto-format code  
make check     # Both format and lint
```

### Development Setup
```bash
make install-dev  # Install with development dependencies
make dev-setup    # Complete development environment setup
```

## CI/CD Integration

The Makefile provides special targets for CI/CD environments:

```bash
make ci-test        # Unit tests only (for fast CI)
make ci-test-docker # Unit + Integration tests (for full CI)
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.docker` - Requires Docker daemon
- `@pytest.mark.slow` - Long-running tests  
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance benchmarks

You can run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run all tests except slow ones  
pytest -m "not slow"

# Run only Docker tests
pytest -m docker
```

## Troubleshooting

### Docker Tests Failing
- Ensure Docker daemon is running: `docker info`
- Check available disk space for images
- Verify network connectivity for image pulls

### Slow Test Performance
- Use `make test` for rapid iteration
- Run `make test-docker` only when needed
- Consider running specific test files: `pytest tests/unit/test_cli.py`

### Test Warnings
- Pytest marker warnings can be ignored (they're registered in pytest.ini)
- Asyncio warnings are expected and don't affect functionality
