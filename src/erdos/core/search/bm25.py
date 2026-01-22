"""BM25/FTS5 search operations.

This module handles FTS5 full-text search with BM25 ranking.
Separated from indexing and embedding operations per SRP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from erdos.core.models import ChunkSource
from erdos.core.search.types import SearchResult


if TYPE_CHECKING:
    from erdos.core.search.db import DatabaseManager


class BM25Search:
    """Handles BM25/FTS5 search operations (read path).

    Responsibilities:
    - Full-text search with FTS5
    - BM25 ranking and snippet generation
    - Filtering by problem ID and source type
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize BM25 search with database manager.

        Args:
            db: Database manager instance
        """
        self._db = db

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
        if not query.strip():
            return []

        # Build query with filters
        sql = """
            SELECT
                c.id,
                c.text,
                snippet(chunks_fts, 0, '<mark>', '</mark>', '...', 32) as snippet,
                bm25(chunks_fts) as score,
                c.source_type,
                c.problem_id,
                c.reference_doi
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c._rowid
            WHERE chunks_fts MATCH ?
        """
        params: list[str | int] = [query]

        if problem_id is not None:
            sql += " AND c.problem_id = ?"
            params.append(problem_id)

        if source_types:
            placeholders = ",".join("?" * len(source_types))
            sql += f" AND c.source_type IN ({placeholders})"
            params.extend(st.value for st in source_types)

        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        results = []
        with self._db.connect() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor:
                results.append(
                    SearchResult(
                        chunk_id=row["id"],
                        text=row["text"],
                        snippet=row["snippet"],
                        score=abs(row["score"]),  # BM25 returns negative scores
                        source_type=ChunkSource(row["source_type"]),
                        problem_id=row["problem_id"],
                        reference_doi=row["reference_doi"],
                    )
                )

        return results
