# DEBT-045: `SearchIndexProtocol` Violates ISP (Interface Segregation) and Encourages Over-Coupling

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SOLID audit (ISP/DIP)
**Fixed In:** 279928f

---

## Summary

`src/erdos/core/ports.py` defines `SearchIndexProtocol` as a single, broad interface covering:
- FTS/BM25 search,
- indexing,
- stats,
- embedding metadata,
- embedding build,
- semantic + hybrid search.

This violates **Interface Segregation (ISP)**: many call sites only need "search BM25", but are typed against an interface that implies "embeddings exist".

Over time, this makes it easier to accidentally couple unrelated subsystems (e.g., a basic command now "needs embedding APIs"), and it increases refactor cost.

---

## Evidence

- `src/erdos/core/ports.py`: `SearchIndexProtocol` includes both core search and embedding APIs.
- Commands that only need BM25/FTS end up importing embedding-related types or carrying embedding-only concerns.

Reproduce:
- Protocol definition: `rg -n "class SearchIndexProtocol" src/erdos/core/ports.py`

---

## Why This Matters

- **ISP:** clients should not depend on methods they do not use.
- **DIP:** wide protocols become "god interfaces", making it harder to substitute partial implementations in tests.
- **OCP:** adding "one more index capability" forces editing a central protocol and rippling type changes across the codebase.

---

## Recommended Fix

Split the protocol into smaller, intention-revealing ports:

```text
SearchIndexReadPort      # search(), stats(), counts
SearchIndexWritePort     # index_problem(), clear()
EmbeddingIndexPort       # has_embeddings(), build_embeddings(), search_semantic(), search_hybrid()
```

Then compose where needed:
- `SearchIndexProtocol = SearchIndexReadPort | SearchIndexWritePort` (typing alias), or keep a compatibility Protocol that inherits the smaller ones.

---

## Acceptance Criteria

1. [x] Ports are split into ≥2 focused protocols.
2. [x] Call sites that only require BM25/FTS depend only on the read port.
3. [x] Concrete `SearchIndex` still satisfies the combined protocol(s).
4. [x] No public import breakage (keep `SearchIndexProtocol` as compatibility alias if needed).
5. [x] `make ci` passes.

---

## Implementation Notes

Split `SearchIndexProtocol` into three focused ports:

1. **`SearchIndexReadPort`** (lines 81-101 in ports.py):
   - `search()`, `problem_count()`, `chunk_count()`, `get_stats()`
   - Used by: `ask/retrieval.py`, `search/service.py::search_fts()`, `mcp/server.py::mcp_search_index()`

2. **`SearchIndexWritePort`** (lines 104-112):
   - `index_problem()`, `clear()`
   - Used by: `index_builder.py::build_index()`

3. **`EmbeddingIndexPort`** (lines 115-147):
   - `has_embeddings()`, `get_embedding_metadata()`, `set_embedding_metadata()`
   - `build_embeddings()`, `search_semantic()`, `search_hybrid()`
   - Used by: `search/service.py::search_semantic()`, `search/service.py::search_hybrid()`

4. **`SearchIndexProtocol`** (lines 150-163):
   - Backward-compatible aggregate that inherits all three ports
   - Kept for call sites that need the full interface (e.g., `execute_search()`)

---

## Non-Goals

- Changing search algorithms or schema.
- Changing CLI UX.
