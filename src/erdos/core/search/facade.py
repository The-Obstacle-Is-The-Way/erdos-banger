"""SearchIndex facade - thin coordinator delegating to focused collaborators.

This module provides the SearchIndex class as a backward-compatible facade
that composes the focused search modules (db, indexer, bm25, embeddings, hybrid).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from erdos.core.search.bm25 import BM25Search
from erdos.core.search.db import DatabaseManager, SearchIndexError
from erdos.core.search.embeddings_store import EmbeddingsStore
from erdos.core.search.hybrid import HybridSearch
from erdos.core.search.indexer import Indexer
from erdos.core.search.types import (
    EmbeddingModelProtocol,
    SearchResult,
    SemanticSearchResult,
)


if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from sqlite3 import Connection

    from erdos.core.models import ChunkSource, ProblemRecord, TextChunk


__all__ = [
    "EmbeddingModelProtocol",
    "SearchIndex",
    "SearchIndexError",
    "SearchResult",
    "SemanticSearchResult",
]


class SearchIndex:
    """SQLite FTS5 search index (facade).

    This class provides a unified interface for search operations,
    delegating to focused collaborators:
    - DatabaseManager: connection and schema
    - Indexer: write path (index_problem, index_chunk, clear)
    - BM25Search: full-text search
    - EmbeddingsStore: embedding storage and semantic search
    - HybridSearch: combined BM25 + semantic search

    Usage:
        index = SearchIndex.from_default()
        index.index_problem(problem)
        results = index.search("prime numbers", limit=10)
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path) -> None:
        """Initialize search index.

        Args:
            db_path: Path to SQLite database file
        """
        self._db = DatabaseManager(db_path)
        self._indexer = Indexer(self._db)
        self._bm25 = BM25Search(self._db)
        self._embeddings = EmbeddingsStore(self._db)
        self._hybrid = HybridSearch(self._db, self._bm25, self._embeddings)

    @classmethod
    def from_default(cls, *, index_path: Path | None = None) -> SearchIndex:
        """Create index using default path (index/erdos.sqlite).

        Args:
            index_path: Explicit path to use (skips env/default lookup).

        Returns:
            SearchIndex instance.
        """
        # 1. Explicit path from config (DIP-compliant)
        if index_path is not None:
            return cls(index_path)

        # 2. Environment variable (legacy fallback)
        env_path = os.environ.get("ERDOS_INDEX_PATH")
        if env_path:
            return cls(Path(env_path))

        # 3. Default path
        return cls(Path("index/erdos.sqlite"))

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database."""
        return self._db.db_path

    # =========================================================================
    # Indexing Operations (delegated to Indexer)
    # =========================================================================

    def index_problem(self, problem: ProblemRecord) -> None:
        """Index a problem's statement.

        Creates chunks for the problem statement and notes.

        Args:
            problem: The problem to index
        """
        self._indexer.index_problem(problem)

    def index_chunk(self, chunk: TextChunk) -> None:
        """Index a single text chunk.

        Args:
            chunk: The chunk to index
        """
        self._indexer.index_chunk(chunk)

    def clear(self) -> None:
        """Delete all indexed content."""
        self._indexer.clear()

    def problem_count(self) -> int:
        """Return number of indexed problems."""
        return self._indexer.problem_count()

    def chunk_count(self) -> int:
        """Return number of indexed chunks."""
        return self._indexer.chunk_count()

    # =========================================================================
    # BM25/FTS Search Operations (delegated to BM25Search)
    # =========================================================================

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]:
        """Search the index using BM25.

        Args:
            query: Search query (supports FTS5 syntax)
            limit: Maximum results to return
            problem_id: Optionally filter to a specific problem
            source_types: Optionally filter by source types

        Returns:
            List of SearchResult objects, sorted by relevance
        """
        return self._bm25.search(
            query, limit=limit, problem_id=problem_id, source_types=source_types
        )

    def rebuild_fts(self) -> None:
        """Rebuild the FTS index (use after direct SQL modifications)."""
        self._db.rebuild_fts()

    # =========================================================================
    # Stats (uses multiple collaborators)
    # =========================================================================

    def get_stats(self) -> dict[str, object]:
        """Get index statistics."""
        problems = self.problem_count()
        chunks = self.chunk_count()
        with self._db.connect() as conn:
            # Count by source type
            by_source: dict[str, int] = {}
            cursor = conn.execute(
                "SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type"
            )
            for row in cursor:
                by_source[row[0]] = row[1]

            # Embedding stats
            embedding_count = conn.execute(
                "SELECT COUNT(*) FROM chunk_embeddings"
            ).fetchone()[0]
            model, dim = self._embeddings.get_embedding_metadata()

            try:
                db_size_bytes = self._db.db_path.stat().st_size
            except FileNotFoundError:
                db_size_bytes = 0

            return {
                "problems": problems,
                "chunks": chunks,
                "chunks_by_source": by_source,
                "db_path": str(self._db.db_path),
                "db_size_bytes": db_size_bytes,
                "embeddings": embedding_count,
                "embedding_model": model,
                "embedding_dimension": dim,
            }

    # =========================================================================
    # Embedding Operations (delegated to EmbeddingsStore)
    # =========================================================================

    def set_embedding_metadata(self, model_name: str, dimension: int) -> None:
        """Store embedding model metadata in schema_meta table."""
        self._embeddings.set_embedding_metadata(model_name, dimension)

    def get_embedding_metadata(self) -> tuple[str | None, int | None]:
        """Get stored embedding model metadata.

        Returns:
            Tuple of (model_name, dimension), or (None, None) if not set.
        """
        return self._embeddings.get_embedding_metadata()

    def has_embeddings(self) -> bool:
        """Check if embeddings have been built."""
        return self._embeddings.has_embeddings()

    def build_embeddings(self, embedder: EmbeddingModelProtocol) -> int:
        """Build embeddings for all indexed chunks.

        Args:
            embedder: Embedding model instance.

        Returns:
            Number of chunks embedded.
        """
        return self._embeddings.build_embeddings(embedder)

    # =========================================================================
    # Semantic/Hybrid Search (delegated to EmbeddingsStore/HybridSearch)
    # =========================================================================

    def search_semantic(
        self,
        query: str,
        embedder: EmbeddingModelProtocol,
        *,
        limit: int = 10,
        problem_id: int | None = None,
    ) -> list[SemanticSearchResult]:
        """Search using semantic similarity.

        Args:
            query: Search query text.
            embedder: Embedding model to use.
            limit: Maximum results to return.
            problem_id: Optionally filter to specific problem.

        Returns:
            List of SemanticSearchResult sorted by semantic similarity.

        Raises:
            SearchIndexError: If embeddings haven't been built or model mismatch.
        """
        return self._embeddings.search_semantic(
            query, embedder, limit=limit, problem_id=problem_id
        )

    def search_hybrid(
        self,
        query: str,
        embedder: EmbeddingModelProtocol,
        *,
        limit: int = 10,
        alpha: float = 0.5,
        problem_id: int | None = None,
    ) -> list[SemanticSearchResult]:
        """Search using hybrid BM25 + semantic scoring.

        Args:
            query: Search query text.
            embedder: Embedding model to use.
            limit: Maximum results to return.
            alpha: Weight for semantic vs BM25 (0=BM25 only, 1=semantic only).
            problem_id: Optionally filter to specific problem.

        Returns:
            List of SemanticSearchResult sorted by hybrid score.

        Raises:
            SearchIndexError: If embeddings haven't been built or model mismatch.
        """
        return self._hybrid.search_hybrid(
            query, embedder, limit=limit, alpha=alpha, problem_id=problem_id
        )

    # =========================================================================
    # Internal access (for backward compatibility in tests)
    # =========================================================================

    def _connect(self) -> AbstractContextManager[Connection]:
        """Internal: access to database connection context manager.

        NOTE: This is for backward compatibility with existing tests.
        New code should not use this method.
        """
        return self._db.connect()
