"""Hybrid BM25 + semantic search.

This module combines BM25 and semantic search with configurable weighting.
Separated from pure BM25 and pure semantic search per SRP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from erdos.core.search.types import EmbeddingModelProtocol, SemanticSearchResult


if TYPE_CHECKING:
    from erdos.core.search.bm25 import BM25Search
    from erdos.core.search.db import DatabaseManager
    from erdos.core.search.embeddings_store import EmbeddingsStore


class HybridSearch:
    """Combines BM25 and semantic search with configurable weighting.

    Responsibilities:
    - Hybrid BM25 + semantic scoring
    - Score normalization and combination
    """

    def __init__(
        self,
        db: DatabaseManager,
        bm25: BM25Search,
        embeddings: EmbeddingsStore,
    ) -> None:
        """Initialize hybrid search with collaborators.

        Args:
            db: Database manager instance
            bm25: BM25 search instance for keyword matching
            embeddings: Embeddings store for semantic similarity
        """
        self._db = db
        self._bm25 = bm25
        self._embeddings = embeddings

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
        from erdos.core.search.embeddings import cosine_similarity  # noqa: PLC0415

        # Validate alpha bounds
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be between 0 and 1, got {alpha}")

        self._embeddings.validate_embedder(embedder)

        # Get BM25 candidates (expanded set for re-ranking)
        bm25_results = self._bm25.search(query, limit=limit * 2, problem_id=problem_id)

        if not bm25_results:
            return []

        # Normalize BM25 scores to 0..1
        max_bm25 = max(r.score for r in bm25_results)
        min_bm25 = min(r.score for r in bm25_results)
        bm25_range = max_bm25 - min_bm25
        if bm25_range == 0:
            bm25_range = 1.0  # Avoid division by zero

        # Encode query
        query_embedding = embedder.encode(query)

        # Compute hybrid scores
        results: list[tuple[float, SemanticSearchResult]] = []
        with self._db.connect() as conn:
            for bm25_result in bm25_results:
                # Get embedding for this chunk
                row = conn.execute(
                    "SELECT embedding FROM chunk_embeddings WHERE chunk_id = ?",
                    (bm25_result.chunk_id,),
                ).fetchone()

                if row is None:
                    # No embedding for this chunk, skip
                    continue

                chunk_emb = embedder.from_blob(row["embedding"])
                raw_similarity = cosine_similarity(query_embedding, chunk_emb)
                semantic_score = (raw_similarity + 1) / 2

                # Normalize BM25 score
                bm25_normalized = (bm25_result.score - min_bm25) / bm25_range

                # Compute hybrid score
                hybrid_score = (1 - alpha) * bm25_normalized + alpha * semantic_score

                result = SemanticSearchResult(
                    chunk_id=bm25_result.chunk_id,
                    text=bm25_result.text,
                    snippet=bm25_result.snippet,
                    source_type=bm25_result.source_type,
                    problem_id=bm25_result.problem_id,
                    reference_doi=bm25_result.reference_doi,
                    bm25_score=bm25_result.score,
                    semantic_score=semantic_score,
                    hybrid_score=hybrid_score,
                )
                results.append((hybrid_score, result))

        # Sort by hybrid score descending
        results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in results[:limit]]
