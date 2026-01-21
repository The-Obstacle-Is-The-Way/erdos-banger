"""SQLite FTS5 search index for erdos-banger."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models import ChunkSource, ProblemRecord, TextChunk

# Import contract types from search.types and re-export for backward compatibility
from erdos.core.search.types import (
    EmbeddingModelProtocol,
    SearchResult,
    SemanticSearchResult,
)


if TYPE_CHECKING:
    from collections.abc import Iterator


logger = logging.getLogger(__name__)

# Re-export for backward compatibility: `from erdos.core.search_index import SearchResult`
__all__ = [
    "EmbeddingModelProtocol",
    "SearchIndex",
    "SearchIndexError",
    "SearchResult",
    "SemanticSearchResult",
]


class SearchIndexError(Exception):
    """Raised when index operations fail."""

    pass


class SearchIndex:
    """
    SQLite FTS5 search index.

    Usage:
        index = SearchIndex.from_default()
        index.index_problem(problem)
        results = index.search("prime numbers", limit=10)
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path) -> None:
        """
        Initialize search index.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Initializing search index at %s", db_path)
        self._ensure_schema()

    @classmethod
    def from_default(cls) -> SearchIndex:
        """Create index using default path (index/erdos.sqlite)."""
        # Check environment variable
        env_path = os.environ.get("ERDOS_INDEX_PATH")
        if env_path:
            return cls(Path(env_path))

        # Default path
        default_path = Path("index/erdos.sqlite")
        default_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(default_path)

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database."""
        return self._db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_sql = """
        -- Problem metadata
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            statement TEXT NOT NULL,
            status TEXT NOT NULL,
            prize INTEGER DEFAULT 0,
            tags TEXT,
            indexed_at TEXT NOT NULL
        );

        -- Text chunks (explicit _rowid for FTS5 external content sync)
        CREATE TABLE IF NOT EXISTS chunks (
            _rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT UNIQUE NOT NULL,
            text TEXT NOT NULL,
            source_type TEXT NOT NULL,
            problem_id INTEGER,
            reference_doi TEXT,
            start_char INTEGER,
            end_char INTEGER,
            indexed_at TEXT NOT NULL
        );

        -- FTS5 virtual table
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            content='chunks',
            content_rowid='_rowid',
            tokenize='porter unicode61'
        );

        -- Sync triggers (use _rowid)
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text) VALUES (new._rowid, new.text);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old._rowid, old.text);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old._rowid, old.text);
            INSERT INTO chunks_fts(rowid, text) VALUES (new._rowid, new.text);
        END;

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_chunks_problem_id ON chunks(problem_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_source_type ON chunks(source_type);

        -- Schema version
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', '1');

        -- Chunk embeddings (SPEC-014: Vector Embeddings)
        CREATE TABLE IF NOT EXISTS chunk_embeddings (
            chunk_id TEXT PRIMARY KEY REFERENCES chunks(id),
            embedding BLOB NOT NULL,
            dimension INTEGER NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """

        with self._connect() as conn:
            try:
                conn.executescript(schema_sql)
            except sqlite3.OperationalError as e:
                # Some Python builds link against SQLite without FTS5 enabled.
                # Fail fast with a clear message instead of a cryptic SQL error.
                if "fts5" in str(e).lower():
                    raise SearchIndexError(
                        "SQLite FTS5 is not available in this environment "
                        "(sqlite3 compiled without FTS5). "
                        "Use a Python/SQLite build with FTS5 enabled."
                    ) from e
                raise

    def index_problem(self, problem: ProblemRecord) -> None:
        """
        Index a problem's statement.

        Creates chunks for the problem statement and notes.

        Args:
            problem: The problem to index
        """
        now = datetime.now(UTC).isoformat()

        with self._connect() as conn:
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
        """
        Index a single text chunk.

        Args:
            chunk: The chunk to index
        """
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
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

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]:
        """
        Search the index using BM25.

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
        with self._connect() as conn:
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

    def problem_count(self) -> int:
        """Return number of indexed problems."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM problems")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def chunk_count(self) -> int:
        """Return number of indexed chunks."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        """Delete all indexed content."""
        logger.info("Clearing search index")
        with self._connect() as conn:
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

    def rebuild_fts(self) -> None:
        """Rebuild the FTS index (use after direct SQL modifications)."""
        with self._connect() as conn:
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")

    def get_stats(self) -> dict[str, object]:
        """Get index statistics."""
        with self._connect() as conn:
            problems = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

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
            model, dim = self.get_embedding_metadata()

            return {
                "problems": problems,
                "chunks": chunks,
                "chunks_by_source": by_source,
                "db_path": str(self._db_path),
                "db_size_bytes": self._db_path.stat().st_size
                if self._db_path.exists()
                else 0,
                "embeddings": embedding_count,
                "embedding_model": model,
                "embedding_dimension": dim,
            }

    # =========================================================================
    # Embedding Methods (SPEC-014)
    # =========================================================================

    def set_embedding_metadata(self, model_name: str, dimension: int) -> None:
        """Store embedding model metadata in schema_meta table."""
        with self._connect() as conn:
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
        with self._connect() as conn:
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
        with self._connect() as conn:
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

        with self._connect() as conn:
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

    def _validate_embedder(self, embedder: EmbeddingModelProtocol) -> None:
        """Validate embedder matches stored metadata."""
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

        self._validate_embedder(embedder)

        # Encode query
        query_embedding = embedder.encode(query)

        # Get all embeddings and compute similarity
        results: list[tuple[float, SemanticSearchResult]] = []
        with self._connect() as conn:
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
        from erdos.core.embeddings import cosine_similarity  # noqa: PLC0415

        self._validate_embedder(embedder)

        # Get BM25 candidates (expanded set for re-ranking)
        bm25_results = self.search(query, limit=limit * 2, problem_id=problem_id)

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
        with self._connect() as conn:
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
