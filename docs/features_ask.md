# Kodx /ask Feature Design

## Overview

The `/ask` feature enables automated repository analysis through GitHub comments, similar to llmproc's repository analysis workflow but using Kodx's containerized execution model.

## Trigger Pattern

Users can invoke repository analysis by commenting on GitHub issues or pull requests:

```
/ask How does the authentication system work?
```

Multi-line queries are supported:
```
/ask Can you explain the database migration process?
Please include details about rollback procedures.
```

## Architecture

```
GitHub Comment → GitHub Action → Kodx CLI → Docker Container
     ↓              ↓               ↓               ↓
  "/ask query"   Extract & Setup   Clone Repo   CodexShell + LLM
```

### Security Model: Clone-Then-Copy

**Repository Access Pattern:**
1. **Host-side cloning**: GitHub Action clones repository using `GITHUB_TOKEN`
2. **File-only transfer**: Copy source files (no `.git`) into Docker container
3. **Clean container**: No authentication tokens or git history in container
4. **Analysis execution**: LLM analyzes code using shell commands in isolated environment

This approach ensures:
- No credentials leak into containers
- Clean, reproducible analysis environment  
- Works with private repositories
- Maintains security isolation

### Tool Minimalism

The feature uses only Kodx's two core tools:
- `feed_chars`: Execute shell commands for code exploration
- `create_new_shell`: Manage shell sessions for persistent state

No custom analysis tools - the LLM uses standard Unix tools through the shell interface:
- `find`, `grep`, `cat` for file discovery and content reading
- `ls`, `tree` for directory structure exploration
- `head`, `tail` for file sampling
- Standard text processing tools (`awk`, `sed`, etc.)

## Implementation Components

### 1. GitHub Action Workflow

**Trigger**: Comments containing `/ask`
**Security**: Repository collaborators only
**Environment**: Ubuntu runner with Docker

**Workflow steps:**
1. Extract query from comment and gather issue/PR context
2. Post initial "processing" status comment
3. Checkout repository with proper authentication
4. Install Kodx CLI
5. Execute analysis with repository context
6. Update status comment with results

### 2. CLI Extension

**CLI usage**: `kodx ask "question" --repo-dir DIR [options]`
**Key options:**
- `--repo-dir`: Local directory containing the repository (use `""` for clean container)
- `--prompt`: Analysis question
- `--context-file`: JSON file with GitHub issue/PR metadata
- `--image`: Docker image to use (default: `python:3.11`)
- `--disable-network-after-setup`: Disconnect internet after setup for enhanced security isolation

**Execution flow:**
1. Start Docker container
2. Clone repository on host using available credentials
3. Copy source files into container at `/workspace/repo`
4. Initialize basic git repository in container (for tools that expect it)
5. Create analysis prompt combining query and context
6. Execute LLM analysis using registered Kodx tools
7. Return formatted results with work log

### 3. Analysis System Prompt

**Role**: Expert software engineering assistant
**Approach**: Systematic code exploration using shell commands
**Documentation**: Use shell commands to document investigation process

**Analysis methodology:**
1. Repository overview (`ls`, `find`, README analysis)
2. Targeted search based on query (`grep`, pattern matching)
3. File content analysis (`cat`, `head`, code reading)
4. Dependency and relationship tracking
5. Comprehensive answer with evidence

### 4. Context Integration

**Issue context**: Title, description, labels
**PR context**: Source/target branches, changes, description
**Query context**: Specific question with any multi-line details

**Prompt format:**
```
Context: [Issue/PR metadata]
Repository: [Cloned to /workspace/repo]
Question: [User query]

Please analyze the repository systematically to answer this question.
```

## Example Interaction Flow

1. **User comments**: `/ask How does user authentication work in this Django app?`
2. **Action triggers**: Extracts query, posts "Processing..." comment
3. **Repository setup**: Clones repo, copies to container
4. **LLM analysis**:
   ```bash
   find . -name "*.py" | grep -i auth
   cat authentication/models.py
   grep -r "User.objects" .
   cat requirements.txt | grep -i auth
   ```
5. **Response**: Detailed explanation of authentication system with code references
6. **Comment update**: Original comment updated with complete analysis

## Benefits

**Minimal complexity**: Leverages existing Kodx tools without custom extensions
**Security focused**: Clone-then-copy pattern prevents credential leakage
**GitHub integrated**: Natural workflow within GitHub issues and PRs
**Flexible analysis**: Standard Unix tools provide comprehensive code exploration
**Isolated execution**: Each analysis runs in fresh, clean container environment
**Enhanced security**: Optional network isolation after setup with `--disable-network-after-setup`

## Limitations

**No git operations**: Container has no git history or remote access
**Read-only analysis**: Cannot make changes or test modifications
**No incremental updates**: Each analysis starts fresh
**Basic shell only**: No specialized IDE features or advanced analysis tools
**Network isolation**: When `--disable-network-after-setup` is used, no internet access during analysis

These limitations are acceptable for the target use case of repository exploration and code explanation.

---

## Documentation Navigation

[Back to Documentation Index](index.md)
