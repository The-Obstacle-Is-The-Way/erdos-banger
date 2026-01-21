# SPEC-022: MetadataProvider Orchestration

**Status:** Complete
**Implemented In:** 6e599a1
**Priority:** P2
**Created:** 2026-01-21
**Resolves:** DEBT-038
**Version Target:** v2.1
**Related ADR:** [ADR-001](../adr/adr-001-metadata-provider-orchestration.md)

---

## Executive Summary

Wire the existing **metadata** clients (OpenAlex primary, Crossref fallback) through a unified `MetadataProvider` protocol, enabling:

1. **Dependency Inversion** - High-level code depends on abstraction, not concrete clients
2. **Pluggable Sources** - Add new sources (Semantic Scholar, Exa, zbMATH) without modifying ingest code
3. **Fallback Chains** - Automatic failover (OpenAlex → Crossref) with retry semantics
4. **Testability** - Inject mock providers in unit tests

**Non-goal:** arXiv source download/extraction is **content**, not metadata. It remains a separate path (download via `arXiv e-print` + extract LaTeX) and is not part of `MetadataProvider`.

---

## Current State (The Problem)

### Architecture Diagram (AS-IS)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ingest/fetch.py                                 │
│                                                                             │
│   fetch_reference_entry(ref, source=OPENALEX, ...)                          │
│       │                                                                     │
│       ├── if source == OPENALEX:                                            │
│       │       client = OpenAlexClient(config)  ← DIRECT CONSTRUCTION        │
│       │       return _fetch_openalex_by_doi(client, ...)                    │
│       │                                                                     │
│       ├── elif source == CROSSREF:                                          │
│       │       return _fetch_doi_only(...)  ← CALLS crossref_client DIRECTLY │
│       │                                                                     │
│       └── elif source == ARXIV:                                             │
│               return _fetch_arxiv_only(...)  ← CALLS arxiv_client DIRECTLY  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Problems with Current Design

| Violation | Description |
|-----------|-------------|
| **DIP** | `fetch_reference_entry()` constructs `OpenAlexClient` directly (line 262, 291) |
| **OCP** | Adding a new source requires modifying `fetch_reference_entry()` |
| **SRP** | `fetch.py` knows about ALL client implementations |
| **Testability** | Can't inject mock clients without monkeypatching |

### Evidence (Code References)

```python
# src/erdos/core/ingest/fetch.py:262
client = OpenAlexClient(config)  # Direct construction inside function

# src/erdos/core/ingest/fetch.py:339-426
if source == MetadataSource.OPENALEX:
    # 87 lines of OpenAlex-specific logic
elif source == MetadataSource.ARXIV:
    # Different path
elif source == MetadataSource.CROSSREF:
    # Different path
```

---

## Target State (The Solution)

### Architecture Diagram (TO-BE)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         High-Level Policy Layer                              │
│                    (IngestService, Commands, Loop)                           │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ depends on abstraction only
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MetadataProvider (Protocol/Port)                          │
│                                                                             │
│   get_by_doi(doi: str) -> ReferenceRecord | None                            │
│   get_by_arxiv(arxiv_id: str) -> ReferenceRecord | None                     │
│   search(query: str, limit: int) -> list[ReferenceRecord]                   │
│   provider_name: str  # For logging/debugging                               │
│                                                                             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ implemented by
        ┌───────────────────────┼───────────────────────────┐
        │                       │                           │
        ▼                       ▼                           ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐
│ OpenAlexProvider │  │ CrossrefProvider │  │     FallbackProvider         │
│                  │  │                  │  │                              │
│ Wraps existing   │  │ Wraps existing   │  │ Chains: primary → fallback   │
│ OpenAlexClient   │  │ crossref_client  │  │ e.g., OpenAlex → Crossref    │
│                  │  │ functions        │  │                              │
│ • Implements     │  │ • Implements     │  │ • Implements MetadataProvider│
│   MetadataProvider│  │   MetadataProvider│  │ • Handles failover logic     │
└──────────────────┘  └──────────────────┘  └──────────────────────────────┘
        │                       │                           │
        └───────────────────────┴───────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Composition at the entrypoint (recommended)                 │
│                                                                             │
│   provider = build_metadata_provider(mailto=..., timeout=...)               │
│   # OpenAlex (primary) → Crossref (fallback)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Protocol, not ABC** - Use `typing.Protocol` for structural subtyping (duck typing)
2. **Wrap, don't rewrite** - Existing clients become implementation details of providers
3. **Fallback is a provider** - `FallbackProvider` implements `MetadataProvider` and chains others
4. **Composition at the edge** - Wire providers at the entrypoint (command/service/AppContext factory), never inside `ingest/fetch.py`

---

## Scope

### In Scope

- [x] `MetadataProvider` protocol in `src/erdos/core/ports.py`
- [x] `OpenAlexProvider` wrapper in `src/erdos/core/providers/openalex.py`
- [x] `CrossrefProvider` wrapper in `src/erdos/core/providers/crossref.py`
- [x] `FallbackProvider` in `src/erdos/core/providers/fallback.py`
- [x] Add `build_metadata_provider(mailto, timeout)` in `src/erdos/core/context.py` (entrypoint composition helper)
- [x] Refactor `ingest/fetch.py` to accept `MetadataProvider` parameter
- [x] Unit tests with mock providers (no network calls)
- [x] Integration tests with real providers (marked `requires_network`)

### Out of Scope

- ArxivProvider for metadata (arXiv is for content, not metadata - use OpenAlex for arXiv metadata)
- New source integrations (Semantic Scholar, Exa, zbMATH) - future specs
- Retry/rate-limit logic changes - existing `retry.py` and `rate_limiter.py` are sufficient
- CLI changes - `--source` flag can remain but maps to provider selection

---

## Implementation

### Step 1: Define the Protocol

**File:** `src/erdos/core/ports.py`

```python
class MetadataProvider(Protocol):
    """Port for academic metadata sources (SPEC-022).

    High-level ingest code depends on this abstraction, not concrete clients.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name for logging."""
        ...

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work metadata by DOI.

        Returns:
            ReferenceRecord if found, None if not found.

        Raises:
            requests.RequestException: On network/API errors.
            ValueError: On invalid identifiers or irrecoverable parse errors.
        """
        ...

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch work metadata by arXiv ID.

        Note: This fetches METADATA about the arXiv paper (title, authors, etc.),
        not the source content. For content, use ArxivClient directly.

        Returns:
            ReferenceRecord if found, None if not found.

        Raises:
            requests.RequestException: On network/API errors.
            ValueError: On invalid arXiv identifiers or irrecoverable parse errors.
        """
        ...

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract.

        Returns:
            List of matching ReferenceRecords, possibly empty.
        """
        ...
```

### Step 2: Create Provider Package

**Directory:** `src/erdos/core/providers/`

```
src/erdos/core/providers/
├── __init__.py           # Re-exports: OpenAlexProvider, CrossrefProvider, FallbackProvider
├── openalex.py           # OpenAlexProvider
├── crossref.py           # CrossrefProvider
└── fallback.py           # FallbackProvider
```

### Step 3: OpenAlexProvider

**File:** `src/erdos/core/providers/openalex.py`

```python
"""OpenAlex metadata provider (SPEC-022)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from erdos.core.models import ReferenceRecord
from erdos.core.openalex_client import OpenAlexClient, OpenAlexConfig


logger = logging.getLogger(__name__)


@dataclass
class OpenAlexProvider:
    """MetadataProvider implementation using OpenAlex API.

    Wraps the existing OpenAlexClient to conform to the MetadataProvider protocol.
    """

    _client: OpenAlexClient

    @property
    def provider_name(self) -> str:
        return "openalex"

    @classmethod
    def from_env(cls) -> OpenAlexProvider:
        """Create provider with config from environment."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)
        return cls(_client=client)

    @classmethod
    def from_config(cls, config: OpenAlexConfig) -> OpenAlexProvider:
        """Create provider with explicit config."""
        client = OpenAlexClient(config)
        return cls(_client=client)

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work by DOI via OpenAlex."""
        logger.debug("OpenAlex lookup by DOI: %s", doi)
        try:
            return self._client.get_by_doi(doi)
        except requests.HTTPError as e:
            # Normalize "not found" to None so fallback chains can proceed.
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch work by arXiv ID via OpenAlex."""
        logger.debug("OpenAlex lookup by arXiv: %s", arxiv_id)
        try:
            return self._client.get_by_arxiv(arxiv_id)
        except ValueError:
            # OpenAlexClient raises ValueError when the arXiv paper cannot be resolved.
            return None
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works via OpenAlex."""
        logger.debug("OpenAlex search: %s (limit=%d)", query, limit)
        return self._client.search(query, limit=limit)
```

### Step 4: CrossrefProvider

**File:** `src/erdos/core/providers/crossref.py`

```python
"""Crossref metadata provider (SPEC-022)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import requests

from erdos.core.crossref_client import fetch_crossref_work, parse_crossref_work
from erdos.core.models import ReferenceRecord


logger = logging.getLogger(__name__)


@dataclass
class CrossrefProvider:
    """MetadataProvider implementation using Crossref API.

    Note: Crossref is DOI-only. arXiv lookups and search are not supported.
    """

    mailto: str
    timeout: float = 30.0

    @property
    def provider_name(self) -> str:
        return "crossref"

    @classmethod
    def from_env(cls) -> CrossrefProvider:
        """Create provider using ERDOS_MAILTO for Crossref's polite pool."""
        # Keep a stable default for local dev, but real usage should set ERDOS_MAILTO.
        mailto = os.environ.get("ERDOS_MAILTO", "erdos-banger@example.com")
        return cls(mailto=mailto)

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work by DOI via Crossref."""
        logger.debug("Crossref lookup by DOI: %s", doi)
        try:
            raw = fetch_crossref_work(doi, mailto=self.mailto, timeout=self.timeout)
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise
        return parse_crossref_work(raw, doi=doi)

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Crossref does not support arXiv ID lookups."""
        logger.debug("Crossref does not support arXiv lookup: %s", arxiv_id)
        return None

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Crossref search is not implemented (use OpenAlex for search)."""
        logger.debug("Crossref search not implemented")
        return []
```

### Step 5: FallbackProvider

**File:** `src/erdos/core/providers/fallback.py`

```python
"""Fallback metadata provider chain (SPEC-022)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from erdos.core.models import ReferenceRecord
from erdos.core.ports import MetadataProvider


logger = logging.getLogger(__name__)


@dataclass
class FallbackProvider:
    """MetadataProvider that chains multiple providers with fallback.

    Tries the primary provider first. If it returns None (not found) or raises
    an exception, falls back to the next provider in the chain.

    Example:
        provider = FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider.from_env(),
        )
        # Tries OpenAlex first, falls back to Crossref if OpenAlex fails
    """

    providers: list[MetadataProvider] = field(default_factory=list)

    def __init__(self, *providers: MetadataProvider) -> None:
        """Initialize with ordered list of providers."""
        self.providers = list(providers)
        if not self.providers:
            raise ValueError("FallbackProvider requires at least one provider")

    @property
    def provider_name(self) -> str:
        names = [p.provider_name for p in self.providers]
        return f"fallback({' -> '.join(names)})"

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Try each provider in order until one returns a result."""
        for provider in self.providers:
            try:
                result = provider.get_by_doi(doi)
                if result is not None:
                    logger.debug(
                        "DOI %s resolved by %s", doi, provider.provider_name
                    )
                    return result
                logger.debug(
                    "DOI %s not found in %s, trying next", doi, provider.provider_name
                )
            except Exception:
                logger.warning(
                    "Provider %s failed for DOI %s, trying next",
                    provider.provider_name,
                    doi,
                    exc_info=True,
                )
        logger.debug("DOI %s not found in any provider", doi)
        return None

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Try each provider in order until one returns a result."""
        for provider in self.providers:
            try:
                result = provider.get_by_arxiv(arxiv_id)
                if result is not None:
                    logger.debug(
                        "arXiv %s resolved by %s", arxiv_id, provider.provider_name
                    )
                    return result
                logger.debug(
                    "arXiv %s not found in %s, trying next",
                    arxiv_id,
                    provider.provider_name,
                )
            except Exception:
                logger.warning(
                    "Provider %s failed for arXiv %s, trying next",
                    provider.provider_name,
                    arxiv_id,
                    exc_info=True,
                )
        logger.debug("arXiv %s not found in any provider", arxiv_id)
        return None

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Use first provider that returns non-empty results."""
        for provider in self.providers:
            try:
                results = provider.search(query, limit=limit)
                if results:
                    logger.debug(
                        "Search '%s' returned %d results from %s",
                        query,
                        len(results),
                        provider.provider_name,
                    )
                    return results
            except Exception:
                logger.warning(
                    "Provider %s failed for search '%s', trying next",
                    provider.provider_name,
                    query,
                    exc_info=True,
                )
        logger.debug("Search '%s' returned no results from any provider", query)
        return []
```

### Step 6: Update AppContext

**File:** `src/erdos/core/context.py`

```python
"""Application wiring (SPEC-022 update)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from erdos.core.problem_loader import ProblemLoader
from erdos.core.openalex_client import OpenAlexConfig
from erdos.core.providers import CrossrefProvider, FallbackProvider, OpenAlexProvider
from erdos.core.search_index import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import MetadataProvider, ProblemRepository, SearchIndexProtocol


@dataclass
class AppContext:
    """Dependency container for CLI commands.

    Providers should be composed at the entrypoint (command/service/context
    factory), not inside low-level ingest functions.
    """

    problems: ProblemRepository
    index: SearchIndexProtocol | None = None

    @classmethod
    def from_environment(cls) -> AppContext:
        """Create context using environment defaults."""
        return cls(problems=ProblemLoader.from_default())

    def ensure_index(self) -> SearchIndexProtocol:
        """Ensure the search index dependency exists."""
        if self.index is None:
            self.index = SearchIndex.from_default()
        return self.index


def build_metadata_provider(*, mailto: str, timeout: float) -> MetadataProvider:
    """Create the default metadata provider chain (OpenAlex → Crossref).

    This function exists so call sites can pass CLI-derived configuration (e.g.,
    `--mailto`, `--timeout`) without constructing concrete clients inside
    `ingest/fetch.py`.
    """
    primary = OpenAlexProvider.from_config(OpenAlexConfig(email=mailto, timeout=timeout))
    fallback = CrossrefProvider(mailto=mailto, timeout=timeout)
    return FallbackProvider(primary, fallback)
```

### Step 7: Refactor ingest/fetch.py

**Key Changes:**

1. Remove direct `OpenAlexClient` construction
2. Accept `MetadataProvider` as parameter
3. Remove `MetadataSource` enum (or keep for backward compat CLI flag)

```python
# BEFORE (current)
def fetch_reference_entry(
    ref: ReferenceEntry,
    repo_root: Path,
    timeout: float,
    no_download: bool,
    source: MetadataSource = MetadataSource.OPENALEX,
) -> ManifestEntry:
    if source == MetadataSource.OPENALEX:
        client = OpenAlexClient(config)  # Direct construction
        ...

# AFTER (target)
def fetch_reference_entry(
    ref: ReferenceEntry,
    repo_root: Path,
    timeout: float,
    no_download: bool,
    provider: MetadataProvider,  # Injected dependency
) -> ManifestEntry:
    if ref.doi:
        record = provider.get_by_doi(ref.doi)
    elif ref.arxiv_id:
        record = provider.get_by_arxiv(ref.arxiv_id)
    else:
        raise ValueError(f"Reference {ref.key} has no DOI or arXiv ID")

    if record is None:
        raise ValueError(f"Reference {ref.key} not found in {provider.provider_name}")

    # Continue with manifest creation using `record`
    ...
```

---

## Testing Strategy

### Unit Tests (No Network)

**File:** `tests/unit/test_providers.py`

```python
"""Unit tests for MetadataProvider implementations (SPEC-022)."""

import pytest
from unittest.mock import MagicMock

from erdos.core.models import ReferenceRecord
from erdos.core.providers import FallbackProvider


class MockProvider:
    """Mock MetadataProvider for testing."""

    def __init__(self, name: str, results: dict | None = None):
        self.provider_name = name
        self._results = results or {}

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        return self._results.get(("doi", doi))

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        return self._results.get(("arxiv", arxiv_id))

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        return self._results.get(("search", query), [])


class TestFallbackProvider:
    """Tests for FallbackProvider."""

    def test_uses_primary_when_successful(self) -> None:
        """Primary provider result is returned if found."""
        record = ReferenceRecord(title="Test", doi="10.1234/test")
        primary = MockProvider("primary", {("doi", "10.1234/test"): record})
        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_falls_back_when_primary_returns_none(self) -> None:
        """Fallback is used when primary returns None."""
        record = ReferenceRecord(title="Test", doi="10.1234/test")
        primary = MockProvider("primary")  # Returns None
        fallback = MockProvider("fallback", {("doi", "10.1234/test"): record})

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_falls_back_when_primary_raises(self) -> None:
        """Fallback is used when primary raises exception."""
        record = ReferenceRecord(title="Test", doi="10.1234/test")

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.get_by_doi.side_effect = Exception("API error")

        fallback = MockProvider("fallback", {("doi", "10.1234/test"): record})

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_returns_none_when_all_providers_fail(self) -> None:
        """None is returned when all providers return None."""
        primary = MockProvider("primary")
        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/nonexistent")

        assert result is None

    def test_provider_name_shows_chain(self) -> None:
        """Provider name reflects the fallback chain."""
        primary = MockProvider("openalex")
        fallback = MockProvider("crossref")

        provider = FallbackProvider(primary, fallback)

        assert provider.provider_name == "fallback(openalex -> crossref)"
```

### Integration Tests (With Network)

**File:** `tests/integration/test_providers_network.py`

```python
"""Integration tests for MetadataProvider with real APIs."""

import pytest

from erdos.core.providers import OpenAlexProvider, CrossrefProvider, FallbackProvider


@pytest.mark.requires_network
class TestOpenAlexProviderIntegration:
    """Integration tests for OpenAlexProvider."""

    def test_get_by_doi_real(self) -> None:
        """Test real DOI lookup via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        # Use a known, stable DOI
        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert "nature" in result.title.lower() or result.doi == "10.1038/nature12373"

    def test_get_by_arxiv_real(self) -> None:
        """Test real arXiv lookup via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        # Use a known arXiv paper
        result = provider.get_by_arxiv("2103.03874")

        assert result is not None


@pytest.mark.requires_network
class TestFallbackProviderIntegration:
    """Integration tests for fallback behavior."""

    def test_openalex_to_crossref_fallback(self) -> None:
        """Test that Crossref is used when OpenAlex fails."""
        provider = FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider.from_env(),
        )

        # A DOI that should exist in either
        result = provider.get_by_doi("10.1038/nature12373")
        assert result is not None
```

---

## Acceptance Criteria

1. [x] `MetadataProvider` protocol exists in `src/erdos/core/ports.py`
2. [x] `OpenAlexProvider` implements `MetadataProvider` and wraps `OpenAlexClient`
3. [x] `CrossrefProvider` implements `MetadataProvider` and wraps `crossref_client` functions
4. [x] `FallbackProvider` implements `MetadataProvider` and chains other providers
5. [x] `build_metadata_provider(mailto, timeout)` composes the default chain (OpenAlex → Crossref)
6. [x] `ingest/fetch.py` accepts `MetadataProvider` via dependency injection
7. [x] Unit tests use mock providers (no network calls)
8. [x] Integration tests verify real API behavior (marked `requires_network`)
9. [x] `make ci` passes with no coverage regression
10. [x] Adding a new source requires only: new provider class + registration in `build_metadata_provider(...)`

---

## Migration Path

### Phase 1: Add Without Breaking (This Spec)

1. Add `MetadataProvider` protocol and provider implementations
2. Add `build_metadata_provider(mailto, timeout)` to `src/erdos/core/context.py`
3. Create new `fetch_reference_metadata()` function that uses injected provider
4. Keep existing `fetch_reference_entry()` working (backward compat)

### Phase 2: Migrate Callers (Follow-up)

1. Update `ingest` command/service to build the provider via `build_metadata_provider(mailto, timeout)`
2. Update `ingest/service.py` to use new function
3. Deprecate `MetadataSource` enum
4. Remove direct client construction from `fetch.py`

### Phase 3: Extend (Future Specs)

1. Add `SemanticScholarProvider` for citation context
2. Add `ExaProvider` for agentic research
3. Add `ZbMathProvider` for math-specific metadata

---

## References

- [ADR-001: Metadata Provider Orchestration](../adr/adr-001-metadata-provider-orchestration.md)
- [DEBT-038: MetadataProvider Abstraction Missing](../debt/debt-038-metadata-provider-abstraction.md)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Ports and Adapters Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Protocol classes in Python (PEP 544)](https://peps.python.org/pep-0544/)
- [master-qualifications.md Section 5](./master-qualifications.md#5-api-orchestration-strategy-rob-c-martin-principles)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-21 | Initial draft |
