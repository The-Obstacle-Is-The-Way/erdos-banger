# DEBT-062: `src/erdos/core/search/service.py` Is a God Module (626 LOC)

**Status:** Open
**Priority:** P1
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

`src/erdos/core/search/service.py` is **626 LOC** (> `MODULE_LOC_THRESHOLD_CORE=500`, +25%). It currently bundles multiple responsibilities:

- **Search execution paths**: BM25/FTS, basic fallback, semantic, hybrid
- **Index/embedding orchestration**: build index, build embeddings, embedder loading
- **Result shaping/enrichment**: building `CLIOutput` payloads, adding titles to results
- **Test seams**: indirection helpers like `_get_search_index_class()` / `_get_search_index_error()`

This violates **SRP** (many reasons to change) and makes **OCP** worse (adding a search mode tends to require editing this module and its dispatch logic).

---

## Current Guardrail State (Important)

`scripts/audit_code_health.py --strict` reports `src/erdos/core/search/service.py` as a module-size violation, but it is currently **exempted** via an inline marker in the module docstring:

- Current marker in `src/erdos/core/search/service.py`: `# exempt: DEBT-043`
- Problem: **DEBT-043 is archived** and is no longer the correct SSOT for this exemption.

While this debt remains open, the exemption marker should be updated to **`DEBT-062`** so the guardrail points at the correct deck. Once the refactor lands and the module is ≤ 500 LOC, the exemption marker should be removed entirely.

---

## Evidence

```bash
wc -l src/erdos/core/search/service.py
# 626 lines
```

```bash
uv run python scripts/audit_code_health.py --strict
# ⚠️  EXEMPT (DEBT-043)
#   src/erdos/core/search/service.py: 626 LOC (threshold: 500)
```

**Top-level functions (AST-derived LOC):**

- `_enrich_result()` — 18 LOC
- `search_fts()` — 77 LOC
- `search_basic()` — 78 LOC
- `search_with_fallback()` — 43 LOC
- `get_embedding_model()` — 50 LOC
- `build_search_index()` — 27 LOC
- `build_embeddings()` — 43 LOC
- `search_semantic()` — 79 LOC
- `search_hybrid()` — 83 LOC
- `execute_search()` — 40 LOC

**SOLID violations:**
- **SRP**: Search execution + index build + embeddings + output shaping are independent concerns.
- **OCP**: Adding a new mode requires editing `SearchMode`, `SearchOptions`, and `execute_search()` dispatch here.

---

## Recommended Fix

Split `service.py` into smaller, focused modules within the existing `core/search/` bounded context (do **not** invent new layers).

```text
src/erdos/core/search/
├── service.py             # Thin orchestrator (≤200 LOC), no exemptions
├── options.py             # SearchMode, SearchOptions (dataclass)
├── enrichment.py          # _enrich_result() + result-shaping helpers
├── fts_service.py         # search_fts() (CLIOutput-shaping wrapper)
├── basic_service.py       # search_basic()
├── embeddings_service.py  # get_embedding_model(), build_embeddings()
└── indexing_service.py    # build_search_index()
```

Implementation steps (concrete):

1. Move code from `src/erdos/core/search/service.py` into the modules above (keep behavior identical).
1. Update call sites:
   - `src/erdos/commands/search.py`
   - `src/erdos/mcp/server.py`
   - `tests/unit/test_search_command_helpers.py`
   - `src/erdos/core/search/__init__.py` re-exports (if we keep them)
1. Update the module exemption marker in `src/erdos/core/search/service.py` from `DEBT-043` → `DEBT-062` (temporary).
1. Once `service.py` is ≤ 500 LOC, **remove** the exemption marker entirely.

---

## Acceptance Criteria

1. [ ] `src/erdos/core/search/service.py` is ≤ 200 LOC
2. [ ] No core search module exceeds `MODULE_LOC_THRESHOLD_CORE=500` without an exemption marker
3. [ ] `src/erdos/core/search/service.py` no longer contains `# exempt:` markers
4. [ ] `uv run python scripts/audit_code_health.py --strict` reports **no module-size violations** for `core/search/*`
5. [ ] `make ci` passes

---

## Non-Goals

- Changing search algorithm implementations
- Modifying CLI or JSON output format
- Adding new search modes (that would be a feature)
