# Contributing to Kodx

## Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/cccntu/kodx
cd kodx
pip install -e ".[dev]"

# Run tests (multiple tiers available)
make test         # Fast unit tests (no Docker required)
make test-docker  # Integration tests (requires Docker)
make test-all     # Complete test suite

# Code quality
make check        # Format and lint code
make lint         # Check code style
make format       # Auto-format code
```

### Testing Tiers

Kodx uses a tiered testing approach:

- **`make test`** - Fast unit tests (~0.2s, no external dependencies)
- **`make test-docker`** - Docker integration tests (~1-2min, requires Docker)
- **`make test-system`** - System workflow tests (~2-5min, requires Docker)
- **`make test-perf`** - Performance benchmarks (~3-10min, requires Docker)

See [TESTING.md](TESTING.md) for detailed testing documentation.

## Contributing Guidelines

1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Make changes**: Follow existing code style, add tests, update docs
3. **Test**: Run `make check` and `make test` 
4. **Commit**: Use conventional commits (`feat:`, `fix:`, `docs:`, etc.)
5. **Submit PR**: Clear description, reference issues, ensure checks pass

### Code Standards
- Type hints for all functions
- Docstrings for public APIs
- Tests for new functionality
- Follow existing patterns

### Architecture Principles
- **Minimal Interface**: 2 tools only
- **Security First**: No credentials in containers
- **Container Isolation**: Clean environment per execution
- **Unix Philosophy**: Standard shell commands over custom wrappers

## License

By contributing, you agree your contributions will be licensed under Apache License 2.0.
