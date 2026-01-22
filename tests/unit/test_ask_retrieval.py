"""Unit tests for ask retrieval logic."""

from unittest.mock import MagicMock

from erdos.core.ask import perform_retrieval, retrieve_sources
from erdos.core.models import ChunkSource, ProblemRecord, ProblemStatus
from erdos.core.search.facade import SearchIndex
from erdos.core.search.types import SearchResult


def test_retrieval_calls_search_index():
    """perform_retrieval must call SearchIndex.search with correct params."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "What is known?"
    limit = 5

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = [
        SearchResult(
            chunk_id="test",
            text="result",
            snippet="...",
            score=1.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        )
    ]

    results, _query = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=limit,
    )

    # Verify search was called with correct query and problem_id
    mock_index.search.assert_called_once()
    call_args = mock_index.search.call_args
    assert call_args.kwargs["limit"] == limit
    assert call_args.kwargs["problem_id"] == problem.id
    assert len(results) == 1
    assert results[0].chunk_id == "test"


def test_retrieval_constructs_query_from_problem_and_question():
    """Query should include problem title and question."""
    problem = ProblemRecord(
        id=6,
        title="Small primes",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "What partial results?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    _results, query = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=5,
    )

    # Verify query was constructed and search was called with problem_id filter
    call_args = mock_index.search.call_args
    assert query is not None
    # Query should include tokens from both the problem title and the question.
    assert '"small"' in query
    assert '"partial"' in query
    # Problem ID should be passed as a filter
    assert call_args.kwargs["problem_id"] == problem.id


def test_retrieval_returns_empty_when_no_results():
    """perform_retrieval must handle empty search results."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "Test?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    results, _query = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=5,
    )

    assert results == []


def test_retrieval_respects_limit():
    """perform_retrieval must pass limit to search index."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "Test?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    _results, _query = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=10,
    )

    call_args = mock_index.search.call_args
    assert call_args.kwargs["limit"] == 10


def test_retrieval_filters_by_problem_id():
    """perform_retrieval must filter to the specified problem."""
    problem = ProblemRecord(
        id=42,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "Test?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    _results, _query = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=5,
    )

    call_args = mock_index.search.call_args
    assert call_args.kwargs["problem_id"] == 42


def test_retrieve_sources_empty_index():
    """retrieve_sources returns fallback sources when index is empty."""
    problem = ProblemRecord(
        id=6,
        title="Test Problem",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.chunk_count.return_value = 0

    sources, used_fts, query = retrieve_sources(
        index=mock_index,
        problem=problem,
        question="Test?",
        limit=5,
    )

    # Should return fallback sources (statement + notes if present)
    assert len(sources) >= 1
    assert sources[0].chunk_id == f"problem_{problem.id}_statement"
    assert not used_fts
    assert query is None


def test_retrieve_sources_with_index_data():
    """retrieve_sources combines fallback and retrieved sources."""
    problem = ProblemRecord(
        id=6,
        title="Test Problem",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.chunk_count.return_value = 10
    mock_index.search.return_value = [
        SearchResult(
            chunk_id="retrieved_1",
            text="retrieved text",
            snippet="...",
            score=0.9,
            source_type=ChunkSource.REFERENCE_ABSTRACT,
            problem_id=6,
            reference_doi=None,
        )
    ]

    sources, used_fts, query = retrieve_sources(
        index=mock_index,
        problem=problem,
        question="Test?",
        limit=5,
    )

    # Should have both fallback (statement) and retrieved sources
    assert len(sources) >= 1
    chunk_ids = [s.chunk_id for s in sources]
    assert f"problem_{problem.id}_statement" in chunk_ids
    assert "retrieved_1" in chunk_ids
    assert used_fts
    assert query is not None


def test_retrieve_sources_deduplicates():
    """retrieve_sources removes duplicate chunk IDs."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )

    # Mock index returns a duplicate of the problem statement
    mock_index = MagicMock(spec=SearchIndex)
    mock_index.chunk_count.return_value = 10
    mock_index.search.return_value = [
        SearchResult(
            chunk_id=f"problem_{problem.id}_statement",
            text="Test statement",
            snippet="...",
            score=1.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        )
    ]

    sources, _used_fts, _query = retrieve_sources(
        index=mock_index,
        problem=problem,
        question="Test?",
        limit=5,
    )

    # Should only have one instance of the statement
    chunk_ids = [s.chunk_id for s in sources]
    assert chunk_ids.count(f"problem_{problem.id}_statement") == 1
