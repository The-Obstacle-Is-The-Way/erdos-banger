# DEBT-049: `SearchIndex` Is a Monolith (Schema + Indexing + Retrieval + Embeddings)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SRP / cohesion audit

---

## Summary

`src/erdos/core/search_index.py` (**679** LOC) implements a large “everything search” class:

- schema creation/migration (`_ensure_schema`)
- connection management (`_connect`)
- indexing (problems + chunks)
- retrieval (FTS, snippets)
- semantic/hybrid search
- embedding storage + metadata

This is cohesive “at the feature level” but violates SRP at the class level. The result is:
- higher regression risk when modifying one search mode,
- harder targeted unit tests,
- more complicated refactors (schema vs algorithms vs storage).

---

## Evidence

- `src/erdos/core/search_index.py` defines:
  - schema + DB plumbing
  - multiple search methods (`search`, `search_semantic`, `search_hybrid`)
  - embedding metadata and embedding blob persistence
  - Reproduce file size: `wc -l src/erdos/core/search_index.py`

The file has multiple conceptual reasons to change:
- “DB schema changed”
- “snippet generation changed”
- “embedding algorithm changed”
- “hybrid scoring changed”

---

## Recommended Fix (Incremental, Backwards-Compatible)

Extract into a bounded-context package and keep `search_index.py` as a shim:

```text
src/erdos/core/search/
├── __init__.py
├── db.py              # sqlite connect + schema manager
├── indexer.py         # write path: index_problem/index_chunk
├── bm25.py            # FTS search + snippet formatting
├── embeddings.py      # embedding blobs + metadata
├── hybrid.py          # hybrid score composition
└── types.py           # already exists (contract types)
```

Public API stays stable:
- `from erdos.core.search_index import SearchIndex` continues to work (shim re-export).
- Contract types remain re-exported for compatibility (`SearchResult`, etc.).

---

## Acceptance Criteria

1. [ ] `SearchIndex` becomes a thin facade delegating to focused collaborators (or is replaced by focused classes used by a facade).
2. [ ] The DB schema manager is isolated (schema changes don’t require touching search algorithms).
3. [ ] Hybrid/semantic logic lives outside the DB plumbing module.
4. [ ] No public import breakage (`search_index.py` shim allowed for one release).
5. [ ] `make ci` passes.

---

## Non-Goals

- Changing ranking behavior or results schema.
- Switching away from SQLite FTS5.
