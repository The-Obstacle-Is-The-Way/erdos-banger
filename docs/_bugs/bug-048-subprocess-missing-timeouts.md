# BUG-048: Subprocess Calls Missing Timeouts in submodule.py

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-27
**Fixed:** 2026-01-27
**Component:** `src/erdos/core/sync/submodule.py`

## Description

Multiple git subprocess calls in `sync/submodule.py` don't have explicit timeouts. These can hang indefinitely on network issues or large repositories.

**Note:** `sync/proofs.py` is NOT affected - all its subprocess calls already have timeouts.

## Affected Files

| File | Lines | Description |
|------|-------|-------------|
| `sync/submodule.py` | 118-125 | `git rev-parse HEAD` no timeout |
| `sync/submodule.py` | 154-160 | `git fetch origin` no timeout |
| `sync/submodule.py` | 163-169 | `git rev-list --count` no timeout |
| `sync/submodule.py` | 225-231 | `git fetch origin` no timeout |
| `sync/submodule.py` | 234-240 | `git checkout origin/main` no timeout |

## Evidence

```python
# src/erdos/core/sync/submodule.py:118-125
result = subprocess.run(
    ["git", "rev-parse", "HEAD"],  # noqa: S607
    cwd=submodule_path,
    capture_output=True,
    text=True,
    check=True,
    # NO TIMEOUT!
)
```

## Impact

- Medium: CLI can hang indefinitely waiting for git
- Affects: Users behind slow networks, large repositories
- Workaround: Kill process manually (poor UX)

## Recommended Fix

```python
# Import from constants.py (centralized timeouts)
from erdos.core.constants import GIT_FETCH_TIMEOUT, GIT_OP_TIMEOUT

result = subprocess.run(
    ["git", "rev-parse", "HEAD"],  # noqa: S607
    cwd=submodule_path,
    capture_output=True,
    text=True,
    check=True,
    timeout=GIT_OP_TIMEOUT,  # ADD THIS
)

subprocess.run(
    ["git", "fetch", "origin"],  # noqa: S607
    cwd=submodule_path,
    capture_output=True,
    text=True,
    check=True,
    timeout=GIT_FETCH_TIMEOUT,  # ADD THIS
)
```

## Files to Modify

1. `src/erdos/core/sync/submodule.py` - Add `timeout=` to all 5 subprocess.run calls

## Note

`sync/proofs.py` already handles timeouts correctly (all 4 subprocess calls have timeout parameters).

## Related

- DEBT-114: Hardcoded relative paths (same modules)
- DEBT-116: Timeout constants fragmented across codebase
