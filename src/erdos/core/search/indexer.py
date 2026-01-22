"""Indexing operations for search index (write path).

This module handles indexing problems and chunks into the database.
Separated from search algorithms per SRP.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models import ChunkSource, TextChunk


if TYPE_CHECKING:
    import sqlite3

    from erdos.core.models import ProblemRecord
    from erdos.core.search.db import DatabaseManager


logger = logging.getLogger(__name__)


class Indexer:
    """Handles indexing operations (write path).

    Responsibilities:
    - Index problems (metadata + chunks)
    - Index individual chunks
    - Clear indexed content
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize indexer with database manager.

        Args:
            db: Database manager instance
        """
        self._db = db

    def index_problem(self, problem: ProblemRecord) -> None:
        """Index a problem's statement.

        Creates chunks for the problem statement and notes.

        Args:
            problem: The problem to index
        """
        now = datetime.now(UTC).isoformat()

        with self._db.connect() as conn:
            # Insert/update problem metadata
            conn.execute(
                """
                INSERT OR REPLACE INTO problems
                (id, title, statement, status, prize, tags, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem.id,
                    problem.title,
                    problem.statement,
                    problem.status.value,
                    problem.prize,
                    json.dumps(problem.tags),
                    now,
                ),
            )

            # Create chunk for statement
            chunk = TextChunk.from_problem(problem)
            self._insert_chunk(conn, chunk, now)

            # Create chunk for notes if present
            if problem.notes:
                notes_chunk = TextChunk(
                    id=f"problem_{problem.id}_notes",
                    text=problem.notes,
                    source=ChunkSource.PROBLEM_NOTES,
                    problem_id=problem.id,
                    preview=problem.notes[:PREVIEW_LENGTH]
                    if len(problem.notes) > PREVIEW_LENGTH
                    else problem.notes,
                )
                self._insert_chunk(conn, notes_chunk, now)

    def index_chunk(self, chunk: TextChunk) -> None:
        """Index a single text chunk.

        Args:
            chunk: The chunk to index
        """
        now = datetime.now(UTC).isoformat()
        with self._db.connect() as conn:
            self._insert_chunk(conn, chunk, now)

    def _insert_chunk(
        self, conn: sqlite3.Connection, chunk: TextChunk, timestamp: str
    ) -> None:
        """Insert a chunk into the database."""
        conn.execute(
            """
            INSERT OR REPLACE INTO chunks
            (id, text, source_type, problem_id, reference_doi, start_char, end_char, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.id,
                chunk.text,
                chunk.source.value,
                chunk.problem_id,
                chunk.reference_doi,
                chunk.start_char,
                chunk.end_char,
                timestamp,
            ),
        )

    def clear(self) -> None:
        """Delete all indexed content."""
        logger.info("Clearing search index")
        with self._db.connect() as conn:
            conn.execute("DELETE FROM chunk_embeddings")
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM problems")
            # Clear embedding metadata
            conn.execute(
                "DELETE FROM schema_meta WHERE key IN ('embedding_model', 'embedding_dimension')"
            )
            # Rebuild FTS index
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        logger.debug("Search index cleared")

    def problem_count(self) -> int:
        """Return number of indexed problems."""
        with self._db.connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM problems")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def chunk_count(self) -> int:
        """Return number of indexed chunks."""
        with self._db.connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            row = cursor.fetchone()
            return int(row[0]) if row else 0
