"""Database connection and schema management for search index.

This module handles SQLite connection management and schema creation/migration.
Separated from search algorithms per SRP.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path  # noqa: TC003 - Used at runtime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator


logger = logging.getLogger(__name__)


class SearchIndexError(Exception):
    """Raised when index operations fail."""


SCHEMA_VERSION = 1

SCHEMA_SQL = """
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


class DatabaseManager:
    """Manages SQLite database connections and schema.

    Responsibilities:
    - Create/ensure database file exists
    - Ensure schema is created
    - Provide connection context manager
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Initializing database at %s", db_path)
        self._ensure_schema()

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database."""
        return self._db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
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
        with self.connect() as conn:
            try:
                conn.executescript(SCHEMA_SQL)
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

    def rebuild_fts(self) -> None:
        """Rebuild the FTS index (use after direct SQL modifications)."""
        with self.connect() as conn:
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
