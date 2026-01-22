# DEBT-051: `core/batch.py` Is an SRP Hotspot (Execution + State + Filtering + Error Taxonomy)

**Status:** Open
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Clean Code audit

---

## Summary

`src/erdos/core/batch.py` is a large module (**570** LOC) that contains multiple responsibilities:

- filtering problem IDs
- batch state serialization / persistence
- execution orchestration
- error mapping and CLI-shaped result data

The code works and is well-tested, but this is a classic “feature accretion” hotspot. As we add more batch-able operations (ingest, formalize, convert, loop), this file will become a god module again.

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

1. [ ] Module split reduces `batch.py` to a thin shim (or ≤ ~200 LOC).
2. [ ] State persistence is isolated from execution logic (easier to test + reason about).
3. [ ] Public API remains stable (shim re-exports allowed).
4. [ ] `make ci` passes.

---

## Non-Goals

- Changing batch behavior or CLI options.
- Adding concurrency beyond current constraints.
