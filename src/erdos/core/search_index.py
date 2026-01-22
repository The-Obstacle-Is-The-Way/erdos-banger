"""SQLite FTS5 search index for erdos-banger.

BACKWARD COMPATIBILITY SHIM:
This module re-exports SearchIndex and related types from the refactored
search package (core/search/). The SearchIndex class has been refactored
from a monolithic implementation to a facade pattern with focused collaborators:

- core/search/db.py: Database connection and schema management
- core/search/indexer.py: Indexing operations (write path)
- core/search/bm25.py: BM25/FTS5 search
- core/search/embeddings_store.py: Embedding storage and semantic search
- core/search/hybrid.py: Hybrid BM25 + semantic search
- core/search/facade.py: SearchIndex facade (this is the actual class)

Import paths remain stable:
    from erdos.core.search_index import SearchIndex, SearchResult
"""

from __future__ import annotations

# Re-export everything from the new facade module
from erdos.core.search.db import SearchIndexError
from erdos.core.search.facade import SearchIndex
from erdos.core.search.types import (
    EmbeddingModelProtocol,
    SearchResult,
    SemanticSearchResult,
)


__all__ = [
    "EmbeddingModelProtocol",
    "SearchIndex",
    "SearchIndexError",
    "SearchResult",
    "SemanticSearchResult",
]
