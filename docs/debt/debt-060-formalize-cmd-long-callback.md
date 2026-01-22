# DEBT-060: `formalize_cmd.py` Typer Callback Exceeds Function LOC Threshold

**Status:** Open
**Priority:** P4
**Found:** 2026-01-22
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

1. [ ] `register()` reduced to ≤ 120 LOC (or split into multiple functions)
2. [ ] Core logic extracted into testable helpers
3. [ ] `make ci` passes

---

## Non-Goals

- Changing CLI UX or argument names
- Refactoring other lean command modules (tracked separately if needed)
