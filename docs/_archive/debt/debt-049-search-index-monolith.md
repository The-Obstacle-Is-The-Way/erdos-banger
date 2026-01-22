# DEBT-049: `SearchIndex` Is a Monolith (Schema + Indexing + Retrieval + Embeddings)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SRP / cohesion audit
**Fixed In:** 96ec69a

---

## Summary

`src/erdos/core/search_index.py` (**679** LOC) implemented a large "everything search" class:

- schema creation/migration (`_ensure_schema`)
- connection management (`_connect`)
- indexing (problems + chunks)
- retrieval (FTS, snippets)
- semantic/hybrid search
- embedding storage + metadata

This was cohesive "at the feature level" but violated SRP at the class level.

---

## Fix Applied

Extracted into focused modules within the existing `src/erdos/core/search/` subpackage:

```text
src/erdos/core/search/
├── __init__.py          # Re-exports (existing)
├── db.py                # DatabaseManager: SQLite connect + schema (41 LOC)
├── indexer.py           # Indexer: write path (45 LOC)
├── bm25.py              # BM25Search: FTS search + snippets (27 LOC)
├── embeddings_store.py  # EmbeddingsStore: embedding storage + semantic search (81 LOC)
├── hybrid.py            # HybridSearch: combined BM25+semantic (35 LOC)
├── facade.py            # SearchIndex: thin facade (69 LOC)
├── service.py           # Search orchestration (existing)
└── types.py             # Contract types (existing)
```

The `search_index.py` at `core/` level is now a backward-compatible shim (37 LOC) that re-exports from the facade.

---

## Acceptance Criteria

1. [x] `SearchIndex` becomes a thin facade delegating to focused collaborators (or is replaced by focused classes used by a facade).
2. [x] The DB schema manager is isolated (schema changes don't require touching search algorithms).
3. [x] Hybrid/semantic logic lives outside the DB plumbing module.
4. [x] No public import breakage (`search_index.py` shim allowed for one release).
5. [x] `make ci` passes.

---

## Non-Goals

- Changing ranking behavior or results schema.
- Switching away from SQLite FTS5.
