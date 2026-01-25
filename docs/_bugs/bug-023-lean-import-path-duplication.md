# Bug: `erdos lean import` path duplication causes crash

**Priority:** P1
**Status:** Open
**Found:** 2026-01-25
**Fixed:** (not yet)
**Commit:** (pending)

## Description

The `erdos lean import` command crashes with a path duplication error when validating the imported Lean file. The path `formal/lean/` is prepended twice, resulting in an invalid path like `formal/lean/formal/lean/Erdos/Problem042.lean`.

## Steps to Reproduce

1. Run `uv run erdos lean import 42`

## Expected Behavior

The command should either:
1. Successfully import and validate the file at `formal/lean/Erdos/Problem042.lean`
2. Gracefully handle missing Lean project

## Actual Behavior

```
FileNotFoundError: Lean file not found: formal/lean/formal/lean/Erdos/Problem042.lean
Error: Lean file not found: formal/lean/formal/lean/Erdos/Problem042.lean
```

## Root Cause

In `src/erdos/commands/lean/import_cmd.py` line 175-176:

```python
lean_validated = _validate_imported_file(
    project_path, local_path, skip_lean_validation
)
```

The `local_path` is computed by `get_local_file_path(project_path, problem_id)` which returns `project_path / "Erdos" / f"Problem{problem_id:03d}.lean"` — a **relative path that already includes the project path prefix**.

Then in `_validate_imported_file()` line 41-42:

```python
runner = LeanRunner(project_path)
check_result = runner.check(local_path)
```

When `LeanRunner._resolve_lean_path()` (line 213-214 of `runner.py`) checks if the path is absolute:

```python
if not file_path.is_absolute():
    full_path = self._project_path / file_path
```

Since `local_path` is `formal/lean/Erdos/Problem042.lean` (relative, but already prefixed), it gets the project path prepended again, resulting in `formal/lean/formal/lean/Erdos/Problem042.lean`.

## Fix

Two possible fixes:

**Option A: Fix `_validate_imported_file` to pass relative path**
```python
# In import_cmd.py, compute the relative path for validation
relative_path = Path("Erdos") / f"Problem{problem_id:03d}.lean"
lean_validated = _validate_imported_file(
    project_path, relative_path, skip_lean_validation
)
```

**Option B: Fix `get_local_file_path` to return absolute path**
```python
# In paths.py
return (project_path / "Erdos" / f"Problem{problem_id:03d}.lean").resolve()
```

Option A is cleaner as it maintains separation of concerns.

## Related

- `src/erdos/commands/lean/import_cmd.py:175-176`
- `src/erdos/core/formal_conjectures/paths.py:48-58`
- `src/erdos/core/lean/runner.py:213-219`
