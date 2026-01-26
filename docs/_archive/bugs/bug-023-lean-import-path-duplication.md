# Bug: `erdos lean import` path duplication causes crash

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 92039ca

## Description

The `erdos lean import` command crashed with a path duplication error when validating the imported Lean file. When the Lean project path is relative (default: `formal/lean`), `formal/lean/` was effectively prepended twice, producing an invalid path like `formal/lean/formal/lean/Erdos/Problem042.lean`.

## Steps to Reproduce

1. Run `uv run erdos lean import 42`

## Expected Behavior

The command should either:
1. Successfully import and validate the file at `formal/lean/Erdos/Problem042.lean`
2. Gracefully handle missing Lean project

## Actual Behavior

```text
FileNotFoundError: Lean file not found: formal/lean/formal/lean/Erdos/Problem042.lean
Error: Lean file not found: formal/lean/formal/lean/Erdos/Problem042.lean
```

## Root Cause

`get_local_file_path(project_path, problem_id)` returns `project_path / "Erdos" / f"Problem{problem_id:03d}.lean"`. When `project_path` is relative (default), that produces a *cwd-relative* path that already contains the project prefix (e.g., `formal/lean/Erdos/Problem042.lean`).

`LeanRunner.check()` treats any non-absolute path as *project-relative* and prepends `project_path` again, resulting in `formal/lean/formal/lean/Erdos/Problem042.lean`.

In `src/erdos/commands/lean/import_cmd.py`:

```python
lean_validated = _validate_imported_file(
    project_path, local_path, skip_lean_validation
)
```

## Fix

Normalize the path passed to `LeanRunner.check()` so it is either absolute or project-relative:
- if the local path includes the project prefix (e.g., `formal/lean/Erdos/...`), strip `project_path` and pass `Erdos/...`
- otherwise, pass it through unchanged

## Related

- `src/erdos/commands/lean/import_cmd.py`
- `src/erdos/core/formal_conjectures/paths.py`
- `src/erdos/core/lean/runner.py`
