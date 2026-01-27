# BUG-048: Subprocess Calls Missing Timeouts

**Priority:** P2
**Status:** Open
**Found:** 2026-01-27
**Component:** `src/erdos/core/sync/`

## Description

Multiple git subprocess calls in sync modules don't have explicit timeouts. These can hang indefinitely on network issues or large repositories.

## Affected Files

| File | Lines | Description |
|------|-------|-------------|
| `sync/proofs.py` | 153-159 | `git rev-parse HEAD` no timeout |
| `sync/submodule.py` | 118 | `git status` no timeout |
| `sync/submodule.py` | 154 | `git init` no timeout |
| `sync/submodule.py` | 163 | `git remote add` no timeout |
| `sync/submodule.py` | 225 | `git fetch` no timeout |
| `sync/submodule.py` | 235 | `git checkout` no timeout |

## Evidence

```python
# src/erdos/core/sync/proofs.py:153-159
commit_result = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=dest,
    capture_output=True,
    text=True,
    check=False,
    # NO TIMEOUT!
)
```

## Impact

- Medium: CLI can hang indefinitely waiting for git
- Affects: Users behind slow networks, large repositories
- Workaround: Kill process manually (poor UX)

## Recommended Fix

```python
# Use constants from proofs.py or create new constant
GIT_OP_TIMEOUT = 30  # seconds

commit_result = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=dest,
    capture_output=True,
    text=True,
    check=False,
    timeout=GIT_OP_TIMEOUT,
)
```

## Note

`sync/proofs.py` already defines `CLONE_TIMEOUT=120` and `BUILD_TIMEOUT=600` but doesn't use them consistently for all git operations.

## Related

- DEBT-114: Hardcoded relative paths (same modules)
- AUDIT-009: Subprocess timeout not always enforced
