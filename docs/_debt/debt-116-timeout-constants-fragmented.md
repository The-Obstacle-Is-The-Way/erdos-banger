# DEBT-116: Timeout Constants Fragmented Across Codebase

**Priority:** P3
**Status:** Open
**Found:** 2026-01-27

## Summary

Timeout values are defined inconsistently across the codebase - some in constants.py, some hardcoded inline, some as class defaults. This makes it difficult to tune timeouts globally.

## Current State

| Location | Constant | Value | Usage |
|----------|----------|-------|-------|
| `core/constants.py:19` | `DEFAULT_HTTP_TIMEOUT` | 30.0 | HTTP clients |
| `core/sync/proofs.py:53` | `CLONE_TIMEOUT` | 120 | git clone |
| `core/sync/proofs.py:54` | `BUILD_TIMEOUT` | 600 | lake build |
| `core/sync/proofs.py:55` | `NO_SORRIES_TIMEOUT` | 120 | sorry check |
| `core/sync/website.py:66,250,317` | inline | 30.0 | HTTP requests |
| `core/clients/openalex.py:39` | inline | 30.0 | OpenAlex API |
| `core/clients/*.py` | class default | 30.0 | Various clients |

## Problems

1. **Inconsistency**: Some use `DEFAULT_HTTP_TIMEOUT`, others hardcode `30.0`
2. **No global override**: Can't tune all timeouts via config
3. **Hidden magic numbers**: `30.0` appears 10+ times without context
4. **Missing timeouts**: Some subprocess calls have no timeout at all (BUG-048)

## Recommended Fix

```python
# src/erdos/core/constants.py
# HTTP and network timeouts
DEFAULT_HTTP_TIMEOUT = 30.0  # seconds
DEFAULT_API_TIMEOUT = 30.0   # seconds (alias for clarity)

# Git operations
GIT_CLONE_TIMEOUT = 120     # seconds
GIT_OP_TIMEOUT = 30         # seconds (rev-parse, status, etc.)

# Build operations
LEAN_BUILD_TIMEOUT = 600    # seconds (lake build)
LEAN_CHECK_TIMEOUT = 120    # seconds (sorry/admit checks)

# Then update all modules to import from constants
```

## Acceptance Criteria

- [ ] All timeout values moved to `constants.py`
- [ ] All inline `30.0` replaced with `DEFAULT_HTTP_TIMEOUT`
- [ ] All `timeout=` parameters import from constants
- [ ] Documentation of timeout values in constants.py

## Notes

Low priority because current timeouts work, but maintenance burden grows with each new module.
