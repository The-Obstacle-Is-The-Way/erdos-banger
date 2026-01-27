# DEBT-116: Timeout Constants Not Consistently Used

**Priority:** P3
**Status:** Open
**Found:** 2026-01-27

## Summary

`constants.py` already defines timeout constants (lines 17-35), but some modules define their own local constants or hardcode values instead of importing from the central location.

## Current State

### Centralized (in `core/constants.py`)

| Line | Constant | Value | Purpose |
|------|----------|-------|---------|
| 19 | `DEFAULT_HTTP_TIMEOUT` | 30.0 | HTTP requests |
| 25 | `LEAN_COMPILE_TIMEOUT` | 120 | Lean compilation |
| 28 | `LEAN_VERSION_TIMEOUT` | 10 | lean --version |
| 31 | `LAKE_UPDATE_TIMEOUT` | 600 | lake update |
| 34 | `LLM_COMMAND_TIMEOUT` | 300 | LLM commands |
| 37 | `GIT_OP_TIMEOUT` | 30 | Git operations |
| 40 | `GIT_FETCH_TIMEOUT` | 120 | Git network operations |

### Local Duplicates (should import from constants.py)

| Location | Constant | Value | Duplicates |
|----------|----------|-------|------------|
| `core/sync/proofs.py:53` | `CLONE_TIMEOUT` | 120 | Same as `LEAN_COMPILE_TIMEOUT` |
| `core/sync/proofs.py:54` | `BUILD_TIMEOUT` | 600 | Same as `LAKE_UPDATE_TIMEOUT` |
| `core/sync/proofs.py:55` | `NO_SORRIES_TIMEOUT` | 120 | Same as `LEAN_COMPILE_TIMEOUT` |

### Hardcoded Values (should use constants)

| Location | Value | Should Use |
|----------|-------|------------|
| `core/sync/website.py:66,250,317` | `30.0` | `DEFAULT_HTTP_TIMEOUT` |
| `core/clients/openalex.py:39` | `30.0` | `DEFAULT_HTTP_TIMEOUT` |
| Various clients | `30.0` | `DEFAULT_HTTP_TIMEOUT` |

## Problems

1. **Duplication**: `proofs.py` defines constants that duplicate `constants.py`
2. **Hidden magic numbers**: `30.0` appears inline instead of using `DEFAULT_HTTP_TIMEOUT`
3. **Inconsistent git timeouts**: use `GIT_OP_TIMEOUT` / `GIT_FETCH_TIMEOUT` for git subprocess calls (BUG-048 fixed in PR #42)

## Recommended Fix

```python
# In proofs.py, replace local constants:
from erdos.core.constants import (
    LEAN_COMPILE_TIMEOUT,  # replaces CLONE_TIMEOUT, NO_SORRIES_TIMEOUT
    LAKE_UPDATE_TIMEOUT,   # replaces BUILD_TIMEOUT
)

# For git subprocess calls, prefer these centralized constants:
from erdos.core.constants import GIT_FETCH_TIMEOUT, GIT_OP_TIMEOUT

# In website.py and clients/*.py, replace inline 30.0:
from erdos.core.constants import DEFAULT_HTTP_TIMEOUT
```

## Acceptance Criteria

- [ ] `proofs.py` imports from `constants.py` instead of defining local constants
- [ ] Inline `30.0` in `website.py` replaced with `DEFAULT_HTTP_TIMEOUT`
- [ ] Inline `30.0` in clients replaced with `DEFAULT_HTTP_TIMEOUT`
- [x] Add `GIT_OP_TIMEOUT` / `GIT_FETCH_TIMEOUT` to `constants.py` for `submodule.py` (BUG-048)

## Notes

Low priority because current timeouts work. Main benefit is consistency and single source of truth for tuning.
