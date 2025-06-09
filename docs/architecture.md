# Kodx Architecture Documentation

## Overview

Kodx provides a minimal interface for LLMs to interact with containerized development environments. The system creates Docker containers, deploys a PTY server inside them, and exposes only two simple tools for shell interaction.

## Architecture Components

```
Kodx CLI → DockerCodexTools → CodexShell → HTTP → PTY Server (in container) → Bash Process
```

### Key Components

1. **CLI** (`cli.py`) - Command-line interface using llmproc framework
2. **DockerCodexTools** (`tools.py`) - Tool class with @register_tool decorated methods
3. **CodexShell** (`codex_shell.py`) - Shell interaction layer via HTTP
4. **PTY Server** - FastAPI server running inside Docker container
5. **Docker Container** - Isolated execution environment

## Container Initialization Flow

### Step 1: Container Creation

```python
self.container = self.docker_client.containers.run(
    self.container_image,           # e.g., "python:3.11"
    command="sleep infinity",       # Keep container alive
    detach=True,                   # Run in background
    remove=True,                   # Auto-remove when stopped
    name=self.container_name,      # e.g., "kodx-12345"
    network_mode="bridge"          # Network access (may be disconnected later)
)
```

**Result**: Container running with base image, but no shell interaction yet.

### Step 2: Prerequisites Check

```python
for cmd, name, install_cmd in [
    ("which bash", "bash", None),
    ("which python3", "python3", None),
    ("which curl", "curl", ["bash", "-c", "apt-get update -qq && apt-get install -y -qq curl"])
]:
```

**Purpose**: Ensure bash, python3, and curl are available. Installs curl if missing since it's needed for PTY server communication.

### Step 3: Install PTY Server Dependencies

```python
container.exec_run("pip3 install -q fastapi uvicorn")
```

**Purpose**: Install FastAPI and uvicorn inside the container to run the HTTP PTY server.

### Step 4: Deploy PTY Server Code

```python
from pathlib import Path

server_file = Path(__file__).with_name("pty_server.py")
docker_cp(str(server_file), f"{container.id}:/root/pty_server.py")
```

**Details**:
- PTY server code lives in `pty_server.py` and is copied into the container
- Creates `/root/pty_server.py` inside the container
- Server provides HTTP endpoints for PTY process management

### Step 5: Start PTY Server

```python
container.exec_run("python3 /root/pty_server.py &", detach=True)
await asyncio.sleep(1.0)  # Wait for server startup
```

**Result**: PTY server running on localhost:1384 inside the container.

### Step 6: Health Check

```python
result = container.exec_run("curl -s http://localhost:1384/healthcheck")
if result.exit_code != 0 or b"ok" not in result.output:
    raise Exception("PTY server health check failed")
```

**Purpose**: Verify PTY server is responding before proceeding.

### Step 7: Create Bash Session

```python
open_req = {
    "cmd": ["/bin/bash"],
    "env": {"PS1": "\\w $ ", "TERM": "xterm", "PYTHONUNBUFFERED": "1"}
}

result = container.exec_run([
    "curl", "-s", "-X", "POST", "http://localhost:1384/open",
    "-H", "Content-Type: application/json",
    "-d", json.dumps(open_req)
])

shell_pid = int(result.output.strip())
```

**Details**:
- Sends HTTP POST to PTY server to create a bash session
- PTY server creates a new bash process with PTY attached
- Returns PID that identifies this specific shell session
- All future shell interactions use this PID

### Step 8: Setup Working Directory

```python
await self.shell.run("cd /workspace || mkdir -p /workspace && cd /workspace")
```

**Result**: Shell ready in `/workspace` directory for user commands.

### Step 9: Optional Network Isolation

```python
if self.disable_network_after_setup:
    # Disconnect all networks after setup completes
    for network_name in container.attrs['NetworkSettings']['Networks'].keys():
        network = self.docker_client.networks.get(network_name)
        network.disconnect(container)
```

**Purpose**: Enhances security by removing internet access after setup scripts complete, while preserving internal PTY server communication via localhost.

## PTY Server Endpoints

The PTY server (running on port 1384 inside container) provides:

### `GET /healthcheck`
- **Purpose**: Verify server is running
- **Returns**: `{"status": "ok"}`

### `POST /open`
- **Purpose**: Create new PTY process
- **Body**: JSON with cmd, env, cwd
- **Returns**: Process PID (integer)
- **Example**: Creates bash session and returns its PID

### `POST /write/{pid}`
- **Purpose**: Send input to PTY process
- **Body**: Raw bytes to send to process stdin
- **Returns**: Number of bytes written
- **Example**: Send "ls\n" to execute ls command

### `POST /read/{pid}`
- **Purpose**: Read output from PTY process
- **Body**: Maximum bytes to read (as string)
- **Returns**: Raw bytes from process stdout/stderr
- **Example**: Read command output after sending "ls\n"

### `POST /kill/{pid}`
- **Purpose**: Terminate PTY process
- **Returns**: Success/error status
- **Example**: Clean up bash session when done

## Tool Interface

Kodx exposes exactly 2 tools to LLMs:

### `feed_chars(chars: str, shell_name: str = "default", yield_time_ms: int = 1000) -> str`

**Purpose**: Feed characters to a session's STDIN. After feeding characters, wait some amount of time, flush STDOUT/STDERR, and show the results. The `yield_time_ms` parameter controls how long to wait, with a minimum of 250 ms enforced.

**Implementation**:
1. Send chars via HTTP POST to `/write/{pid}`
2. Wait 0.1 seconds for processing
3. Read output via HTTP POST to `/read/{pid}`
4. Return decoded output

**Examples**:
- `feed_chars("ls -la")` - Execute command
- `feed_chars("cat > file.py\nprint('hello')\n")` - Create file with content
- `feed_chars("\x03")` - Send Ctrl+C to interrupt running process
- `feed_chars("python")` - Start interactive Python session

### `create_new_shell(shell_name: str = "default") -> str`

**Purpose**: Create or reset a named shell session, resetting environment.

**Implementation**:
1. Close current shell session (HTTP POST to `/kill/{pid}`)
2. Create new CodexShell instance (repeats initialization steps 4-7)
3. Setup working directory again
4. Return success message

**Use Cases**:
- Shell gets into bad state (broken terminal settings)
- Need clean environment (reset environment variables)
- Process hangs and can't be interrupted

## Communication Flow

### Example: Execute "ls -la" Command

1. **LLM calls**: `feed_chars("ls -la")`
2. **CodexShell.run()**:
   ```python
   # Send command
   container.exec_run([
       "bash", "-c",
       'printf "%s\\n" "ls -la" | curl -s -X POST http://localhost:1384/write/{pid} --data-binary @-'
   ])

   # Read output
   result = container.exec_run([
       "curl", "-s", "-X", "POST", "http://localhost:1384/read/{pid}",
       "-d", "4096"
   ])
   ```
3. **PTY Server**: Receives HTTP requests, writes to bash stdin, reads from bash stdout
4. **Bash Process**: Executes "ls -la", outputs result
5. **Return**: Command output returned to LLM

### Example: Interrupt Running Process

1. **LLM calls**: `feed_chars("python -c 'while True: print(1)'")` (starts infinite loop)
2. **LLM calls**: `feed_chars("\x03")` (send Ctrl+C)
3. **PTY Server**: Receives \x03 (ASCII 3), sends interrupt signal to bash
4. **Bash Process**: Terminates running Python process
5. **Return**: Prompt returns, ready for next command

## Key Design Decisions

### Why PTY Instead of Simple exec_run?

- **Interactive Programs**: PTY supports programs that need terminal (python, vim, top)
- **Signal Handling**: Proper Ctrl+C interrupt capability
- **Output Formatting**: Preserves colors, formatting, cursor movements
- **Session State**: Maintains shell state (environment variables, current directory)

### Why HTTP Server Inside Container?

- **Reliability**: HTTP is more reliable than direct PTY manipulation
- **Async Support**: Non-blocking I/O with proper timeouts
- **Error Handling**: Clear error responses and status codes
- **Network Isolation**: Works even with restricted container networking

### Why Only 2 Tools?

- **Simplicity**: LLMs understand shell commands better than custom file APIs
- **Flexibility**: Shell commands can do anything (file ops, package installs, etc.)
- **No Abstraction Leaks**: Direct shell access, no hidden behavior
- **Standard Interface**: Uses familiar Unix command patterns

## Error Handling

### Container Failures
- Docker daemon not running → Clear error message
- Image not found → Docker pulls automatically or fails with clear message
- Container startup fails → Exception with Docker error details

### PTY Server Failures
- Dependencies missing → Auto-install curl, fail clearly for bash/python3
- Server startup fails → Health check catches and reports
- Server becomes unresponsive → HTTP timeouts provide graceful degradation

### Shell Session Failures
- Shell process dies → create_new_shell() can recover
- Commands hang → feed_chars("\x03") can interrupt
- Terminal corruption → create_new_shell() resets state

## Security Considerations

### Container Isolation
- Each session gets fresh container
- Containers are automatically removed (remove=True)
- No persistent storage by default
- Network access controlled by Docker network settings

### PTY Server Security
- Server only listens on localhost inside container
- No authentication needed (container is already isolated)
- No file system access outside container
- Process isolation via Docker

### Tool Access Control
- LLMs can only use feed_chars and create_new_shell
- No direct Docker API access
- No host file system access
- All operations go through container shell

## Performance Characteristics

### Startup Time
- Container creation: ~1-2 seconds
- Dependency installation: ~10-30 seconds (first time per image)
- PTY server startup: ~1-2 seconds
- **Total**: ~15-35 seconds for first run, ~5 seconds for subsequent runs

### Runtime Performance
- Command execution: Near-native speed (minimal HTTP overhead)
- Output streaming: Limited by HTTP polling (0.1s intervals)
- Memory usage: Base container + FastAPI overhead (~50-100MB)

### Cleanup
- Automatic container removal on exit
- No persistent storage or network resources
- Clean state for every session

## Troubleshooting

### Common Issues

**"Container not initialized"**
- Check Docker daemon is running
- Verify image is available
- Check container creation logs

**"PTY server health check failed"**
- Check if port 1384 is available in container
- Verify FastAPI/uvicorn installation succeeded
- Look for Python errors in container logs

**"Process not found" errors**
- Shell session may have died
- Use create_new_shell() to recover
- Check for shell process crashes

**Commands hang or produce no output**
- Use feed_chars("\x03") to interrupt
- Try create_new_shell() to reset
- Check if command is waiting for input

### Debug Commands

```bash
# Check container status
docker ps

# View container logs
docker logs <container-name>

# Access container directly
docker exec -it <container-name> bash

# Check PTY server
docker exec <container-name> curl http://localhost:1384/healthcheck
```

## Extension Points

### Custom Docker Images
- Modify container_image parameter
- Ensure python3, bash, and curl are available
- Pre-install development tools in custom images

### Additional Tools
- Add more @register_tool methods to DockerCodexTools
- Follow minimal interface principle
- Consider if shell commands can accomplish the same thing

### Configuration Options
- Network isolation settings
- Volume mounts for persistent storage
- Environment variable injection
- Resource limits (CPU, memory)

## Core Philosophy

### Container-First Architecture
All AI interaction happens in isolated Docker containers to ensure:
- Consistent execution environment
- Security isolation from host system
- Reproducible results across different machines
- Clean separation between AI work and host environment

### Fail-Fast Principle
Commands fail early with clear error messages rather than silent fallbacks:
- **`kodx code`** requires git repository
- **`kodx ask`** requires analyzable files
- **`kodx`** user responsible for all configuration

## Implementation Notes

### Git Reference Resolution
Use `git rev-parse` to resolve base references:
- Branch names: `main`, `develop`, `feature/auth`
- Commit SHAs: `abc123`, `a1b2c3d4e5f6...`
- Tags: `v1.2.3`
- Relative refs: `HEAD~1`, `main^`

For detailed git integration, see [git-integration.md](git-integration.md).

This architecture provides a robust, secure, and flexible foundation for LLM-driven code execution in containerized environments.

---

## Documentation Navigation

[Back to Documentation Index](index.md)
