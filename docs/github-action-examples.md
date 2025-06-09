# GitHub Actions with Kodx

This guide shows how to integrate Kodx into GitHub workflows for automated code analysis and implementation.

## Working Examples

The Kodx repository includes two production-ready GitHub Actions workflows:

- **[kodx-slash-ask.yml](../.github/workflows/kodx-slash-ask.yml)** - Responds to `/ask` commands in issue comments
- **[kodx-slash-code.yml](../.github/workflows/kodx-slash-code.yml)** - Implements features when issues are labeled with `kodx-implement`

## How It Works

Both workflows follow the same pattern using the `kodx` core command:

1. **Trigger**: GitHub event (issue comment, label, etc.)
2. **Setup**: Install Kodx and configure environment
3. **Execute**: Run `kodx` with custom program and capture JSON output
4. **Respond**: Create comments, branches, or pull requests based on results

## Creating Custom Workflows

You can build your own workflows using the `kodx` core command:

### Basic Pattern

```yaml
name: Custom Kodx Workflow
on: [your-trigger]

jobs:
  kodx-custom:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - run: pip install kodx
    
    - name: Run Kodx
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        kodx your-program.yaml \
          --prompt "$YOUR_PROMPT" \
          --repo-dir . \
          --json-output-file result.json
    
    - name: Process results
      run: |
        # Use result.json to create comments, PRs, etc.
```

### Key Concepts

1. **Custom Programs**: Create YAML files to define LLM behavior and Docker setup
2. **JSON Output**: Use `--json-output-file` to capture structured results
3. **Cost Control**: Add `--cost-limit` to prevent excessive spending
4. **Docker Images**: Specify `--image` for language-specific environments

## Advanced Usage

### Multi-Stage Analysis

```bash
# First analyze the issue
kodx analysis-program.yaml --prompt "$ISSUE_BODY" --json-output-file analysis.json

# Then implement based on analysis
kodx implementation-program.yaml --prompt "$ANALYSIS_RESULT" --export-dir ./changes
```

### Environment-Specific Testing

```bash
# Test in different environments
for image in python:3.11 node:18 ruby:3.2; do
  kodx test-program.yaml --image $image --prompt "Run tests"
done
```

### Security-First Workflows

```bash
# Run security analysis with network isolation
kodx security-program.yaml \
  --prompt "Security audit" \
  --disable-network-after-setup \
  --setup-script "pip install bandit safety"
```

## Prerequisites

1. **API Key**: Add `ANTHROPIC_API_KEY` to repository secrets
2. **Permissions**: Configure appropriate workflow permissions
3. **Programs**: Create custom LLM programs for your use cases

## Best Practices

- Start with the provided workflow examples
- Review all automated changes before merging
- Set appropriate cost limits
- Use specific, detailed prompts
- Version control your program files

## Learn More

- [Kodx Core Command](kodx-core.md) - Full command reference
- [Program File Format](kodx-core.md#program-file-format) - Creating custom programs
- [Docker Configuration](docker-config.md) - Container setup options

---

## Documentation Navigation

[Back to Documentation Index](index.md)
