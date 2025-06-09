# Makefile for Kodx development

.PHONY: setup test test-ci test-docker test-workflows test-performance test-all lint format check clean docs help

# Set help as default target
.DEFAULT_GOAL := help

# Activate the virtual environment if it exists
ifneq ($(wildcard .venv/bin/activate),)
ACTIVATE := . .venv/bin/activate &&
else
ACTIVATE :=
endif

# Convenience wrappers
PYTHON := $(ACTIVATE) python
PYTEST := $(PYTHON) -m pytest

# Default target
help:
	@echo "Kodx Development Commands"
	@echo "============================="
	@echo ""
	@echo "Installation:"
	@echo "  setup        Set up development environment (venv, deps, pre-commit)"
	@echo "  install      Install package for production use"
	@echo "  install-dev  Install package with development dependencies"
	@echo ""
	@echo "Testing (by tier):"
	@echo "  test          Run fast unit tests (no Docker/network/API required)"
	@echo "  test-docker   Run Docker integration + error tests (requires Docker)"
	@echo "  test-workflows Run slow workflow tests (requires Docker, marked as slow)"
	@echo "  test-perf     Run performance benchmarks (requires Docker)"
	@echo "  test-all      Run all tests except slow workflows (requires Docker)"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         Check code style and quality"
	@echo "  format       Auto-format code with ruff"
	@echo "  check        Run both lint and format checks"
	@echo ""
	@echo "Development:"
	@echo "  clean        Clean up build artifacts and cache"
	@echo "  docs         Generate documentation"
	@echo ""
	@echo "Examples:"
	@echo "  make test                    # Fast unit tests only"
	@echo "  make test-docker             # Integration + error tests (needs Docker)"
	@echo "  make test-workflows          # Slow workflow tests (optional)"
	@echo "  make check && make test      # Full code quality + unit tests"

# Setup virtual environment and install dependencies
setup:
	@echo "Setting up virtual environment and installing dependencies"
	uv venv --quiet
	. .venv/bin/activate && uv sync --all-extras --all-groups --quiet
	. .venv/bin/activate && pip install pre-commit
	. .venv/bin/activate && pre-commit install-hooks
	@echo "Setup complete. Activate with: source .venv/bin/activate"

# Installation targets (legacy)
install:
	pip install .

install-dev:
	pip install -e ".[dev]"

# Testing targets by tier

# Tier 1: Fast unit tests (no external dependencies)
test:
	@echo "Running fast unit tests (no Docker/network/API required)..."
	$(PYTEST) tests/unit/ -v --tb=short -x --color=no $(TEST_ARGS)

# Tier 2: Docker integration tests + error scenarios (requires Docker daemon)
test-docker:
	@echo "Running Docker integration tests + error scenarios (requires Docker)..."
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker not found. Please install Docker."; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Error: Docker daemon not running. Please start Docker."; exit 1; }
	$(PYTEST) tests/integration/ tests/system/test_error_scenarios.py -v --tb=short -m docker -n 4 $(TEST_ARGS)

# Tier 3: Slow workflow tests (requires Docker, marked as slow)
test-workflows:
	@echo "Running slow workflow tests (requires Docker, may be slow)..."
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker not found. Please install Docker."; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Error: Docker daemon not running. Please start Docker."; exit 1; }
	$(PYTEST) tests/system/test_workflows.py -v --tb=short -m "workflow and slow" -n 2 $(TEST_ARGS)

# Tier 4: Performance benchmarks (requires Docker, may be slow)
test-perf:
	@echo "Running performance benchmarks (requires Docker, may be slow)..."
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker not found. Please install Docker."; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Error: Docker daemon not running. Please start Docker."; exit 1; }
	$(PYTEST) tests/performance/ -v --tb=short -m "docker and slow" $(TEST_ARGS)

# Run all tests except slow workflows (requires Docker)
test-all:
	@echo "Running all tests except slow workflows (requires Docker)..."
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker not found. Please install Docker."; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Error: Docker daemon not running. Please start Docker."; exit 1; }
	$(PYTEST) tests/ -v --tb=short -m "not workflow" -n 4 $(TEST_ARGS)

# Run tests for CI with coverage (minimal output)
test-ci:
	@echo "Running CI tests with coverage"
	$(PYTEST) tests/unit/ --cov=kodx --cov-report=xml --no-header -p no:warnings

# Code quality targets
lint:
	@echo "Checking code style and quality..."
	$(ACTIVATE) ruff check .
	@echo "Linting complete!"

format:
	@echo "Auto-formatting code..."
	$(ACTIVATE) ruff format .
	@echo "Formatting complete!"

check: format lint
	@echo "Code quality checks passed!"

# Development targets
clean:
	@echo "Cleaning up build artifacts and cache..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .venv
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete!"

docs:
	@echo "Documentation generation not yet implemented."
	@echo "See docs/ directory for existing documentation."

# Special targets for CI/CD
ci-test:
	@echo "Running CI tests (unit tests only)..."
	$(PYTEST) tests/unit/ --tb=short --junitxml=test-results.xml

ci-test-docker:
	@echo "Running CI tests with Docker..."
	$(PYTEST) tests/unit/ tests/integration/ tests/system/test_error_scenarios.py --tb=short --junitxml=test-results.xml -m "not slow and not workflow" -n 4

# Development workflow targets
dev-setup: setup
	@echo "Development environment setup complete!"
	@echo "You can now run: make test"

dev-check: check test
	@echo "Development checks passed! Ready to commit."

# Quick targets for common workflows
quick-test: test
fast-test: test
unit-test: test
integration-test: test-docker
