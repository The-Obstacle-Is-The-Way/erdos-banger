# DEBT-063: `MetadataProvider` Protocol Violates Interface Segregation

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

`MetadataProvider` protocol in `src/erdos/core/ports.py` requires all implementers to provide `get_by_doi()`, `get_by_arxiv()`, and `search()` methods. This violates Interface Segregation Principle (ISP) because:

- `ArxivProvider` implements **DOI lookup + search** but cannot fulfill them (returns `None` / `[]`)
- `CrossrefProvider` implements **arXiv lookup + search** but cannot fulfill them (returns `None` / `[]`)
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
| ArxivProvider | Returns `None` (unsupported) | ✓ Implemented | Returns `[]` (unsupported) |
| CrossrefProvider | ✓ Implemented | Returns `None` (unsupported) | Returns `[]` (unsupported) |
| OpenAlexProvider | ✓ Implemented | ✓ Implemented | ✓ Implemented |
| FallbackProvider | Delegates | Delegates | Delegates |

**ISP violation**: `ArxivProvider` and `CrossrefProvider` implement methods they cannot fulfill, and the protocol does not let call sites depend on minimal capabilities.

---

## Impacted Files (SSOT)

- `src/erdos/core/ports.py` (protocol definitions)
- `src/erdos/core/providers/arxiv.py` (currently defines unsupported `get_by_doi()` and `search()`)
- `src/erdos/core/providers/crossref.py` (currently defines unsupported `get_by_arxiv()` and `search()`)
- `src/erdos/core/providers/openalex.py` (supports all three)
- `src/erdos/core/providers/fallback.py` (currently assumes a single “do everything” provider interface)
- `src/erdos/core/context.py::build_metadata_provider()` (creates the default chain)
- `src/erdos/core/ingest/fetch.py::_build_provider_from_source()` (builds providers from `MetadataSource`)

---

## Recommended Fix

Split the fat protocol into focused protocols **and update the provider/fallback wiring so unsupported methods disappear**.

Simply adding new Protocols is not sufficient while providers still define stub methods: structural typing will continue to treat them as “implementing” interfaces they shouldn’t. The fix requires removing unsupported methods and updating fallback composition.

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

class MetadataProvider(DOILookupProvider, ArxivLookupProvider, SearchableMetadataProvider, Protocol):
    """Full provider supporting all three operations."""
    @property
    def provider_name(self) -> str: ...
```

Concrete implementation plan:

1. Update providers to only expose supported methods:
   - `src/erdos/core/providers/arxiv.py`: remove `get_by_doi()` and `search()`
   - `src/erdos/core/providers/crossref.py`: remove `get_by_arxiv()` and `search()`
   - `src/erdos/core/providers/openalex.py`: keeps all three
2. Replace `src/erdos/core/providers/fallback.py` with a small router that composes three independent chains:
   - DOI chain: list[`DOILookupProvider`]
   - arXiv chain: list[`ArxivLookupProvider`]
   - search chain: list[`SearchableMetadataProvider`]
3. Update `src/erdos/core/context.py::build_metadata_provider()` to build the router with the correct chains:
   - DOI: OpenAlex → Crossref
   - arXiv: OpenAlex → Arxiv
   - search: OpenAlex only (until another search-capable provider exists)
4. Update call sites to depend on the minimal interface they need (e.g., DOI-only ingest helpers should accept `DOILookupProvider`).

---

## Acceptance Criteria

1. [ ] Split `MetadataProvider` into `DOILookupProvider`, `ArxivLookupProvider`, `SearchableMetadataProvider`
2. [ ] `src/erdos/core/providers/arxiv.py` no longer defines `get_by_doi()` or `search()`
3. [ ] `src/erdos/core/providers/crossref.py` no longer defines `get_by_arxiv()` or `search()`
4. [ ] Fallback composition supports all three operations via dedicated chains (DOI/arXiv/search)
5. [ ] `src/erdos/core/ingest/fetch.py` depends only on the minimal lookup protocols it needs (DOI/arXiv), not the full provider
6. [ ] Call sites depend on the minimal required protocol (mypy enforces this)
7. [ ] All existing tests pass
8. [ ] `make ci` passes

---

## Non-Goals

- Adding new metadata providers
- Changing provider HTTP semantics (requests, parsing, retry/rate-limiting)
- Modifying CLI
