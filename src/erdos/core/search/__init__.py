"""Search domain types, contracts, and service.

This package provides:
- types: Contract types (SearchResult, SemanticSearchResult, EmbeddingModelProtocol)
- service: Search orchestration (execute_search, search_fts, search_basic, etc.)

All public APIs are re-exported for backward compatibility.
"""

from erdos.core.search.service import (
    SearchMode,
    SearchOptions,
    build_embeddings,
    build_search_index,
    execute_search,
    get_embedding_model,
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
    "EmbeddingModelProtocol",
    "SearchMode",
    "SearchOptions",
    "SearchResult",
    "SemanticSearchResult",
    "build_embeddings",
    "build_search_index",
    "execute_search",
    "get_embedding_model",
    "search_basic",
    "search_fts",
    "search_hybrid",
    "search_semantic",
    "search_with_fallback",
]
