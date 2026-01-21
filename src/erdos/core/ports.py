"""Core application ports (abstractions).

These Protocols define the interfaces that higher-level code (services/commands)
depends on, rather than concrete implementations like ProblemLoader/SearchIndex.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from collections.abc import Iterator

    from erdos.core.models import ChunkSource, ProblemRecord, ReferenceRecord
    from erdos.core.search.types import (
        EmbeddingModelProtocol,
        SearchResult,
        SemanticSearchResult,
    )


class MetadataProvider(Protocol):
    """Port for academic metadata sources (SPEC-022).

    High-level ingest code depends on this abstraction, not concrete clients.
    Implementations wrap existing clients (OpenAlexClient, crossref_client, etc.).
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name for logging/debugging."""
        ...

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work metadata by DOI.

        Returns:
            ReferenceRecord if found, None if not found.

        Raises:
            requests.RequestException: On network/API errors (non-404).
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
            requests.RequestException: On network/API errors (non-404).
            ValueError: On invalid arXiv identifiers or irrecoverable parse errors.
        """
        ...

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract.

        Returns:
            List of matching ReferenceRecords, possibly empty.
        """
        ...


class ProblemRepository(Protocol):
    """Abstract interface for accessing Erdős problems."""

    def get_by_id(self, problem_id: int) -> ProblemRecord | None: ...

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]: ...

    def iter_problems(self) -> Iterator[ProblemRecord]: ...


class SearchIndexProtocol(Protocol):
    """Abstract interface for search operations."""

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]: ...

    def index_problem(self, problem: ProblemRecord) -> None: ...

    def problem_count(self) -> int: ...

    def chunk_count(self) -> int: ...

    def clear(self) -> None: ...

    def get_stats(self) -> dict[str, object]: ...

    # SPEC-014: Embedding methods
    def has_embeddings(self) -> bool: ...

    def get_embedding_metadata(self) -> tuple[str | None, int | None]: ...

    def set_embedding_metadata(self, model_name: str, dimension: int) -> None: ...

    def build_embeddings(self, embedder: EmbeddingModelProtocol) -> int: ...

    def search_semantic(
        self,
        query: str,
        embedder: EmbeddingModelProtocol,
        *,
        limit: int = 10,
        problem_id: int | None = None,
    ) -> list[SemanticSearchResult]: ...

    def search_hybrid(
        self,
        query: str,
        embedder: EmbeddingModelProtocol,
        *,
        limit: int = 10,
        alpha: float = 0.5,
        problem_id: int | None = None,
    ) -> list[SemanticSearchResult]: ...
