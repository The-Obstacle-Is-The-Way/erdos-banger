# DEBT-039: `erdos lean` Command Module Is a God File (SRP Violation)

**Status:** Fixed
**Fixed In:** 8540017
**Priority:** P2
**Found:** 2026-01-21
**Found By:** Clean Code / SRP audit

---

## Summary

`src/erdos/commands/lean.py` has grown into a **god module** (~1.4k LOC) that mixes multiple responsibilities:

- Typer command wiring (`erdos lean …`)
- Human/JSON output formatting and routing
- Lean project initialization (`lean init`)
- Compile/check orchestration (`lean check`)
- Skeleton generation (`lean formalize`)
- Batch operations and progress aggregation
- Upstream formalization import (Formal Conjectures repo)
- Aristotle integration (`lean prove` / external tool)

This violates **Single Responsibility Principle (SRP)** and increases the cost of change, review complexity, and the likelihood of regressions.

---

## Evidence

- File size: `src/erdos/commands/lean.py` is **~1427 lines** (run `wc -l src/erdos/commands/lean.py`).
- The import surface includes unrelated subsystems (batch, formal conjectures, Aristotle) in a single CLI module.

---

## Why This Matters

1. **Change amplification:** Small changes to one subcommand force large-module edits and full-file review.
2. **Testing friction:** Unit tests struggle to target “core logic” when it’s embedded in a single command module.
3. **Accidental coupling:** Shared globals/helpers accrete and become implicit APIs.
4. **Onboarding cost:** Contributors must understand too much context to make safe changes.

---

## Recommended Fix (Incremental, Low-Risk)

### Step 1: Split into a Package

Create `src/erdos/commands/lean/` and move each subcommand into its own module:

```
src/erdos/commands/lean/
├── __init__.py          # exports `app` (Typer group)
├── common.py            # shared helpers + human printers
├── init_cmd.py          # `erdos lean init`
├── check_cmd.py         # `erdos lean check`
├── formalize_cmd.py     # `erdos lean formalize`
├── status_cmd.py        # `erdos lean status`
├── import_cmd.py        # `erdos lean import`
└── prove_cmd.py         # `erdos lean prove` (Aristotle integration)
```

Keep `src/erdos/commands/lean.py` temporarily as a thin shim (or delete it once imports are updated), to preserve CLI entry points and avoid churn.

### Step 2: Move Orchestration Out of CLI (Optional, Follow-up)

If/when feasible, move non-CLI orchestration into `src/erdos/core/…` (e.g., `core/lean/service.py`) so that Typer callbacks stay thin and testable.

---

## Acceptance Criteria

1. [x] No single `src/erdos/commands/lean/*.py` module exceeds **~300 LOC** without justification.
   - Largest module: `import_cmd.py` at 316 LOC (justified: well-factored with multiple helper functions and thin CLI callback)
   - `formalize_cmd.py` at 269 LOC (within limit after extracting batch logic to `batch_formalize.py`)
2. [x] `erdos lean --help` output and subcommand behavior remain unchanged.
3. [x] Unit tests cover the extracted "core logic" functions (no Typer runner required).
4. [x] `make ci` passes with no coverage regression (82.17% coverage).

---

## Non-Goals

- Changing CLI UX/flags/output schemas (keep stable).
- Re-architecting LeanRunner internals (handled elsewhere).
