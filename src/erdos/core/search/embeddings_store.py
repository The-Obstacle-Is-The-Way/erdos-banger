"""Embedding storage and metadata management.

This module handles storing, retrieving, and managing embeddings in the database.
Separated from search algorithms per SRP.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from erdos.core.models import ChunkSource
from erdos.core.search.db import SearchIndexError
from erdos.core.search.types import EmbeddingModelProtocol, SemanticSearchResult


if TYPE_CHECKING:
    from erdos.core.search.db import DatabaseManager


logger = logging.getLogger(__name__)


class EmbeddingsStore:
    """Manages embedding storage and metadata.

    Responsibilities:
    - Store/retrieve embeddings
    - Manage embedding model metadata
    - Build embeddings for all chunks
    - Pure semantic search (cosine similarity)
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize embeddings store with database manager.

        Args:
            db: Database manager instance
        """
        self._db = db

    def set_embedding_metadata(self, model_name: str, dimension: int) -> None:
        """Store embedding model metadata in schema_meta table."""
        with self._db.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
                ("embedding_model", model_name),
            )
            conn.execute(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
                ("embedding_dimension", str(dimension)),
            )
        logger.debug("Set embedding metadata: model=%s, dim=%d", model_name, dimension)

    def get_embedding_metadata(self) -> tuple[str | None, int | None]:
        """Get stored embedding model metadata.

        Returns:
            Tuple of (model_name, dimension), or (None, None) if not set.
        """
        with self._db.connect() as conn:
            model_row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'embedding_model'"
            ).fetchone()
            dim_row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'embedding_dimension'"
            ).fetchone()

            model = model_row[0] if model_row else None
            dim = int(dim_row[0]) if dim_row else None
            return model, dim

    def has_embeddings(self) -> bool:
        """Check if embeddings have been built."""
        with self._db.connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunk_embeddings")
            count = cursor.fetchone()[0]
            return bool(count > 0)

    def build_embeddings(self, embedder: EmbeddingModelProtocol) -> int:
        """Build embeddings for all indexed chunks.

        Args:
            embedder: Embedding model instance.

        Returns:
            Number of chunks embedded.
        """
        logger.info("Building embeddings with model: %s", embedder.model_name)
        now = datetime.now(UTC).isoformat()

        with self._db.connect() as conn:
            # Clear existing embeddings
            conn.execute("DELETE FROM chunk_embeddings")

            # Get all chunks
            chunks = conn.execute("SELECT id, text FROM chunks").fetchall()
            if not chunks:
                logger.info("No chunks to embed")
                return 0

            # Generate embeddings in batches
            batch_size = 32
            count = 0
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                texts = [c[1] for c in batch]
                embeddings = embedder.encode_batch(texts)

                for (chunk_id, _), emb in zip(batch, embeddings, strict=True):
                    blob = embedder.to_blob(emb)
                    conn.execute(
                        """
                        INSERT INTO chunk_embeddings
                        (chunk_id, embedding, dimension, model, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (chunk_id, blob, embedder.dimension, embedder.model_name, now),
                    )
                    count += 1

                if count % 100 == 0:
                    logger.debug("Embedded %d/%d chunks", count, len(chunks))

        # Store metadata
        self.set_embedding_metadata(embedder.model_name, embedder.dimension)
        logger.info("Embedded %d chunks", count)
        return count

    def validate_embedder(self, embedder: EmbeddingModelProtocol) -> None:
        """Validate embedder matches stored metadata.

        Raises:
            SearchIndexError: If no embeddings or model mismatch.
        """
        if not self.has_embeddings():
            raise SearchIndexError(
                "No embeddings found. Run 'erdos search --build-embeddings' first."
            )

        stored_model, stored_dim = self.get_embedding_metadata()

        if stored_model != embedder.model_name:
            raise SearchIndexError(
                f"Model mismatch: index has '{stored_model}', "
                f"but embedder uses '{embedder.model_name}'. "
                "Rebuild embeddings with 'erdos search --build-embeddings'."
            )

        if stored_dim != embedder.dimension:
            raise SearchIndexError(
                f"Embedding dimension mismatch: index has {stored_dim}, "
                f"but embedder produces {embedder.dimension}. "
                "Rebuild embeddings with 'erdos search --build-embeddings'."
            )

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
        # Import cosine_similarity lazily to avoid import errors when
        # embeddings deps are not installed
        from erdos.core.embeddings import cosine_similarity  # noqa: PLC0415

        self.validate_embedder(embedder)

        # Encode query
        query_embedding = embedder.encode(query)

        # Get all embeddings and compute similarity
        results: list[tuple[float, SemanticSearchResult]] = []
        with self._db.connect() as conn:
            sql = """
                SELECT
                    e.chunk_id,
                    e.embedding,
                    c.text,
                    c.source_type,
                    c.problem_id,
                    c.reference_doi
                FROM chunk_embeddings e
                JOIN chunks c ON e.chunk_id = c.id
            """
            params: list[int] = []

            if problem_id is not None:
                sql += " WHERE c.problem_id = ?"
                params.append(problem_id)

            for row in conn.execute(sql, params):
                chunk_emb = embedder.from_blob(row["embedding"])
                raw_similarity = cosine_similarity(query_embedding, chunk_emb)
                # Normalize to 0..1 range
                semantic_score = (raw_similarity + 1) / 2

                # Create snippet (first 150 chars)
                text = row["text"]
                snippet = text[:150] + "..." if len(text) > 150 else text

                result = SemanticSearchResult(
                    chunk_id=row["chunk_id"],
                    text=text,
                    snippet=snippet,
                    source_type=ChunkSource(row["source_type"]),
                    problem_id=row["problem_id"],
                    reference_doi=row["reference_doi"],
                    semantic_score=semantic_score,
                    hybrid_score=semantic_score,  # For pure semantic, hybrid = semantic
                )
                results.append((semantic_score, result))

        # Sort by semantic score descending
        results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in results[:limit]]
