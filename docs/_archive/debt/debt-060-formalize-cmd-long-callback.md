# DEBT-060: `formalize_cmd.py` Typer Callback Exceeds Function LOC Threshold

**Status:** Fixed
**Priority:** P4
**Found:** 2026-01-22
**Fixed:** 2026-01-22
**Fixed In:** 7b871e5
**Found By:** audit_code_health.py guardrail

---

## Summary

`src/erdos/commands/lean/formalize_cmd.py` contains a nested Typer callback pattern where `register()` defines `formalize()` internally. The combined structure exceeds the 120 LOC function threshold:

- `register()`: 194 LOC (includes the nested `formalize()` definition)
- `formalize()`: 190 LOC (the actual callback)

This is a pattern issue common to Typer commands with many options. The code is functional and well-tested, but the long function bodies reduce readability.

---

## Evidence

```bash
python3 - <<'PY'
import ast
import pathlib

p = pathlib.Path("src/erdos/commands/lean/formalize_cmd.py")
t = p.read_text()
m = ast.parse(t)
for n in ast.walk(m):
    if isinstance(n, ast.FunctionDef):
        if n.name in ("register", "formalize"):
            print(f"{n.name} LOC: {n.end_lineno - n.lineno + 1} at {p}:{n.lineno}")
PY
```

---

## Recommended Fix

1. Extract batch vs single-problem orchestration into separate helper functions
2. Move argument validation and error handling into dedicated functions
3. Keep the Typer callback thin (parse args → call orchestrator → return result)

---

## Acceptance Criteria

1. [x] `register()` reduced to ≤ 120 LOC (or split into multiple functions)
2. [x] Core logic extracted into testable helpers
3. [x] `make ci` passes

---

## Fix Applied

Refactored `formalize_cmd.py` to extract logic into helper functions:

1. Added `_FormalizeArgs` dataclass to bundle validated arguments with `batch_mode` property
2. Extracted `_validate_args()` for argument validation (24 LOC)
3. Extracted `_execute_formalize()` for orchestration logic (48 LOC)
4. Kept existing `_run_batch_formalize()` helper (42 LOC)

Result:
- `register()`: 80 LOC (down from 194)
- `formalize()`: 76 LOC (down from 190)
- All helpers under threshold

---

## Non-Goals

- Changing CLI UX or argument names
- Refactoring other lean command modules (tracked separately if needed)
