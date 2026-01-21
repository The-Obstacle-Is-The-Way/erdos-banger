"""Search domain contract types.

These types define the public contracts for search operations.
Both the ports module and the search_index implementation import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol


if TYPE_CHECKING:
    from numpy.typing import NDArray

    from erdos.core.models import ChunkSource


class EmbeddingModelProtocol(Protocol):
    """Protocol for embedding models."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def encode(self, text: str) -> NDArray[Any]: ...

    def encode_batch(self, texts: list[str]) -> list[NDArray[Any]]: ...

    def to_blob(self, embedding: NDArray[Any]) -> bytes: ...

    def from_blob(self, blob: bytes) -> NDArray[Any]: ...


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    chunk_id: str
    text: str
    snippet: str  # Highlighted excerpt
    score: float  # BM25 score (higher = more relevant)
    source_type: ChunkSource
    problem_id: int | None
    reference_doi: str | None


@dataclass
class SemanticSearchResult:
    """A search result with semantic and/or hybrid scores."""

    chunk_id: str
    text: str
    snippet: str
    source_type: ChunkSource
    problem_id: int | None
    reference_doi: str | None
    # Scores
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    hybrid_score: float = field(default=0.0)
