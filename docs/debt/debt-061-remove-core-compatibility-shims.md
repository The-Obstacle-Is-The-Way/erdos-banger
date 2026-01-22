# DEBT-061: Remove `src/erdos/core/*` Backward-Compatibility Shims

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean architecture audit (module sprawl)

---

## Summary

`src/erdos/core/` contains several **backward-compatibility shims** whose only job is to re-export symbols from refactored subpackages (e.g., `core/search/`, `core/clients/`, `core/loop/`, `core/pdf/`, `core/batch/`).

This project is effectively **greenfield** (no external API consumers), so these shims add:

- unnecessary indirection and cognitive overhead
- duplicate module surfaces that drift
- `core/` sprawl (more top-level modules than needed)

Removing them will tighten the import graph and reduce confusion about the SSOT module for each concern.

---

## Evidence

The following files explicitly state they are shims:

```bash
rg -n "Backward-compatible shim|BACKWARD COMPATIBILITY SHIM|has been moved to" src/erdos/core
```

Current shim modules:

- `src/erdos/core/arxiv_client.py` → `erdos.core.clients.arxiv`
- `src/erdos/core/crossref_client.py` → `erdos.core.clients.crossref`
- `src/erdos/core/openalex_client.py` → `erdos.core.clients.openalex`
- `src/erdos/core/embeddings.py` → `erdos.core.search.embeddings`
- `src/erdos/core/index_builder.py` → `erdos.core.search.index_builder`
- `src/erdos/core/search_index.py` → `erdos.core.search.facade` (+ `erdos.core.search.types`)
- `src/erdos/core/pdf_converter.py` → `erdos.core.pdf.converter`
- `src/erdos/core/patch_validator.py` → `erdos.core.loop.patch_validator`
- `src/erdos/core/loop_config.py` → `erdos.core.loop.config`
- `src/erdos/core/loop_verifier.py` → `erdos.core.loop.verifier`
- `src/erdos/core/batch.py` → `erdos.core.batch.*`

---

## Recommended Fix

1. **Update imports** across `src/erdos/` and `tests/` to use the new locations directly.
2. **Update docs/specs** that reference old import paths (SSOT should point at the refactored modules).
3. **Delete shim modules** listed above.
4. Add a regression guard:
   - a unit test (or `scripts/audit_code_health.py` rule) that fails if any shim file is reintroduced.

---

## Acceptance Criteria

1. [ ] No remaining references to shim modules in source or tests:
   - `rg -n "erdos\\.core\\.(arxiv_client|crossref_client|openalex_client|embeddings|index_builder|search_index|pdf_converter|patch_validator|loop_config|loop_verifier|batch)\\b" src/ tests/` returns no matches
2. [ ] All shim modules deleted
3. [ ] `make ci` passes

---

## Non-Goals

- Renaming the refactored bounded-context packages
- Changing CLI UX or JSON schemas
