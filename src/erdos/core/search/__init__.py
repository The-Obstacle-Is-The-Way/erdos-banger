"""Search domain types, contracts, and service.

This package provides:
- types: Contract types (SearchResult, SemanticSearchResult, EmbeddingModelProtocol)
- service: Search orchestration (execute_search, search_fts, search_basic, etc.)
- embeddings: Embedding model for semantic search
- index_builder: Index building utilities

All public APIs are re-exported for backward compatibility.
"""

from erdos.core.search.embeddings import (
    DEFAULT_DIMENSION,
    DEFAULT_MODEL_NAME,
    EMBEDDING_AVAILABLE,
    EmbeddingConfig,
    EmbeddingModel,
    EmbeddingNotAvailableError,
    cosine_similarity,
    embedding_from_blob,
    embedding_to_blob,
    get_embedding_model,
)
from erdos.core.search.index_builder import build_index
from erdos.core.search.service import (
    SearchMode,
    SearchOptions,
    build_embeddings,
    build_search_index,
    execute_search,
    search_basic,
    search_fts,
    search_hybrid,
    search_semantic,
    search_with_fallback,
)
from erdos.core.search.types import (
    EmbeddingModelProtocol,
    SearchResult,
    SemanticSearchResult,
)


__all__ = [
    "DEFAULT_DIMENSION",
    "DEFAULT_MODEL_NAME",
    "EMBEDDING_AVAILABLE",
    "EmbeddingConfig",
    "EmbeddingModel",
    "EmbeddingModelProtocol",
    "EmbeddingNotAvailableError",
    "SearchMode",
    "SearchOptions",
    "SearchResult",
    "SemanticSearchResult",
    "build_embeddings",
    "build_index",
    "build_search_index",
    "cosine_similarity",
    "embedding_from_blob",
    "embedding_to_blob",
    "execute_search",
    "get_embedding_model",
    "search_basic",
    "search_fts",
    "search_hybrid",
    "search_semantic",
    "search_with_fallback",
]
