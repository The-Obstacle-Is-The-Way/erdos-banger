# DEBT-062: `search/service.py` Exceeds Module LOC Threshold

**Status:** Open
**Priority:** P1
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

`src/erdos/core/search/service.py` is 626 LOC, exceeding the 500 LOC threshold for core modules by 25%. It contains four distinct search algorithms plus result formatting logic, violating Single Responsibility Principle.

---

## Evidence

```bash
wc -l src/erdos/core/search/service.py
# 626 lines
```

**Functions in this module:**
- `search_fts()` - 77 LOC - FTS5 full-text search
- `search_basic()` - 78 LOC - Basic search wrapper
- `search_semantic()` - 79 LOC - Semantic/embedding search
- `search_hybrid()` - 83 LOC - BM25 + semantic hybrid
- `_enrich_result()` - Result enrichment helper
- `_format_snippet()` - Snippet formatting helper
- `execute_search()` - Main dispatch function

**SOLID violations:**
- **SRP**: Four distinct algorithms + formatting in one module = 5+ reasons to change
- **OCP**: Adding new search mode requires modifying this file

---

## Recommended Fix

Extract each search algorithm into a strategy module:

```text
src/erdos/core/search/
├── service.py           # Thin orchestrator (<150 LOC)
├── strategies/
│   ├── __init__.py
│   ├── fts.py          # FTS5 implementation
│   ├── basic.py        # Basic search wrapper
│   ├── semantic.py     # Semantic/embedding search
│   └── hybrid.py       # BM25 + semantic hybrid
└── enrichment.py       # Result enrichment utilities
```

1. Create `SearchStrategy` protocol in `core/ports.py`
2. Extract each `search_*()` function into its own strategy module
3. Keep `service.py` as thin orchestrator that selects and invokes strategy
4. Extract `_enrich_result()` and formatting into `enrichment.py`

---

## Acceptance Criteria

1. [ ] `src/erdos/core/search/service.py` reduced to ≤ 200 LOC
2. [ ] Each strategy module ≤ 150 LOC
3. [ ] `SearchStrategy` protocol defined in `core/ports.py`
4. [ ] All existing tests pass without modification (behavior preserved)
5. [ ] `make ci` passes

---

## Non-Goals

- Changing search algorithm implementations
- Modifying CLI interface or JSON output format
- Adding new search modes (that would be a feature)
