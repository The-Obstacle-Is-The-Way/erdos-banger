"""Unit tests for erdos search service (DEBT-017-D4, DEBT-043)."""

from __future__ import annotations

from unittest import mock

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search import (
    SearchOptions,
    build_search_index,
    search_fts,
    search_with_fallback,
)
from erdos.core.search_index import SearchIndexError


class TestSearchOptions:
    """Tests for SearchOptions dataclass."""

    def test_all_fields(self) -> None:
        """Should create options with all fields."""
        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=6,
            build_index=True,
        )
        assert options.query == "prime"
        assert options.limit == 10
        assert options.problem_id == 6
        assert options.build_index is True

    def test_none_problem_id(self) -> None:
        """Should handle None problem_id."""
        options = SearchOptions(
            query="test",
            limit=5,
            problem_id=None,
            build_index=False,
        )
        assert options.problem_id is None


class TestBuildSearchIndex:
    """Tests for build_search_index() service function."""

    @mock.patch("erdos.core.search.service.build_index")
    def test_successful_build(self, mock_build: mock.Mock) -> None:
        """Should return None on successful build."""
        mock_build.return_value = {"problems_indexed": 100}
        repo = mock.Mock()
        index = mock.Mock()

        result = build_search_index(repo=repo, index=index)

        assert result is None
        mock_build.assert_called_once_with(loader=repo, index=index, rebuild=True)

    @mock.patch("erdos.core.search.service.build_index")
    def test_loader_error(self, mock_build: mock.Mock) -> None:
        """Should return CLIOutput error on ProblemLoaderError."""
        mock_build.side_effect = ProblemLoaderError("Problems not found")
        repo = mock.Mock()
        index = mock.Mock()

        result = build_search_index(repo=repo, index=index)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "LoaderError"
        assert "Problems not found" in result.error["message"]
        assert result.error["code"] == ExitCode.ERROR

    @mock.patch("erdos.core.search.service.build_index")
    def test_index_error(self, mock_build: mock.Mock) -> None:
        """Should return CLIOutput error on SearchIndexError."""
        mock_build.side_effect = SearchIndexError("Index corrupted")
        repo = mock.Mock()
        index = mock.Mock()

        result = build_search_index(repo=repo, index=index)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "IndexError"
        assert "Index corrupted" in result.error["message"]
        assert result.error["code"] == ExitCode.ERROR


class TestSearchWithFallback:
    """Tests for search_with_fallback() service function."""

    @mock.patch("erdos.core.search.service.search_fts")
    def test_successful_fts_search(self, mock_fts: mock.Mock) -> None:
        """Should return FTS result when successful."""
        expected_result = CLIOutput.ok(
            "erdos search",
            {"query": "prime", "count": 1, "results": [], "use_fts": True},
        )
        mock_fts.return_value = expected_result

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        repo = mock.Mock()
        index = mock.Mock()
        result = search_with_fallback(options, index=index, repo=repo)

        assert result.success is True
        mock_fts.assert_called_once_with(
            "prime",
            index=index,
            repo=repo,
            limit=10,
            problem_id=None,
        )

    @mock.patch("erdos.core.search.service.search_basic")
    @mock.patch("erdos.core.search.service.search_fts")
    def test_fallback_to_basic_on_empty_index(
        self, mock_fts: mock.Mock, mock_basic: mock.Mock
    ) -> None:
        """Should fall back to basic search when index is empty (FTS returns None)."""
        # FTS returns None when index is empty
        mock_fts.return_value = None
        repo = mock.Mock()
        index = mock.Mock()
        expected_result = CLIOutput.ok(
            "erdos search",
            {"query": "prime", "count": 0, "results": [], "use_fts": False},
        )
        mock_basic.return_value = expected_result

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        result = search_with_fallback(options, index=index, repo=repo)

        assert result.success is True
        assert result.data is not None
        assert result.data.get("mode") == "basic"
        assert result.data.get("fallback_reason") == "index_empty"
        mock_basic.assert_called_once_with("prime", repo, 10, None)

    @mock.patch("erdos.core.search.service.search_basic")
    def test_index_unavailable_uses_basic(self, mock_basic: mock.Mock) -> None:
        """Should use basic search when index is unavailable."""
        mock_basic.return_value = CLIOutput.ok(
            "erdos search",
            {"query": "prime", "count": 0, "results": [], "use_fts": False},
        )
        repo = mock.Mock()

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        search_with_fallback(options, index=None, repo=repo)
        mock_basic.assert_called_once_with("prime", repo, 10, None)

    @mock.patch("erdos.core.search.service.search_fts")
    def test_other_fts_errors_not_fallback(self, mock_fts: mock.Mock) -> None:
        """Should not fall back for FTS errors (non-None results)."""
        mock_fts.return_value = CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message="Some other error",
            code=ExitCode.ERROR,
        )
        repo = mock.Mock()
        index = mock.Mock()

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        result = search_with_fallback(options, index=index, repo=repo)

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "IndexError"

    @mock.patch("erdos.core.search.service.search_fts")
    def test_passes_problem_id_filter(self, mock_fts: mock.Mock) -> None:
        """Should pass problem_id filter to FTS search."""
        mock_fts.return_value = CLIOutput.ok(
            "erdos search",
            {"query": "test", "count": 0, "results": [], "use_fts": True},
        )
        repo = mock.Mock()
        index = mock.Mock()

        options = SearchOptions(
            query="test",
            limit=5,
            problem_id=42,
            build_index=False,
        )
        search_with_fallback(options, index=index, repo=repo)

        mock_fts.assert_called_once_with(
            "test",
            index=index,
            repo=repo,
            limit=5,
            problem_id=42,
        )


class TestSearchFts:
    """Tests for search_fts function."""

    def test_empty_query_returns_usage_error(self) -> None:
        """Should return UsageError for empty query."""
        index = mock.Mock()
        result = search_fts("", index=index)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "UsageError"
        assert "empty" in result.error["message"].lower()
        assert result.error["code"] == ExitCode.USAGE_ERROR

    def test_whitespace_query_returns_usage_error(self) -> None:
        """Should return UsageError for whitespace-only query."""
        index = mock.Mock()
        result = search_fts("   ", index=index)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "UsageError"
        assert result.error["code"] == ExitCode.USAGE_ERROR

    def test_empty_index_returns_none(self) -> None:
        """Should return None when index is empty (signals fallback needed)."""
        index = mock.Mock()
        index.problem_count.return_value = 0
        result = search_fts("prime", index=index)

        assert result is None
        index.problem_count.assert_called_once()

    def test_populated_index_returns_results(self) -> None:
        """Should return CLIOutput with results when index has data."""
        index = mock.Mock()
        index.problem_count.return_value = 10
        index.search.return_value = []

        result = search_fts("prime", index=index)

        assert result is not None
        assert result.success is True
        assert result.data is not None
        assert result.data["use_fts"] is True
        assert result.data["query"] == "prime"
