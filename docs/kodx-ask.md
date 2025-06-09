# kodx `ask` Command

Kodx provides a dedicated `ask` subcommand for code analysis and repository questions.

## Purpose

Code analysis with container isolation, designed for read-only analysis of repositories.

**Characteristics**:
- Copies files to container for AI analysis
- Defaults to current directory
- Fails if no relevant files found
- No exports or side effects
- Container isolation ensures analysis doesn't affect host

## Usage

```bash
kodx ask "QUESTION" [OPTIONS]
```

`QUESTION` is a free form string describing what you want to learn about the code. The command runs inside an isolated Docker container with the specified directory copied into the container.

## Common Options

- `--repo-dir DIR` - Directory to analyze (defaults to the current directory).
- `--program FILE` - Path to a custom analysis program.
- `--json` - Output structured JSON result.
- `--json-output-file FILE` - Write JSON output to a file instead of stdout.
- `-q, --quiet` - Reduce output verbosity.
- `--log-level LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR).
- `--cost-limit USD` - Stop execution when cost exceeds this value.
- `--timeout SECONDS` - Stop execution after this many seconds (default 1200).
- `--dry-run` - Print planned actions without starting a container.

## Examples

```bash
# Basic usage in current directory
kodx ask "What does this project do?"

# Analyze a specific directory with a custom program
kodx ask "Security review" --repo-dir ./src --program security.yaml

# Analysis with cost control
kodx ask "Review code quality" --cost-limit 0.50

# Analyze specific path
kodx ask "How can I improve performance?" --repo-dir /specific/path

# Analyze with JSON output
kodx ask "Analyze current work" --json
```

## Error Handling

### No Files to Analyze
```bash
kodx ask "Analyze this" --repo-dir /empty/directory
# ERROR: No files found to analyze in /empty/directory
# kodx ask requires code files to analyze
```

## Requirements

- Requires analyzable files in the target directory
- Fails with clear error if no relevant files found
- Git repository not required (unlike `kodx code`)

---

## Documentation Navigation

[Back to Documentation Index](index.md)
