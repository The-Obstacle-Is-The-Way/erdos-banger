"""Unit tests for SearchIndex - Spec 006."""

from pathlib import Path

import pytest

from erdos.core.models import ChunkSource, ProblemRecord, ProblemStatus, TextChunk
from erdos.core.search.db import SearchIndexError
from erdos.core.search.facade import SearchIndex
from erdos.core.search.types import SearchResult


@pytest.fixture
def temp_index(tmp_path: Path):
    """Create a temporary search index."""
    return SearchIndex(tmp_path / "test.sqlite")


@pytest.fixture
def sample_problem() -> ProblemRecord:
    """A sample problem for indexing."""
    return ProblemRecord(
        id=6,
        title="Small primes in arithmetic progressions",
        statement="Let p_1 < p_2 < ... be the sequence of primes. Prove that for every k, there exist infinitely many arithmetic progressions of length k consisting entirely of primes.",
        status=ProblemStatus.PROVED,
        prize=100,
        tags=["number theory", "primes"],
    )


@pytest.fixture
def sample_problem_2() -> ProblemRecord:
    """Another sample problem for testing multiple indexing."""
    return ProblemRecord(
        id=42,
        title="Erdős-Straus conjecture",
        statement="For every integer n >= 2, the equation 4/n = 1/x + 1/y + 1/z has a solution with positive integers x, y, z.",
        status=ProblemStatus.OPEN,
        prize=500,
        tags=["number theory", "diophantine"],
        notes="This is an important open problem in number theory.",
    )


class TestSearchIndexBasics:
    """Test basic SearchIndex operations."""

    def test_creates_database(self, temp_index) -> None:
        """Index creates SQLite database file."""
        assert temp_index.db_path.exists()

    def test_empty_stats(self, temp_index) -> None:
        """New index has zero counts."""
        stats = temp_index.get_stats()
        assert stats["problems"] == 0
        assert stats["chunks"] == 0

    def test_db_path_property(self, tmp_path: Path) -> None:
        """db_path property returns correct path."""
        db_file = tmp_path / "custom.sqlite"
        index = SearchIndex(db_file)
        assert index.db_path == db_file


class TestSearchIndexFromDefault:
    """Test from_default() factory method."""

    def test_from_default_creates_index(self, tmp_path: Path, monkeypatch) -> None:
        """from_default() creates index at default location."""
        # Change to tmp_path so we don't create files in repo
        monkeypatch.chdir(tmp_path)

        index = SearchIndex.from_default()
        assert index.db_path.exists()
        assert "erdos.sqlite" in str(index.db_path)

    def test_from_default_respects_env_var(self, tmp_path: Path, monkeypatch) -> None:
        """from_default() uses ERDOS_INDEX_PATH if set."""
        custom_path = tmp_path / "custom" / "index.sqlite"
        monkeypatch.setenv("ERDOS_INDEX_PATH", str(custom_path))

        index = SearchIndex.from_default()
        assert index.db_path == custom_path


class TestSearchIndexIndexing:
    """Test indexing operations."""

    def test_index_problem(self, temp_index, sample_problem: ProblemRecord) -> None:
        """Indexing a problem creates chunks."""
        temp_index.index_problem(sample_problem)

        assert temp_index.problem_count() == 1
        assert temp_index.chunk_count() >= 1

    def test_index_is_idempotent(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """Indexing same problem twice doesn't duplicate."""
        temp_index.index_problem(sample_problem)
        temp_index.index_problem(sample_problem)

        assert temp_index.problem_count() == 1

    def test_index_multiple_problems(
        self, temp_index, sample_problem: ProblemRecord, sample_problem_2: ProblemRecord
    ) -> None:
        """Can index multiple problems."""
        temp_index.index_problem(sample_problem)
        temp_index.index_problem(sample_problem_2)

        assert temp_index.problem_count() == 2
        # sample_problem_2 has notes, so should have 2 chunks
        assert temp_index.chunk_count() >= 3

    def test_index_chunk_directly(self, temp_index) -> None:
        """Can index a TextChunk directly."""
        chunk = TextChunk(
            id="test_chunk_1",
            text="This is a test chunk about prime numbers and arithmetic.",
            source=ChunkSource.PROBLEM_STATEMENT,
            problem_id=999,
        )
        temp_index.index_chunk(chunk)

        assert temp_index.chunk_count() == 1


class TestSearchIndexSearch:
    """Test search operations."""

    def test_search_finds_indexed_content(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """Search returns results for matching query."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes arithmetic progression")

        assert len(results) > 0
        assert results[0].problem_id == 6

    def test_search_returns_empty_for_no_match(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """Search returns empty list for non-matching query."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("quantum mechanics")

        assert len(results) == 0

    def test_search_respects_limit(
        self, temp_index, sample_problem: ProblemRecord, sample_problem_2: ProblemRecord
    ) -> None:
        """Search respects limit parameter."""
        temp_index.index_problem(sample_problem)
        temp_index.index_problem(sample_problem_2)

        results = temp_index.search("integer", limit=1)

        assert len(results) <= 1

    def test_search_with_problem_filter(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """Search can filter by problem ID."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes", problem_id=6)
        assert len(results) > 0

        results = temp_index.search("primes", problem_id=999)
        assert len(results) == 0

    def test_search_with_source_type_filter(
        self, temp_index, sample_problem_2: ProblemRecord
    ) -> None:
        """Search can filter by source type."""
        temp_index.index_problem(sample_problem_2)  # Has notes

        # Search only in problem notes
        results = temp_index.search(
            "important", source_types=[ChunkSource.PROBLEM_NOTES]
        )
        assert len(results) > 0

        # Search only in statements (should not find "important")
        results = temp_index.search(
            "important", source_types=[ChunkSource.PROBLEM_STATEMENT]
        )
        assert len(results) == 0

    def test_search_returns_snippets(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """Search results include highlighted snippets."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes")

        assert results[0].snippet is not None
        assert len(results[0].snippet) > 0

    def test_search_empty_query(self, temp_index) -> None:
        """Empty query returns empty results."""
        results = temp_index.search("")
        assert results == []

        results = temp_index.search("   ")
        assert results == []

    def test_search_results_have_scores(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """Search results include BM25 scores."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes")

        assert len(results) > 0
        assert results[0].score > 0  # BM25 score should be positive


class TestSearchIndexClear:
    """Test clear operations."""

    def test_clear_removes_all(self, temp_index, sample_problem: ProblemRecord) -> None:
        """clear() removes all indexed content."""
        temp_index.index_problem(sample_problem)
        temp_index.clear()

        assert temp_index.problem_count() == 0
        assert temp_index.chunk_count() == 0


class TestSearchIndexRebuild:
    """Test FTS rebuild operations."""

    def test_rebuild_fts(self, temp_index, sample_problem: ProblemRecord) -> None:
        """rebuild_fts() doesn't error."""
        temp_index.index_problem(sample_problem)
        # Should not raise
        temp_index.rebuild_fts()


class TestSearchIndexStats:
    """Test stats operations."""

    def test_get_stats_structure(
        self, temp_index, sample_problem: ProblemRecord
    ) -> None:
        """get_stats() returns expected structure."""
        temp_index.index_problem(sample_problem)

        stats = temp_index.get_stats()

        assert "problems" in stats
        assert "chunks" in stats
        assert "chunks_by_source" in stats
        assert "db_path" in stats
        assert "db_size_bytes" in stats

    def test_get_stats_counts_by_source(
        self, temp_index, sample_problem_2: ProblemRecord
    ) -> None:
        """get_stats() counts chunks by source type."""
        temp_index.index_problem(sample_problem_2)  # Has statement + notes

        stats = temp_index.get_stats()

        assert "problem_statement" in stats["chunks_by_source"]


class TestSearchResultDataclass:
    """Test SearchResult dataclass."""

    def test_search_result_fields(self) -> None:
        """SearchResult has expected fields."""
        result = SearchResult(
            chunk_id="test_1",
            text="Some text about primes",
            snippet="...text about <mark>primes</mark>...",
            score=1.5,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        )

        assert result.chunk_id == "test_1"
        assert result.text == "Some text about primes"
        assert result.snippet == "...text about <mark>primes</mark>..."
        assert result.score == 1.5
        assert result.source_type == ChunkSource.PROBLEM_STATEMENT
        assert result.problem_id == 6
        assert result.reference_doi is None


class TestSearchIndexError:
    """Test SearchIndexError exception."""

    def test_search_index_error_exists(self) -> None:
        """SearchIndexError can be raised."""
        with pytest.raises(SearchIndexError):
            raise SearchIndexError("Test error")


class TestFTS5Queries:
    """Test FTS5 query syntax support."""

    def test_phrase_search(self, temp_index, sample_problem: ProblemRecord) -> None:
        """FTS5 phrase search with quotes works."""
        temp_index.index_problem(sample_problem)

        # Phrase match
        results = temp_index.search('"arithmetic progressions"')
        assert len(results) > 0

    def test_prefix_search(self, temp_index, sample_problem: ProblemRecord) -> None:
        """FTS5 prefix search with * works."""
        temp_index.index_problem(sample_problem)

        # Prefix match (prim* matches prime, primes)
        results = temp_index.search("prim*")
        assert len(results) > 0

    def test_or_search(
        self, temp_index, sample_problem: ProblemRecord, sample_problem_2: ProblemRecord
    ) -> None:
        """FTS5 OR search works."""
        temp_index.index_problem(sample_problem)
        temp_index.index_problem(sample_problem_2)

        # OR query - use words from both statements (primes from sample_problem,
        # integer from sample_problem_2)
        results = temp_index.search("primes OR integer")
        assert len(results) >= 2  # Should find both problems
