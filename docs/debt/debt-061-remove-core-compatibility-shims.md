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

**SSOT shim inventory (core root only)**

These are the *only* `src/erdos/core/*.py` modules that explicitly declare themselves as backward-compatibility shims:

```bash
rg -l "Backward-compatible shim|BACKWARD COMPATIBILITY SHIM|has been moved to" src/erdos/core/*.py
```

Expected output (11 files):

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
- `src/erdos/core/batch.py` → **dead/unreachable file** (see note below)

**Important note about `src/erdos/core/batch.py`**

`src/erdos/core/` currently contains both:
- `src/erdos/core/batch/` (the real package; **this is what `import erdos.core.batch` resolves to**), and
- `src/erdos/core/batch.py` (a shim file that is **not imported** in practice and would recurse if it were).

This file should be deleted as part of this debt item to eliminate confusion, but it does **not** require import-path updates because the canonical path is already `erdos.core.batch` (the package).

---

## Recommended Fix

1. **Update imports** across `src/erdos/` and `tests/` to use the refactored modules directly.
   - Mapping (old → new):
     - `erdos.core.arxiv_client` → `erdos.core.clients.arxiv`
     - `erdos.core.crossref_client` → `erdos.core.clients.crossref`
     - `erdos.core.openalex_client` → `erdos.core.clients.openalex`
     - `erdos.core.embeddings` → `erdos.core.search.embeddings`
     - `erdos.core.index_builder` → `erdos.core.search.index_builder`
     - `erdos.core.search_index` → `erdos.core.search.*` (use the real modules: `core/search/facade.py`, `core/search/db.py`, `core/search/types.py`)
     - `erdos.core.pdf_converter` → `erdos.core.pdf.converter`
     - `erdos.core.patch_validator` → `erdos.core.loop.patch_validator`
     - `erdos.core.loop_config` → `erdos.core.loop.config`
     - `erdos.core.loop_verifier` → `erdos.core.loop.verifier`
   - `src/erdos/core/batch.py`: delete (no import updates required; `erdos.core.batch` is already a package)
2. **Update docs/specs** that reference old import paths (SSOT must point at the refactored modules above).
3. **Delete shim modules** listed above.
4. **Add a regression guard** so shims can’t creep back in:
   - a unit test that fails if any of the 11 shim files exist, and
   - a grep-based test that fails if any code imports the old module paths.

---

## Acceptance Criteria

1. [ ] Shim files are gone (core root only):
   - `rg -l "Backward-compatible shim|BACKWARD COMPATIBILITY SHIM|has been moved to" src/erdos/core/*.py` returns no matches
   - `test ! -f src/erdos/core/batch.py`
2. [ ] No remaining imports of the removed shim module paths:
   - `rg -n "erdos\\.core\\.(arxiv_client|crossref_client|openalex_client|embeddings|index_builder|search_index|pdf_converter|patch_validator|loop_config|loop_verifier)\\b" src/ tests/` returns no matches
3. [ ] Full quality gates pass:
   - `make ci`
   - `make test-all` (ensures we didn’t break `requires_network` / full-suite coverage)

---

## Non-Goals

- Renaming the refactored bounded-context packages
- Changing CLI UX or JSON schemas
