# Kodx Core Command

The `kodx` core command is the original, general-purpose interface that provides maximum flexibility for containerized LLM-assisted development. Unlike the specialized `kodx ask` and `kodx code` commands, it allows full customization of LLM programs and Docker configurations.

## Synopsis

```bash
kodx [PROGRAM_PATH] [OPTIONS]
```

## Description

The core command executes an LLM program within a Docker container, providing the AI assistant with tools to interact with code through a shell interface. It can use built-in or custom programs and offers complete control over the execution environment.

## Arguments

### PROGRAM_PATH (optional)

Path to an LLM program file in YAML or TOML format. If omitted, uses the built-in default assistant program located at `src/kodx/programs/default.yml`.

## Options

### Prompt Options (required - choose one)

- `--prompt TEXT`, `-p TEXT` - Provide prompt directly on command line
- `--prompt-file FILE`, `-f FILE` - Read prompt from a file
- If neither provided, reads prompt from stdin

### Repository Options

- `--repo-dir DIR` - Local directory to copy into container at `/workspace/repo`
  - Defaults to current directory (`.`) if not specified
  - Use empty string (`""`) for a clean container with no files
  - Can be any relative or absolute path

### Docker Options

- `--image TEXT` - Docker image to use (default: `python:3.11`)
- `--setup-script FILE` - Path to bash script to execute after container initialization
- `--disable-network-after-setup` - Disconnect container from networks after setup completes

### Output Options

- `--json` - Output results as JSON to stdout
- `--json-output-file FILE` - Write JSON results to specified file
- `--quiet`, `-q` - Suppress most output except errors
- `--log-level LEVEL`, `-l LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Control Options

- `--append`, `-a` - Append provided prompt to program's embedded prompt
- `--export-dir DIR` - Export container's `/workspace` to host directory after execution
- `--cost-limit USD` - Stop execution when cost exceeds limit in USD
- `--timeout SECONDS` - Stop execution after this many seconds (default 1200)
- `--help`, `-h` - Show help message and exit

## Default Program

When no program path is specified, kodx uses the built-in default assistant which provides:

- **Model**: Claude Sonnet 4 with Anthropic provider
- **Tools**: `feed_chars` and `create_new_shell` for shell interaction
- **Capabilities**: Code analysis, implementation, debugging, testing, file operations
- **Working Directory**: `/workspace` with optional repository at `/workspace/repo`

## Program File Format

Custom program files define the LLM configuration and behavior:

```yaml
model:
  name: claude-sonnet-4-20250514
  provider: anthropic
  max_iterations: 100

parameters:
  max_tokens: 8000
  temperature: 0.1

docker:
  image: python:3.11
  setup_script: |
    pip install pytest black mypy
    apt-get update && apt-get install -y git
  disable_network_after_setup: false

prompt:
  system: |
    You are an expert software engineer...
    
tools:
  - module: kodx.tools
    class: DockerCodexTools
```

## Usage Examples

### Basic Usage

```bash
# Analyze current directory with default program
kodx --prompt "What is the architecture of this project?"

# Work in clean container
kodx --repo-dir "" --prompt "Create a Python web app with Flask"

# Work with specific directory
kodx --repo-dir ./my-project --prompt "Run the tests and fix any issues"
```

### Custom Programs

```bash
# Use custom program from .github/config
kodx .github/config/kodx-slash-code-program.yaml --prompt "Add logging"

# Use program from .kodx directory (created by kodx init)
kodx .kodx/ask.yaml --prompt "Review the security aspects"

# Custom program with clean container
kodx my-assistant.yaml --repo-dir "" --prompt "Create a CLI tool"

# Experiment in the background
kodx --prompt "start fastapi server app.py and test it"

# Custom program with specific workflow
kodx my-program.yaml --prompt "Run security audit" --cost-limit 2.0
```

### Advanced Options

```bash
# With setup script for dependencies
kodx --repo-dir . --setup-script setup.sh --prompt "Run integration tests"

# With network isolation for security
kodx --repo-dir . --disable-network-after-setup --prompt "Analyze sensitive code"

# Export results to local directory
kodx --repo-dir "" --prompt "Create FastAPI server" --export-dir ./new-app

# Set cost limit
kodx --prompt "Comprehensive code review" --cost-limit 1.00

# Custom Docker image
kodx --image node:18 --repo-dir . --prompt "Run npm audit and fix issues"
```

### Output Formats

```bash
# JSON output to stdout
kodx --prompt "Count lines of code" --json

# JSON output to file
kodx --prompt "Analyze dependencies" --json-output-file analysis.json

# Quiet mode (errors only)
kodx --prompt "Format code" --quiet

# Debug logging
kodx --prompt "Debug failing test" --log-level DEBUG
```

### Pipeline Usage

```bash
# Read prompt from file
kodx --prompt-file requirements.txt

# Pipe prompt from another command
echo "Create a TODO app with SQLite" | kodx --repo-dir ""

# Append to program's system prompt
kodx custom.yaml --prompt "Focus on performance" --append
```

## JSON Output Format

When using `--json` or `--json-output-file`, the output follows this structure:

```json
{
  "command": "core",
  "prompt": "Create a hello world script",
  "api_calls": 3,
  "usd_cost": 0.0125,
  "last_message": "Created hello.py with a simple greeting",
  "stderr": [],
  "stop_reason": "Max iterations reached"
}
```

## Container Environment

The AI assistant operates in a Docker container with:

- **Working Directory**: `/workspace`
- **Repository Location**: `/workspace/repo` (if `--repo-dir` provided)
- **Available Tools**:
  - `feed_chars(chars)` - Feed characters to a session's STDIN and return the output
  - `create_new_shell()` - Start fresh shell session
- **Shell**: Interactive bash with full PTY support

## Differences from Specialized Commands

| Feature | `kodx` (core) | `kodx ask` | `kodx code` |
|---------|---------------|------------|-------------|
| Custom programs | ✓ | ✗ | ✗ |
| Git integration | ✗ | ✗ | ✓ |
| Default workflow | General | Analysis | Implementation |
| Branch creation | ✗ | ✗ | ✓ |
| Flexibility | Maximum | Limited | Limited |

## Common Use Cases

1. **Custom AI Assistants** - Create specialized assistants with custom prompts and tools
2. **One-off Tasks** - Quick operations without predefined workflows
3. **Testing New Models** - Experiment with different LLM providers and models
4. **Complex Workflows** - Combine with shell scripts for automation
5. **Security Analysis** - Use network isolation for sensitive code review

## Tips and Best Practices

1. Use `--repo-dir ""` for tasks that create new projects
2. Set `--cost-limit` for expensive operations
3. Use `--export-dir` to save generated code locally
4. Create reusable program files in `.kodx/` directory
5. Use `--append` to add context without modifying program files
6. Leverage `--setup-script` for complex environment preparation

## See Also

- [`kodx ask`](kodx-ask.md) - Specialized code analysis command
- [`kodx code`](kodx-code.md) - Git-integrated implementation command
- [`kodx init`](quickstart.md#initialization) - Initialize program templates
- [Architecture](architecture.md) - Technical implementation details
- [Docker Configuration](docker-config.md) - Container setup options

---

## Documentation Navigation

[Back to Documentation Index](index.md)
