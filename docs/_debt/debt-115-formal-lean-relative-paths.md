# DEBT-115: formal/lean Relative Paths in Lean Commands

**Priority:** P2
**Status:** Open
**Found:** 2026-01-27
**Related:** DEBT-114 (parent issue)

## Summary

Multiple Lean-related commands use `Path("formal/lean")` as a hardcoded default. This is separate from DEBT-114's data/logs/literature paths because:
1. These are in command modules, not core
2. They affect the Lean toolchain specifically
3. Fix pattern is slightly different (project path vs cache path)

## Affected Files

| File | Line | Path | Current Pattern |
|------|------|------|-----------------|
| `commands/sync/statements_cmd.py` | 89 | `formal/lean` | `path = project_path or Path("formal/lean")` |
| `commands/sync/all_cmd.py` | 383 | `formal/lean` | inline default |
| `commands/loop.py` | 199 | `formal/lean` | default parameter |
| `commands/lean/import_cmd.py` | 316 | `formal/lean` | default parameter |
| `commands/lean/check_cmd.py` | 91 | `formal/lean` | default parameter |
| `commands/lean/formalize_cmd.py` | 273 | `formal/lean` | default parameter |
| `commands/lean/init_cmd.py` | 77 | `formal/lean` | default parameter |
| `commands/lean/status_cmd.py` | 258 | `formal/lean` | default parameter |
| `mcp/server.py` | 53 | `formal/lean` | `DEFAULT_LEAN_PROJECT_PATH` |

## Impact

- Breaks when running `erdos lean check` from a subdirectory
- CI/CD must set working directory to repo root
- Cannot embed in larger applications without path gymnastics

## Recommended Fix

```python
# In src/erdos/core/constants.py or config.py
from erdos.core.repo_root import resolve_repo_root

def get_default_lean_project_path() -> Path:
    """Get default Lean project path (formal/lean)."""
    return resolve_repo_root(None) / "formal" / "lean"

# Usage in commands:
from erdos.core.config import get_default_lean_project_path

path = project_path or get_default_lean_project_path()
```

## Acceptance Criteria

- [ ] All 9 files updated to use helper function
- [ ] Helper function added to config.py or constants.py
- [ ] Tests verify paths work from subdirectories
- [ ] MCP server uses the same helper

## Notes

This is a subset of DEBT-114 but tracked separately because:
1. Different module layer (commands vs core)
2. May need different fix approach (Lean project path is more static)
3. Could be fixed independently
