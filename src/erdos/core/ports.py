"""Core application ports (abstractions).

These Protocols define the interfaces that higher-level code (services/commands)
depends on, rather than concrete implementations like ProblemLoader/SearchIndex.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from collections.abc import Iterator

    from erdos.core.models import ChunkSource, ProblemRecord
    from erdos.core.search.types import (
        EmbeddingModelProtocol,
        SearchResult,
        SemanticSearchResult,
    )


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
