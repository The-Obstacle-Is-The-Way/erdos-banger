# DEBT-038: MetadataProvider Abstraction Missing

**Status:** Resolved
**Resolved In:** SPEC-022
**Priority:** P2
**Found:** 2026-01-21
**Found By:** API orchestration architecture review
**Resolution:** SPEC-022 implemented the MetadataProvider protocol and provider chain

---

## Summary

The codebase has separate clients for each metadata source (`arxiv_client.py`, `crossref_client.py`, `openalex_client.py`) but lacks a unified `MetadataProvider` protocol/interface. This violates:

1. **Dependency Inversion Principle (DIP)** - High-level ingest logic depends on concrete clients
2. **Open/Closed Principle (OCP)** - Adding new sources requires modifying existing code

---

## Current State

```
src/erdos/core/
├── arxiv_client.py      # ArxivClient class
├── crossref_client.py   # fetch_crossref_work(), parse_crossref_work()
├── openalex_client.py   # OpenAlexClient class
└── ingest/
    └── fetch.py         # Hardcoded source selection + concrete client construction
```

The ingest pipeline in `src/erdos/core/ingest/fetch.py` currently:

1. Selects a metadata source via the `MetadataSource` enum / `source` parameter.
2. Constructs concrete clients inside the fetch layer (e.g., `OpenAlexClient(config)`).
3. Uses branching logic inside `fetch_reference_entry()` to decide which concrete code path to run.

```python
# Current (as of HEAD, simplified)
def fetch_reference_entry(..., source: MetadataSource = MetadataSource.OPENALEX) -> ManifestEntry:
    ...
    if source == MetadataSource.OPENALEX:
        if ref.doi:
            return _fetch_openalex_by_doi(...)
        if ref.arxiv_id:
            return _fetch_openalex_by_arxiv(...)
        raise ValueError(...)

    # Legacy behavior: Crossref/arXiv directly
    if ref.doi and ref.arxiv_id:
        return _fetch_doi_with_arxiv(...)
    if ref.doi:
        return _fetch_doi_only(...)
    if ref.arxiv_id:
        return _fetch_arxiv_only(...)
    raise ValueError(...)
```

---

## Desired State (Rob C. Martin Principles)

### MetadataProvider Protocol

```python
# src/erdos/core/ports.py (or ports/metadata.py)

from typing import Protocol
from erdos.core.models import ReferenceRecord

class MetadataProvider(Protocol):
    """Port for academic metadata sources (DIP)."""

    @property
    def provider_name(self) -> str:
        """Human-readable provider name (for logs/debugging)."""
        ...

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work by DOI (return None if not found)."""
        ...

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch work by arXiv ID (return None if not found)."""
        ...

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract."""
        ...
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    High-Level Policy                         │
│                  (IngestService, AskService)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ depends on abstraction
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               MetadataProvider (Protocol/Port)              │
│  get_by_doi(doi) -> ReferenceRecord | None                  │
│  get_by_arxiv(arxiv_id) -> ReferenceRecord | None           │
│  search(query) -> List[ReferenceRecord]                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ implemented by
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ OpenAlexProv │   │ CrossrefProv │   │  FutureProv  │
│  (Primary)   │   │  (Fallback)  │   │ (Pluggable)  │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Ingest With Provider

```python
# Desired state
def fetch_reference_metadata(
    ref_id: str,
    *,
    provider: MetadataProvider,  # Injected dependency
) -> ReferenceRecord:
    """Fetch reference metadata using the injected provider."""
    if is_doi(ref_id):
        return provider.get_by_doi(ref_id)
    elif is_arxiv_id(ref_id):
        return provider.get_by_arxiv(ref_id)
    else:
        raise ValueError(f"Unknown reference format: {ref_id}")
```

### Composition at the Entrypoint (Recommended)

```python
# src/erdos/core/context.py
from erdos.core.openalex_client import OpenAlexConfig
from erdos.core.providers import CrossrefProvider, FallbackProvider, OpenAlexProvider

def build_metadata_provider(*, mailto: str, timeout: float) -> MetadataProvider:
    """OpenAlex (primary) → Crossref (fallback)."""
    primary = OpenAlexProvider.from_config(OpenAlexConfig(email=mailto, timeout=timeout))
    fallback = CrossrefProvider(mailto=mailto, timeout=timeout)
    return FallbackProvider(primary, fallback)
```

---

## Benefits

1. **Testability** - Inject mock providers in tests
2. **Extensibility** - Add Semantic Scholar, Exa, zbMATH without modifying ingest code
3. **Clarity** - Clear separation of concerns
4. **Configuration** - Swap providers via config/env

---

## Implementation Steps

1. [ ] Create `MetadataProvider` protocol in `src/erdos/core/ports.py`
2. [ ] Create `OpenAlexProvider` wrapper (adapts `OpenAlexClient` to the protocol)
3. [ ] Create `CrossrefProvider` wrapper (adapts `crossref_client` functions to the protocol)
4. [ ] Add `build_metadata_provider(mailto, timeout)` (composition helper) in `src/erdos/core/context.py`
5. [ ] Refactor `ingest/fetch.py` to accept `MetadataProvider` instead of string source
6. [ ] Add `FallbackProvider` that chains providers (OpenAlex → Crossref)
7. [ ] Update tests to inject mock providers

---

## Acceptance Criteria

1. [ ] `MetadataProvider` protocol exists and is documented
2. [ ] OpenAlex and Crossref implement the protocol
3. [ ] Ingest service accepts provider via dependency injection
4. [ ] Tests use mock providers (no network calls in unit tests)
5. [ ] Adding a new source requires only: new provider + registration

---

## Related

- `BUG-018`: OpenAlex `get_by_arxiv()` bug (fixed; see archived bug deck)
- `SPEC-020`: OpenAlex integration spec
- `docs/specs/master-qualifications.md`: Section 5 (API Orchestration Strategy)

---

## References

- [Protocol classes in Python](https://peps.python.org/pep-0544/)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Ports and Adapters / Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
