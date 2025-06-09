# Test Suite Overview

This directory contains all functional tests for **Kodx**. The tests are grouped by scope to make it clear which ones require Docker or run full workflows.

```
unit/         # Fast tests for individual modules with no Docker required
integration/  # Validate Docker interactions and container lifecycle
system/       # End-to-end workflow tests exercising real containers
performance/  # Benchmarks and stress tests
```

`conftest.py` provides shared fixtures such as a Docker client and helpers used by multiple categories.

See `../docs/testing.md` for a more detailed description of each category and guidelines on running specific groups via `make` targets.
