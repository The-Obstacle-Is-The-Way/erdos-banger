# DEBT-045: `SearchIndexProtocol` Violates ISP (Interface Segregation) and Encourages Over-Coupling

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SOLID audit (ISP/DIP)

---

## Summary

`src/erdos/core/ports.py` defines `SearchIndexProtocol` as a single, broad interface covering:
- FTS/BM25 search,
- indexing,
- stats,
- embedding metadata,
- embedding build,
- semantic + hybrid search.

This violates **Interface Segregation (ISP)**: many call sites only need “search BM25”, but are typed against an interface that implies “embeddings exist”.

Over time, this makes it easier to accidentally couple unrelated subsystems (e.g., a basic command now “needs embedding APIs”), and it increases refactor cost.

---

## Evidence

- `src/erdos/core/ports.py`: `SearchIndexProtocol` includes both core search and embedding APIs.
- Commands that only need BM25/FTS end up importing embedding-related types or carrying embedding-only concerns.

Reproduce:
- Protocol definition: `rg -n "class SearchIndexProtocol" src/erdos/core/ports.py`

---

## Why This Matters

- **ISP:** clients should not depend on methods they do not use.
- **DIP:** wide protocols become “god interfaces”, making it harder to substitute partial implementations in tests.
- **OCP:** adding “one more index capability” forces editing a central protocol and rippling type changes across the codebase.

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

1. [ ] Ports are split into ≥2 focused protocols.
2. [ ] Call sites that only require BM25/FTS depend only on the read port.
3. [ ] Concrete `SearchIndex` still satisfies the combined protocol(s).
4. [ ] No public import breakage (keep `SearchIndexProtocol` as compatibility alias if needed).
5. [ ] `make ci` passes.

---

## Non-Goals

- Changing search algorithms or schema.
- Changing CLI UX.
