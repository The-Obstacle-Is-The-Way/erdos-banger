# DEBT-051: `core/batch.py` Is an SRP Hotspot (Execution + State + Filtering + Error Taxonomy)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Clean Code audit
**Fixed In:** 8cb7794

---

## Summary

`src/erdos/core/batch.py` is a large module (**570** LOC) that contains multiple responsibilities:

- filtering problem IDs
- batch state serialization / persistence
- execution orchestration
- error mapping and CLI-shaped result data

The code works and is well-tested, but this is a classic "feature accretion" hotspot. As we add more batch-able operations (ingest, formalize, convert, loop), this file will become a god module again.

---

## Recommended Fix (Prepare for Growth)

Split into a package:

```text
src/erdos/core/batch/
├── __init__.py
├── models.py          # BatchState, BatchResult, filters, serialization
├── runner.py          # BatchRunner orchestration
├── persistence.py     # load/save state files
└── errors.py          # typed errors
```

Keep `src/erdos/core/batch.py` as a temporary shim that re-exports public symbols.

Reproduce file size: `wc -l src/erdos/core/batch.py`

---

## Acceptance Criteria

1. [x] Module split reduces `batch.py` to a thin shim (or ≤ ~200 LOC).
2. [x] State persistence is isolated from execution logic (easier to test + reason about).
3. [x] Public API remains stable (shim re-exports allowed).
4. [x] `make ci` passes.

---

## Resolution

Split `batch.py` (571 LOC) into bounded-context package `src/erdos/core/batch/`:

- `models.py` (235 LOC): BatchFilters, BatchState, BatchProgress, BatchResult, filter_problem_ids
- `persistence.py` (87 LOC): generate_batch_id, save/load_batch_state, save/load_latest_batch_id
- `runner.py` (291 LOC): BatchRunner class with orchestration logic
- `__init__.py` (49 LOC): re-exports for backward compatibility

The shim `batch.py` is now 42 LOC. All 920 tests pass with 83.66% coverage.

---

## Non-Goals

- Changing batch behavior or CLI options.
- Adding concurrency beyond current constraints.
