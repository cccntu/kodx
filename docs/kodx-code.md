# kodx `code` Command

The `code` subcommand automates feature implementation with git integration.

## Purpose

AI-driven feature implementation with git integration and branch management.

**Requirements**:
- Must be run within a git repository
- Fails with clear error if not in git repo

**Workflow**:
1. Validates git repository context
2. Creates temporary workspace with repo clone
3. Creates feature branch from specified base
4. Runs AI implementation in container
5. AI makes explicit commits with meaningful messages
6. Exports container changes as git commits
7. Fetches branch into main repository

## Usage

```bash
kodx code "REQUEST" [OPTIONS]
```

`REQUEST` describes the desired feature or change. Kodx checks out your repository in a temporary workspace, runs the LLM inside a container, and exports the changes as a new git branch.

## Common Options

- `--base-ref REF` - Git reference to branch from.
- `--dirty` - Include uncommitted changes (only without `--base-ref`).
- `--branch NAME` - Use this branch name instead of the auto-generated one.
- `--program FILE` - Path to a custom implementation program.
- `--json` - Output structured JSON result.
- `--json-output-file FILE` - Write JSON output to a file.
- `-q, --quiet` - Reduce output verbosity.
- `--log-level LEVEL` - Set log level.
- `--cost-limit USD` - Stop execution when cost exceeds this value.
- `--timeout SECONDS` - Stop execution after this many seconds (default 1200).
- `--dry-run` - Print planned actions without starting a container.

## Git Integration Options

- **Default**: Branch from current commit (clean checkout)
- **`--base-ref REF`**: Branch from specified reference (always clean checkout)
- **`--dirty`**: Include working directory changes (only when no `--base-ref` specified)

## Branch Naming

- **Default**: `kodx/<commit-message-slug>` (e.g., `kodx/implement-user-authentication`)
- **Conflict resolution**: Append commit hash if branch exists (e.g., `kodx/implement-user-authentication-a1b2c3d4`)
- **User override**: `--branch kodx/custom-name`

## Examples

```bash
# Clean implementation from current commit
kodx code "Add user authentication"

# Include working directory changes
kodx code "Fix current work" --dirty

# Branch from specific reference
kodx code "Add feature" --base-ref main
kodx code "Hotfix" --base-ref v1.2.3
kodx code "Continue work" --base-ref feature/auth

# Custom branch name
kodx code "Add tests" --branch kodx/comprehensive-tests

# ERROR: Invalid combination
kodx code "Add feature" --base-ref main --dirty
# ERROR: --dirty cannot be used with --base-ref
```

## Error Handling

### Not in Git Repository
```bash
cd /tmp/not-a-git-repo
kodx code "Add feature"
# ERROR: kodx code requires a git repository
# Current directory is not in a git repository
```

### Invalid Base Reference
```bash
kodx code "Add feature" --base-ref nonexistent
# ERROR: Invalid reference 'nonexistent'
# Use a valid branch name, commit SHA, or tag
```

### Invalid Flag Combination
```bash
kodx code "Add feature" --base-ref main --dirty
# ERROR: --dirty cannot be used with --base-ref
# --dirty only applies when branching from current commit
```

For detailed git integration information, see [git-integration.md](git-integration.md).

---

## Documentation Navigation

[Back to Documentation Index](index.md)
