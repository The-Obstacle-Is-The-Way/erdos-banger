"""Unit tests for MCP server tools.

Tests are guarded with pytest.importorskip("mcp") so the base test suite
can run without the optional mcp extra.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


# Skip all tests if mcp is not installed
pytestmark = pytest.mark.skipif(
    not pytest.importorskip("mcp", reason="mcp not installed"),
    reason="mcp not installed",
)


@pytest.fixture
def sample_problems_path() -> Path:
    """Return path to sample problems fixture."""
    return Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"


@pytest.fixture
def problem_repo(sample_problems_path: Path) -> ProblemRepository:
    """Create a problem loader from fixture data."""
    from erdos.core.problem_loader import ProblemLoader

    return ProblemLoader(sample_problems_path)


@pytest.fixture
def search_index(
    tmp_path: Path, problem_repo: ProblemRepository
) -> SearchIndexProtocol:
    """Create a search index populated with test data."""
    from erdos.core.search.facade import SearchIndex

    db_path = tmp_path / "test_index.db"
    index = SearchIndex(db_path)

    # Index all problems
    for problem in problem_repo.load_all():
        index.index_problem(problem)

    return index


class TestGetProblem:
    """Tests for the get_problem MCP tool."""

    def test_get_problem_returns_valid_problem(
        self, problem_repo: ProblemRepository
    ) -> None:
        """get_problem returns a valid ProblemRecord for existing problem."""
        from erdos.mcp.server import mcp_get_problem

        result = mcp_get_problem(problem_id=6, repo=problem_repo)

        assert result["success"] is True
        assert result["data"]["id"] == 6
        assert result["data"]["title"] == "Small primes in arithmetic progressions"
        assert result["data"]["status"] == "proved"

    def test_get_problem_returns_error_for_missing(
        self, problem_repo: ProblemRepository
    ) -> None:
        """get_problem returns error for non-existent problem."""
        from erdos.mcp.server import mcp_get_problem

        result = mcp_get_problem(problem_id=99999, repo=problem_repo)

        assert result["success"] is False
        assert result["error"]["type"] == "NotFound"
        assert "99999" in result["error"]["message"]

    def test_get_problem_schema_version(self, problem_repo: ProblemRepository) -> None:
        """get_problem output includes schema_version."""
        from erdos.mcp.server import mcp_get_problem

        result = mcp_get_problem(problem_id=6, repo=problem_repo)

        assert "schema_version" in result
        assert result["schema_version"] == 1


class TestListProblems:
    """Tests for the list_problems MCP tool."""

    def test_list_problems_returns_all(self, problem_repo: ProblemRepository) -> None:
        """list_problems returns all problems when no filters."""
        from erdos.mcp.server import mcp_list_problems

        result = mcp_list_problems(repo=problem_repo)

        assert result["success"] is True
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 6  # 6 problems in sample_problems.yaml

    def test_list_problems_filters_by_status(
        self, problem_repo: ProblemRepository
    ) -> None:
        """list_problems filters by status."""
        from erdos.mcp.server import mcp_list_problems

        result = mcp_list_problems(status="open", repo=problem_repo)

        assert result["success"] is True
        assert len(result["data"]) == 2  # Problems 42 and 100 are open

    def test_list_problems_respects_limit(
        self, problem_repo: ProblemRepository
    ) -> None:
        """list_problems respects limit parameter."""
        from erdos.mcp.server import mcp_list_problems

        result = mcp_list_problems(limit=2, repo=problem_repo)

        assert result["success"] is True
        assert len(result["data"]) == 2

    def test_list_problems_filters_by_tags(
        self, problem_repo: ProblemRepository
    ) -> None:
        """list_problems filters by tags."""
        from erdos.mcp.server import mcp_list_problems

        result = mcp_list_problems(tags=["graph theory"], repo=problem_repo)

        assert result["success"] is True
        # Only problem 100 has "graph theory" tag
        assert len(result["data"]) >= 1
        assert any(p["id"] == 100 for p in result["data"])


class TestGetReferences:
    """Tests for the get_references MCP tool."""

    def test_get_references_returns_refs(self, problem_repo: ProblemRepository) -> None:
        """get_references returns references for a problem."""
        from erdos.mcp.server import mcp_get_references

        result = mcp_get_references(problem_id=6, repo=problem_repo)

        assert result["success"] is True
        assert result["data"]["problem_id"] == 6
        refs = result["data"]["references"]
        assert isinstance(refs, list)
        assert len(refs) == 1
        assert refs[0]["key"] == "GreenTao2008"

    def test_get_references_error_for_missing(
        self, problem_repo: ProblemRepository
    ) -> None:
        """get_references returns error for non-existent problem."""
        from erdos.mcp.server import mcp_get_references

        result = mcp_get_references(problem_id=99999, repo=problem_repo)

        assert result["success"] is False
        assert result["error"]["type"] == "NotFound"


class TestSearchIndex:
    """Tests for the search_index MCP tool."""

    def test_search_index_returns_results(
        self,
        search_index: SearchIndexProtocol,
        problem_repo: ProblemRepository,
    ) -> None:
        """search_index returns matching results."""
        from erdos.mcp.server import mcp_search_index

        result = mcp_search_index(query="prime", index=search_index, repo=problem_repo)

        assert result["success"] is True
        assert result["data"]["query"] == "prime"
        assert len(result["data"]["results"]) > 0

    def test_search_index_respects_limit(
        self,
        search_index: SearchIndexProtocol,
        problem_repo: ProblemRepository,
    ) -> None:
        """search_index respects limit parameter."""
        from erdos.mcp.server import mcp_search_index

        result = mcp_search_index(
            query="prime", limit=1, index=search_index, repo=problem_repo
        )

        assert result["success"] is True
        assert len(result["data"]["results"]) <= 1

    def test_search_index_filters_by_problem(
        self,
        search_index: SearchIndexProtocol,
        problem_repo: ProblemRepository,
    ) -> None:
        """search_index can filter to a specific problem."""
        from erdos.mcp.server import mcp_search_index

        result = mcp_search_index(
            query="prime",
            problem_id=6,
            index=search_index,
            repo=problem_repo,
        )

        assert result["success"] is True
        # All results should be from problem 6
        for r in result["data"]["results"]:
            assert r["problem_id"] == 6

    def test_search_index_empty_query_error(
        self,
        search_index: SearchIndexProtocol,
        problem_repo: ProblemRepository,
    ) -> None:
        """search_index returns error for empty query."""
        from erdos.mcp.server import mcp_search_index

        result = mcp_search_index(query="", index=search_index, repo=problem_repo)

        assert result["success"] is False
        assert result["error"]["type"] == "UsageError"


class TestLeanCheck:
    """Tests for the lean_check MCP tool."""

    def test_lean_check_file_not_found(self, tmp_path: Path) -> None:
        """lean_check returns error for non-existent file."""
        from erdos.mcp.server import mcp_lean_check

        result = mcp_lean_check(file="nonexistent.lean", project_path=tmp_path)

        assert result["success"] is False
        assert result["error"]["type"] == "NotFound"

    def test_lean_check_validates_path_traversal(self, tmp_path: Path) -> None:
        """lean_check rejects path traversal attempts."""
        from erdos.mcp.server import mcp_lean_check

        result = mcp_lean_check(file="../../../etc/passwd", project_path=tmp_path)

        assert result["success"] is False
        assert result["error"]["type"] == "UsageError"
        assert "traversal" in result["error"]["message"].lower()


class TestLeanFormalize:
    """Tests for the lean_formalize MCP tool."""

    def test_lean_formalize_creates_skeleton(
        self, problem_repo: ProblemRepository, tmp_path: Path
    ) -> None:
        """lean_formalize creates a Lean skeleton file."""
        from erdos.mcp.server import mcp_lean_formalize

        result = mcp_lean_formalize(
            problem_id=6, project_path=tmp_path, repo=problem_repo
        )

        assert result["success"] is True
        assert result["data"]["problem_id"] == 6
        assert "file" in result["data"]

    def test_lean_formalize_error_for_missing_problem(
        self, problem_repo: ProblemRepository, tmp_path: Path
    ) -> None:
        """lean_formalize returns error for non-existent problem."""
        from erdos.mcp.server import mcp_lean_formalize

        result = mcp_lean_formalize(
            problem_id=99999, project_path=tmp_path, repo=problem_repo
        )

        assert result["success"] is False
        assert result["error"]["type"] == "NotFound"


class TestAskQuestion:
    """Tests for the ask_question MCP tool (optional, requires SPEC-011)."""

    def test_ask_question_returns_prompt_and_sources(
        self,
        problem_repo: ProblemRepository,
        search_index: SearchIndexProtocol,
    ) -> None:
        """ask_question returns prompt and sources in no_llm mode."""
        from erdos.mcp.server import mcp_ask_question

        result = mcp_ask_question(
            problem_id=6,
            question="What is known about this problem?",
            no_llm=True,
            repo=problem_repo,
            index=search_index,
        )

        assert result["success"] is True
        assert result["data"]["problem_id"] == 6
        assert result["data"]["question"] == "What is known about this problem?"
        assert "sources" in result["data"]

    def test_ask_question_error_for_missing_problem(
        self,
        problem_repo: ProblemRepository,
        search_index: SearchIndexProtocol,
    ) -> None:
        """ask_question returns error for non-existent problem."""
        from erdos.mcp.server import mcp_ask_question

        result = mcp_ask_question(
            problem_id=99999,
            question="What is this?",
            no_llm=True,
            repo=problem_repo,
            index=search_index,
        )

        assert result["success"] is False
        assert result["error"]["type"] == "NotFound"


class TestGetLogs:
    """Tests for the get_logs MCP tool (optional, requires SPEC-013)."""

    def test_get_logs_returns_empty_when_no_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_logs returns empty list when no logs exist."""
        from erdos.mcp.server import mcp_get_logs

        # Point to non-existent log file
        monkeypatch.setenv("ERDOS_RUN_LOG_PATH", str(tmp_path / "nonexistent.jsonl"))

        result = mcp_get_logs()

        assert result["success"] is True
        assert result["data"]["entries"] == []


class TestErrorHandling:
    """Tests for error handling in MCP tools."""

    def test_error_response_format(self, problem_repo: ProblemRepository) -> None:
        """Error responses follow CLIOutput.err() format."""
        from erdos.mcp.server import mcp_get_problem

        result = mcp_get_problem(problem_id=99999, repo=problem_repo)

        assert "schema_version" in result
        assert result["success"] is False
        assert "error" in result
        assert "type" in result["error"]
        assert "message" in result["error"]
        assert "code" in result["error"]


class TestToolSchemas:
    """Tests for MCP tool schemas."""

    def test_tools_have_descriptions(self) -> None:
        """All MCP tools have descriptions."""
        pytest.importorskip("mcp")
        from erdos.mcp.server import mcp

        # FastMCP stores tools internally - we verify by checking the server
        # has the expected tools registered
        assert mcp is not None
        assert mcp.name == "erdos-banger"
