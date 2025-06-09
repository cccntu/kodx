# Kodx API Reference

This document provides a comprehensive reference for the Kodx API, including CLI commands, Python SDK, and configuration options.

## CLI Commands

Kodx provides three main commands for different workflows:

- **[kodx](kodx-core.md)** - General-purpose containerized assistant with custom program support
- **[kodx ask](kodx-ask.md)** - Specialized code analysis workflow  
- **[kodx code](kodx-code.md)** - Git-integrated feature implementation workflow

For detailed command reference, options, and examples, see the individual command documentation linked above.

## Python SDK

### Basic Usage

```python
from kodx.tools import DockerCodexTools
from llmproc import LLMProgram

async def analyze_code():
    # Create Docker tools
    docker_tools = DockerCodexTools(container_image="python:3.11")

    # Initialize container
    await docker_tools.initialize()

    # Create LLM program
    program = LLMProgram.from_dict({
        "model": {"name": "claude-sonnet-4", "provider": "anthropic"},
        "prompt": {"system": "You are a coding assistant."},
        "parameters": {"max_tokens": 4000}
    })

    # Register tools
    program.register_tools([
        docker_tools.feed_chars,
        docker_tools.create_new_shell
    ])

    # Run analysis
    process = await program.start()
    await process.run("Show me the current directory structure")

    # Get results
    response = process.get_last_message()
    print(response)

    # Cleanup
    await docker_tools.cleanup()
```

### Core Classes

#### DockerCodexTools

Main class for Docker container interaction.

```python
class DockerCodexTools:
    def __init__(self, container_image: str = "python:3.11", container_name: str = None, disable_network_after_setup: bool = False)

    async def initialize(self) -> None
    async def cleanup(self) -> None

    @register_tool(
        description=(
            "Feed characters to a session's STDIN. After feeding characters, "
            "wait some amount of time, flush STDOUT/STDERR, and show the "
            "results. Note that a minimum of 250 ms is enforced, so if a "
            "smaller value is provided, it will be overridden with 250 ms."
        )
    )
    async def feed_chars(
        self,
        chars: str,
        shell_name: str = "default",
        yield_time_ms: int = 1000,
    ) -> str

    @register_tool(description="Create a new shell session")
    async def create_new_shell(self, shell_name: str = "default") -> str

    @property
    def container_id(self) -> str
```

**Methods:**

- `initialize()`: Start Docker container and set up shell environment
- `cleanup()`: Stop and remove container, clean up resources
- `feed_chars(chars, shell_name="default", yield_time_ms=1000)`: Feed characters to a session's STDIN and return the output
- `create_new_shell(shell_name="default")`: Reset or create named shell session
- `container_id`: Get container ID for docker cp operations

## Configuration

### TOML Configuration

Kodx uses llmproc configuration format:

```toml
[model]
name = "claude-sonnet-4"
provider = "anthropic"
max_iterations = 10

[prompt]
system = "You are a helpful coding assistant with Docker access."

[parameters]
max_tokens = 4000
temperature = 0.1

[env_info]
variables = ["working_directory", "platform", "date"]

[docker]
image = "python:3.11"
disable_network_after_setup = false  # Set to true for network isolation
```

### GitHub Context File

For repository analysis with GitHub integration:

```json
{
  "issue_title": "Authentication system broken",
  "issue_body": "Users cannot log in after recent changes...",
  "is_pr": false,
  "base_branch": "main",
  "head_branch": "feature/auth-fix"
}
```

## Error Handling

### Common Errors

**Docker not running:**
```
Error: Docker daemon not accessible
```
*Solution: Start Docker service*

**Repository access denied:**
```
Git clone failed: Permission denied
```
*Solution: Check repository permissions and credentials*

**Container initialization failed:**
```
Error: Container not initialized
```
*Solution: Ensure Docker has sufficient resources*

### Error Recovery

```python
async def robust_analysis():
    docker_tools = None
    try:
        docker_tools = DockerCodexTools()
        await docker_tools.initialize()

        # Your analysis code here

    except Exception as e:
        print(f"Analysis failed: {e}")
    finally:
        if docker_tools:
            await docker_tools.cleanup()
```

## Environment Variables

### Required for Repository Analysis

- `ANTHROPIC_API_KEY`: Claude API key for LLM operations
- `GITHUB_TOKEN`: GitHub token for private repository access (optional)

### Optional Configuration

- `OPENCODX_DEFAULT_IMAGE`: Default Docker image to use
- `OPENCODX_LOG_LEVEL`: Default logging level
- `OPENCODX_TIMEOUT`: Default operation timeout in seconds

## Security Considerations

### Credential Handling

- API keys should only be set via environment variables
- Never commit API keys to repositories
- GitHub tokens are only used for repository cloning, not stored in containers

### Container Security

- Each analysis runs in an isolated Docker container
- Containers are automatically removed after completion
- No persistent storage between analyses
- Host file system is not accessible from containers
- Optional network isolation after setup with `--disable-network-after-setup` flag

### Access Control

For GitHub Actions integration:
- Only repository collaborators can trigger analysis
- Workflow permissions are limited to necessary operations
- All operations are logged for audit purposes

## Performance Optimization

### Container Efficiency

- Use lightweight base images when possible
- Reuse containers for multiple operations in the same session
- Clean up resources promptly to avoid resource leaks

### Analysis Optimization

- Use targeted queries for faster results
- Specify relevant files or directories in questions
- Consider repository size when setting timeouts

## Troubleshooting

### Debug Mode

Enable verbose logging:
```bash
kodx ask "..." --repo-dir path/to/repo --log-level DEBUG
```

### Container Issues

Check Docker status:
```bash
docker ps
docker logs <container_id>
```

### Repository Analysis Issues

1. Verify repository URL is accessible
2. Check network connectivity
3. Ensure sufficient disk space for cloning
4. Verify API key is valid and has sufficient credits

---

## Documentation Navigation

[Back to Documentation Index](index.md)
