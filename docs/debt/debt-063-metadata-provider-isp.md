# DEBT-063: `MetadataProvider` Protocol Violates Interface Segregation

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

`MetadataProvider` protocol in `src/erdos/core/ports.py` requires all implementers to provide `get_by_doi()`, `get_by_arxiv()`, and `search()` methods. This violates Interface Segregation Principle (ISP) because:

- `ArxivProvider` implements `search()` but returns empty list (never used)
- `CrossrefProvider` implements `get_by_arxiv()` but always returns None (never used)
- Callers often only need one lookup method

---

## Evidence

```python
# src/erdos/core/ports.py lines 23-68
class MetadataProvider(Protocol):
    def get_by_doi(self, doi: str) -> ReferenceRecord | None: ...
    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None: ...
    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]: ...
```

**Implementer compliance:**

| Provider | get_by_doi | get_by_arxiv | search |
|----------|------------|--------------|--------|
| ArxivProvider | Returns None | ✓ Implemented | Returns [] |
| CrossrefProvider | ✓ Implemented | Returns None | ✓ Implemented |
| OpenAlexProvider | ✓ Implemented | ✓ Implemented | ✓ Implemented |
| FallbackProvider | Delegates | Delegates | Delegates |

**ISP violation**: ArxivProvider and CrossrefProvider implement methods they can't fulfill.

---

## Recommended Fix

Split into focused protocols:

```python
class DOILookupProvider(Protocol):
    """Provider that can resolve metadata by DOI."""
    def get_by_doi(self, doi: str) -> ReferenceRecord | None: ...

class ArxivLookupProvider(Protocol):
    """Provider that can resolve metadata by arXiv ID."""
    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None: ...

class SearchableMetadataProvider(Protocol):
    """Provider that supports text search."""
    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]: ...

# Composition for providers that support multiple operations
class FullMetadataProvider(DOILookupProvider, ArxivLookupProvider, SearchableMetadataProvider, Protocol):
    """Provider supporting all metadata operations."""
    pass
```

1. Update `ArxivProvider` to only implement `ArxivLookupProvider`
2. Update `CrossrefProvider` to implement `DOILookupProvider` + `SearchableMetadataProvider`
3. Update `OpenAlexProvider` to implement `FullMetadataProvider`
4. Update `FallbackProvider` to compose appropriately
5. Update callers to depend on the minimal interface they need

---

## Acceptance Criteria

1. [ ] Split `MetadataProvider` into `DOILookupProvider`, `ArxivLookupProvider`, `SearchableMetadataProvider`
2. [ ] Each provider implements only the protocols it can fulfill
3. [ ] Callers updated to depend on minimal required protocol
4. [ ] `FallbackProvider` properly composes protocols
5. [ ] All existing tests pass
6. [ ] `make ci` passes

---

## Non-Goals

- Adding new metadata providers
- Changing provider implementations (only their type annotations)
- Modifying CLI interface
