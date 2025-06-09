# Git Integration

This document explains how Kodx integrates with Git, particularly for the `kodx code` command which creates new branches with AI-implemented features.

## Git Reference Resolution

Kodx uses `git rev-parse` to resolve base references, supporting:

- **Branch names**: `main`, `develop`, `feature/auth`
- **Commit SHAs**: `abc123`, `a1b2c3d4e5f6...`
- **Tags**: `v1.2.3`
- **Relative refs**: `HEAD~1`, `main^`

## Base Reference Logic

### Default Behavior
```bash
kodx code "Add feature"
# → Branches from current commit, clean checkout (ignores working directory changes)
```

### Including Working Directory Changes
```bash
kodx code "Fix current work" --dirty
# → Branches from current commit + includes uncommitted changes
# → Only works when --base-ref is not specified
```

### Branching from Specific Reference
```bash
kodx code "Add feature" --base-ref main
# → Always clean checkout of specified reference
# → Supports: branch names, commit SHAs, tags, refs
```

## Branch Management

### Branch Name Generation

Branch names are automatically generated from the commit message:

```python
def generate_branch_name(commit_message: str) -> str:
    # Slug from commit message
    slug = re.sub(r'[^a-z0-9]+', '-', commit_message.lower()).strip('-')
    base_name = f"kodx/{slug[:50]}"  # Limit length
    
    # Check for conflicts
    if branch_exists(base_name):
        commit_hash = get_commit_hash()[:8]
        return f"{base_name}-{commit_hash}"
    
    return base_name
```

**Examples**:
- `kodx code "Add user authentication"` → `kodx/add-user-authentication`
- If branch exists: `kodx/add-user-authentication-a1b2c3d4`
- Custom name: `kodx code "Add feature" --branch kodx/custom-name`

### Branch Workflow

```bash
# 1. Implementation
kodx code "Add authentication system"
# → Creates kodx/add-authentication-system

# 2. Review
git checkout kodx/add-authentication-system
git log --oneline  # See AI's commit history
git diff main      # Review all changes

# 3. Integration
git checkout main
git merge kodx/add-authentication-system
```

Kodx only creates the branch if the container repository contains at least one
new commit. If the AI runs without committing changes, no branch is created and
the export directory is left for inspection.

## Commit Management

The AI is responsible for explicit commit decisions:

- AI determines when to commit changes
- AI writes meaningful commit messages
- Multiple commits allowed for complex implementations
- No automatic commits - AI must be intentional

## Workspace Setup Logic

```python
def setup_workspace(base_ref=None, include_dirty=False):
    if base_ref and include_dirty:
        raise ValueError("--dirty cannot be used with --base-ref")
    
    if base_ref:
        # Branch from specified reference (always clean)
        target_commit = resolve_ref(base_ref)
        checkout_commit_to_container(target_commit)
    elif include_dirty:
        # Branch from current commit + working directory
        copy_working_directory_to_container()
    else:
        # Branch from current commit (clean)
        target_commit = get_current_commit()
        checkout_commit_to_container(target_commit)
```

## Container State Management

- All commands copy repository state to container
- Container starts at `/workspace/repo` for consistency
- Clean isolation - no host filesystem pollution

## Error Cases

### Invalid Reference
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

### Not in Git Repository
```bash
cd /tmp/not-a-git-repo
kodx code "Add feature"
# ERROR: kodx code requires a git repository
# Current directory is not in a git repository
```

## Development Workflow Examples

### Feature Development
```bash
# 1. Analysis in container
kodx ask "How should I implement user authentication?"

# 2. Implementation in container → branch
kodx code "Implement user authentication based on analysis"

# 3. Review AI's work
git checkout kodx/implement-user-authentication
git log --oneline  # See AI's commits
git diff main      # Review changes

# 4. Test and merge
npm test
git checkout main && git merge kodx/implement-user-authentication
```

### Working with Uncommitted Changes
```bash
# Current state: working on authentication, uncommitted changes
git status
# modified: src/auth.py (uncommitted work)

# Continue work with AI including current changes
kodx code "Complete the authentication implementation" --dirty
# → AI gets current auth.py changes + implements completion

# Clean implementation ignoring current work
kodx code "Add separate feature" --base-ref main
# → AI starts fresh from main branch
```

---

## Documentation Navigation

[Back to Documentation Index](index.md)
