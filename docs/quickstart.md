# Quick Start Guide

Get up and running with Kodx in under 5 minutes.

## Prerequisites

Before you begin, ensure you have:
- Python 3.11 or higher
- Docker installed and running
- An Anthropic API key (for Claude access)

## Installation

### Option 1: Install from PyPI (Recommended)
```bash
pip install kodx
```

### Option 2: Install from Source
```bash
git clone https://github.com/cccntu/kodx
cd kodx
pip install -e .
```

## Setup

### 1. Configure API Key
```bash
export ANTHROPIC_API_KEY="your-claude-api-key-here"
```

### 2. Verify Installation
```bash
kodx --help
```

### 3. Initialize Repository (optional)
```bash
kodx init
```
Creates a `.kodx` directory with default programs you can customize.

You should see usage instructions for running LLM programs. See the [kodx core command documentation](kodx-core.md) for detailed command syntax and options.

## First Steps

### Interactive Code Execution

Start with basic interactive code execution:

```bash
kodx --repo-dir "" --prompt "Create a simple Python HTTP server and test it"
```

This will:
1. Start a Docker container with Python 3.11
2. Give Claude access to the shell via `feed_chars` and `create_new_shell` tools
3. Let Claude create and test a web server

### Repository Analysis

Analyze a local repository (clone first if needed):

```bash
kodx ask "What are the main components of this codebase and how do they interact?" --repo-dir path/to/repo
```

Write JSON results to a file:
```bash
kodx ask "Security audit" --repo-dir . --json-output-file audit.json
```

This will:
1. Copy the local repository into a Docker container
2. Let Claude systematically explore the codebase
3. Provide a comprehensive analysis
## Common Use Cases

### 1. Code Development
```bash
# Interactive development session
kodx --repo-dir "" --prompt "Build a REST API with FastAPI"

# Secure development with network isolation
kodx --repo-dir "" --disable-network-after-setup --prompt "Create secure application"
```

### 2. Repository Understanding
```bash
# Understand architecture
kodx ask "Explain the overall architecture" --repo-dir path/to/repo

# Secure repository analysis
kodx ask "Security audit" --repo-dir path/to/repo --disable-network-after-setup
```
## Custom Configuration

For specialized workflows, create custom program files. See the [kodx core command documentation](kodx-core.md#program-file-format) for the complete program file format and advanced configuration options.

## GitHub Integration

Set up automated repository analysis via GitHub comments:

### 1. Add Workflow File

Use the example workflow in `.github/workflows/kodx-slash-ask.yml` as a starting point.

### 2. Add Repository Secret

In your GitHub repository settings:
1. Go to Settings → Secrets and variables → Actions
2. Add `ANTHROPIC_API_KEY` with your Claude API key

### 3. Use in Issues/PRs

Comment on any issue or pull request:
```
/ask How does the authentication middleware work in this project?
```

Kodx will automatically analyze the repository and respond with detailed explanations.
## Best Practices

### 1. Effective Prompts
- **Be specific**: "Explain the user authentication flow" vs "How does auth work?"
- **Provide context**: Include relevant files or components you're interested in
- **Ask follow-ups**: Build on previous analyses for deeper understanding

### 2. Docker Images
- **Use appropriate base images**: `python:3.11` for Python, `node:18` for JavaScript
- **Consider image size**: Smaller images start faster
- **Custom images**: Build specialized images for repeated use cases

### 3. Repository Analysis
- **Target specific areas**: Focus queries on particular components or features
- **Use context files**: Provide issue/PR context for more relevant analysis
- **Save results**: Use `--json-output-file results.json` to write analysis to a file

### 4. Security
- **Never commit API keys**: Always use environment variables
- **Verify repository access**: Ensure you have permission to analyze private repos
- **Review GitHub workflow permissions**: Only grant necessary access levels
- **Use network isolation**: Add `--disable-network-after-setup` for security-sensitive analysis
- **Consider setup requirements**: Ensure all dependencies are installed before enabling network isolation

## Troubleshooting

### Common Issues

**Docker not running:**
```bash
# Check Docker status
docker ps

# Start Docker (varies by system)
sudo systemctl start docker  # Linux
# or restart Docker Desktop    # macOS/Windows
```

**API key issues:**
```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

kodx --repo-dir "" --prompt "Hello, Claude!" --log-level DEBUG
```

**Permission denied for repository:**
```bash
# For private repos, set GitHub token
export GITHUB_TOKEN="your-github-token"

# Or use public repository URL
```

### Debug Mode

Enable detailed logging for troubleshooting:
```bash
kodx --repo-dir "" --prompt "Hello, Claude!" --log-level DEBUG
```

## Next Steps

- **Read the [Architecture Guide](architecture.md)** for deeper understanding
 - **Check [GitHub Action Examples](github-action-examples.md)** for advanced workflow setups
- **Review [API Reference](api.md)** for programmatic usage
- **Explore [Features](features_ask.md)** for repository analysis capabilities

## Support

- **Issues**: Report bugs at [GitHub Issues](https://github.com/cccntu/kodx/issues)
- **Documentation**: Browse the [docs/](.) directory

Happy coding with Kodx! 🚀

---

## Documentation Navigation

[Back to Documentation Index](index.md)
