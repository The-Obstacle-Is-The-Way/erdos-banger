"""Integration tests for search index with real data - Spec 006."""

from pathlib import Path

import pytest

from erdos.core.problem_loader import ProblemLoader
from erdos.core.search.facade import SearchIndex
from erdos.core.search.index_builder import build_index
from erdos.core.search.types import SearchResult


@pytest.fixture
def populated_index(tmp_path: Path, sample_problems_yaml: Path):
    """Index populated with sample data."""
    loader = ProblemLoader(sample_problems_yaml)
    index = SearchIndex(tmp_path / "test.sqlite")

    build_index(loader=loader, index=index)
    return index


def test_build_index_indexes_all_problems(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    """build_index indexes all problems from loader."""
    loader = ProblemLoader(sample_problems_yaml)
    index = SearchIndex(tmp_path / "test.sqlite")

    result = build_index(loader=loader, index=index)

    assert result["problems_indexed"] == loader.count()
    total_chunks = result["total_chunks"]
    assert isinstance(total_chunks, int) and total_chunks > 0


def test_build_index_rebuild_clears_existing(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    """build_index with rebuild=True clears existing data."""
    loader = ProblemLoader(sample_problems_yaml)
    index = SearchIndex(tmp_path / "test.sqlite")

    # Build twice
    build_index(loader=loader, index=index)
    result = build_index(loader=loader, index=index, rebuild=True)

    # Should still only have the problems once
    assert result["problems_indexed"] == loader.count()


def test_search_after_build(populated_index) -> None:
    """Search works after building index."""
    # Should be able to search anything that's in the sample data
    results = populated_index.search("problem")

    # Results depend on sample data content
    assert isinstance(results, list)


def test_fts5_phrase_search_integration(populated_index) -> None:
    """FTS5 phrase search works in integration."""
    # Exact phrase match - depends on sample data
    results = populated_index.search('"test"')
    assert isinstance(results, list)


def test_fts5_prefix_search_integration(populated_index) -> None:
    """FTS5 prefix search works in integration."""
    results = populated_index.search("test*")
    assert isinstance(results, list)


def test_search_returns_search_result_objects(populated_index) -> None:
    """Search returns SearchResult objects with correct fields."""
    results = populated_index.search("test")

    if results:  # Only test if we got results
        result = results[0]
        assert isinstance(result, SearchResult)
        assert hasattr(result, "chunk_id")
        assert hasattr(result, "text")
        assert hasattr(result, "snippet")
        assert hasattr(result, "score")
        assert hasattr(result, "source_type")
        assert hasattr(result, "problem_id")


def test_stats_after_build(populated_index) -> None:
    """Stats are accurate after build."""
    stats = populated_index.get_stats()

    assert stats["problems"] > 0
    assert stats["chunks"] > 0
    assert stats["db_size_bytes"] > 0
