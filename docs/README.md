# Kodx Documentation

Welcome to the Kodx documentation! This directory contains comprehensive guides and references for using and developing with Kodx. For a quick overview, see [index.md](index.md).

## Documentation Map

| Document | Description |
| --- | --- |
| [quickstart.md](quickstart.md) | Installation and basic usage |
| [features_ask.md](features_ask.md) | Repository analysis workflow |
| [docker-config.md](docker-config.md) | Docker and network settings |
| [architecture.md](architecture.md) | System architecture overview |
| [api.md](api.md) | CLI and Python API reference |
| [testing.md](testing.md) | Testing strategy and guidelines |
| [github-action-examples.md](github-action-examples.md) | Example CI workflows |
| [git-integration.md](git-integration.md) | Git workflow details |
| [kodx-core.md](kodx-core.md) | Core command documentation |
| [kodx-ask.md](kodx-ask.md) | `ask` subcommand usage |
| [kodx-code.md](kodx-code.md) | `code` subcommand usage |

## Documentation Overview

### For Users

**[🚀 Quick Start Guide](quickstart.md)** - Get up and running in under 5 minutes
- Installation and setup
- First repository analysis
- Basic usage examples
- GitHub integration setup

**[📖 Features: Repository Analysis](features_ask.md)** - Deep dive into the `/ask` feature
- Design principles and architecture
- Security model (clone-then-copy)
- GitHub workflow integration
- Usage patterns and examples

### For Developers

**[🔧 API Reference](api.md)** - Complete technical reference
- CLI commands and options
- Python SDK documentation
- Configuration formats
- Error handling and troubleshooting

**[🏗️ Architecture Guide](architecture.md)** - Technical architecture overview
- Container initialization flow
- PTY server architecture
- Communication patterns
- Security model

**[🧪 Testing Guide](testing.md)** - Testing strategy and implementation
- Test organization and structure
- Running different test suites
- Writing new tests
- CI/CD integration

### For Contributors

**[🤝 Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute to Kodx
- Development environment setup
- Code style and standards
- Pull request process
- Architecture principles

**[📋 Changelog](../CHANGELOG.md)** - Version history and release notes
- Feature additions and changes
- Breaking changes and migrations

## Quick Navigation

### Getting Started
1. **[Install Kodx](quickstart.md#installation)**
2. **[Set up API key](quickstart.md#setup)**
3. **[Try your first analysis](quickstart.md#repository-analysis)**
4. **[Set up GitHub integration](quickstart.md#github-integration)**

### Common Tasks
- **[Analyze a repository](quickstart.md#repository-analysis)**: `kodx ask "question" --repo-dir DIR`
- **[Interactive coding](quickstart.md#interactive-code-execution)**: `kodx --repo-dir "" --prompt "task"`
- **[Create configurations](api.md#configuration)**: TOML/YAML setup
- **[Initialize repository](#)**: `kodx init`
- **[Troubleshoot issues](api.md#troubleshooting)**: Debug and resolve problems

### Advanced Usage
- **[Python SDK](api.md#python-sdk)**: Programmatic usage
- **[Custom Docker images](quickstart.md#docker-images)**: Specialized environments
- **[GitHub Actions](features_ask.md#github-integration)**: Automated workflows
- **[Security considerations](api.md#security-considerations)**: Best practices

## Architecture Summary

Kodx follows a **Unix-inspired philosophy** with these core principles:

### Minimal Interface
- **2 Tools Only**: `feed_chars` and `create_new_shell`
- **No File Wrappers**: LLMs use standard Unix commands (`cat`, `grep`, `find`)
- **Shell-First**: Direct command-line interaction

### Security-First Design
- **Clone-then-Copy**: Repository credentials never enter containers
- **Isolated Execution**: Each analysis runs in a fresh Docker environment
- **Clean Separation**: Host authentication, container execution
- **Network Isolation**: Optional internet disconnection after setup for enhanced security

### Container Architecture
```
Host System          Docker Container
-----------          ----------------
Git Clone     --->   File Copy Only
Credentials          No Tokens
Cleanup              Isolated Shell
```

## Feature Highlights

### Repository Analysis (`/ask`)
- **Automated Code Exploration**: Systematic repository analysis
- **GitHub Integration**: Comment-triggered workflows
- **Context-Aware**: Understands issues/PRs metadata
- **Secure**: No credential leakage to containers

### Interactive Development (`/run`)
- **Live Coding**: Real-time development environment
- **Custom Images**: Support for any Docker base image
- **PTY Support**: Full terminal capabilities including interrupts
- **Tool Integration**: Seamless LLM-to-shell communication

## Design Philosophy

Kodx embodies the **Unix philosophy** applied to LLM tooling:

1. **Do One Thing Well**: Focus on shell-based code execution
2. **Compose Simply**: Minimal tools that work together
3. **Text Interface**: Standard input/output for all operations
4. **Secure by Default**: Credentials and execution isolated

This approach provides:
- **Predictable Behavior**: LLMs use familiar Unix commands
- **Maximum Flexibility**: Any shell operation is possible
- **Security**: Clear boundaries between host and container
- **Simplicity**: Easy to understand and debug

## Support and Community

### Getting Help
- **[GitHub Issues](https://github.com/cccntu/kodx/issues)**: Bug reports and feature requests
- **[Documentation](.)**: Comprehensive guides and references
 - **[GitHub Action Examples](github-action-examples.md)**: Workflow templates and configuration samples

### Contributing
- **[Development Setup](../CONTRIBUTING.md#development-setup)**: Get started with development
- **[Code Style](../CONTRIBUTING.md#code-standards)**: Follow project conventions
- **[Testing](../CONTRIBUTING.md#testing)**: Write and run tests
- **[Architecture](../CONTRIBUTING.md#architecture-principles)**: Understand design principles


---

**Ready to get started?** Begin with the **[Quick Start Guide](quickstart.md)** and have your first repository analysis running in minutes!
