# Docker Configuration

Kodx supports configuring Docker container settings directly in your YAML/TOML program files, allowing for self-contained, version-controlled container definitions.

## Configuration Options

The `docker` section in your program file supports the following options:

```yaml
docker:
  image: python:3.12-slim       # Docker image to use (default: python:3.11)
  disable_network_after_setup: true  # Disconnect internet after setup (default: false)
  setup_script: |               # Bash script to execute after container creation
    #!/bin/bash
    apt-get update
    apt-get install -y git curl
```

## Precedence Rules

Kodx follows strict precedence rules when both CLI options and YAML configuration are present:

1. **CLI options always take precedence over YAML configuration**
2. If a CLI option is not provided, the corresponding YAML configuration is used
3. If neither is provided, defaults are used

This applies to the Docker image, setup script, and network configuration:

```bash
# Scenario 1: CLI image overrides YAML image
# Uses python:3.10 even if docker.image in YAML is different
kodx my-program.yaml --image python:3.10 --repo-dir .

# Scenario 2: CLI setup script overrides YAML setup_script
# Uses my-setup.sh even if docker.setup_script in YAML exists
kodx my-program.yaml --setup-script my-setup.sh --repo-dir .

# Scenario 3: CLI network flag overrides YAML network setting
# Disables network even if docker.disable_network_after_setup is false in YAML
kodx my-program.yaml --disable-network-after-setup --repo-dir .

# Scenario 4: No CLI options
# Uses all docker.* settings from YAML if present
kodx my-program.yaml --repo-dir .
```

### Setup Script Precedence

For setup scripts specifically:

1. If `--setup-script` CLI option is provided, that script is used and any `docker.setup_script` in YAML is ignored
2. If no `--setup-script` is provided but `docker.setup_script` exists in YAML, the embedded script is used
3. If neither is provided, no setup script is executed

### Network Configuration Precedence

For network isolation specifically:

1. If `--disable-network-after-setup` CLI flag is provided, network is disconnected after setup regardless of YAML setting
2. If no CLI flag is provided but `docker.disable_network_after_setup: true` exists in YAML, network is disconnected
3. If neither is provided, network access remains enabled throughout execution

## Example: Custom Python Environment

```yaml
docker:
  image: python:3.12-slim
  disable_network_after_setup: true  # Enhanced security isolation
  setup_script: |
    #!/bin/bash
    # Update and install dependencies
    apt-get update
    apt-get install -y git curl build-essential

    # Set up Python environment
    pip install --upgrade pip
    pip install pytest black mypy pylint

    # Install project dependencies
    cd /workspace/repo
    if [ -f "requirements.txt" ]; then
      pip install -r requirements.txt
    fi
```

## Example: Node.js Environment

```yaml
docker:
  image: node:20-slim
  disable_network_after_setup: false  # Keep network for npm operations
  setup_script: |
    #!/bin/bash
    # Update and install system dependencies
    apt-get update
    apt-get install -y git curl

    # Configure npm
    npm config set fund false
    npm config set audit false

    # Install global tools
    npm install -g eslint prettier

    # Install project dependencies
    cd /workspace/repo
    if [ -f "package.json" ]; then
      npm install
    fi
```

## Best Practices

1. **Use specific image tags** rather than `latest` to ensure reproducibility
2. **Keep setup scripts focused** on essential dependencies
3. **Add clear error handling** in your setup scripts
4. **Test your setup scripts** before committing them
5. **Consider initialization time** - large installations slow down startup
6. **Enable network isolation** for security-sensitive tasks using `disable_network_after_setup: true`
7. **Consider network requirements** - some tools may need internet access during analysis

## GitHub Actions Integration

Kodx's Docker configuration is particularly useful in GitHub Actions workflows:

```yaml
# .github/workflows/example.yml
- name: Run Kodx
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    kodx .github/config/my-program.yaml \
      --repo-dir . \
      --prompt-file prompt.txt \
      --export-dir ./changes \
      --disable-network-after-setup \
      --json-output-file result.json
```

The workflow can use a program file with embedded Docker setup, eliminating the need for separate setup script files.

---

## Documentation Navigation

[Back to Documentation Index](index.md)
