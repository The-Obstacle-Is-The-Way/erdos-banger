"""Integration tests for MCP server.

Tests verify the server starts and responds correctly.
Guarded with pytest.importorskip("mcp").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# Skip all tests if mcp is not installed
pytestmark = pytest.mark.skipif(
    not pytest.importorskip("mcp", reason="mcp not installed"),
    reason="mcp not installed",
)


@pytest.fixture
def sample_problems_path() -> Path:
    """Return path to sample problems fixture."""
    return Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"


class TestMCPServerHelp:
    """Tests for MCP server startup."""

    def test_server_module_importable(self) -> None:
        """The server module can be imported."""
        from erdos.mcp import server

        assert hasattr(server, "mcp")
        assert hasattr(server, "main")

    def test_mcp_instance_has_correct_name(self) -> None:
        """The MCP server instance has the correct name."""
        from erdos.mcp.server import mcp

        assert mcp.name == "erdos-banger"


class TestMCPToolFunctions:
    """Integration tests for MCP tool functions."""

    def test_get_problem_with_fixture_data(
        self, sample_problems_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_problem works with fixture data."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        from erdos.mcp.server import get_problem

        result = get_problem(problem_id=6)
        data = json.loads(result)

        assert data["success"] is True
        assert data["data"]["id"] == 6
        assert "title" in data["data"]

    def test_list_problems_with_fixture_data(
        self, sample_problems_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """list_problems works with fixture data."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        from erdos.mcp.server import list_problems

        result = list_problems()
        data = json.loads(result)

        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 6

    def test_list_problems_with_status_filter(
        self, sample_problems_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """list_problems filters by status."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        from erdos.mcp.server import list_problems

        result = list_problems(status="open")
        data = json.loads(result)

        assert data["success"] is True
        assert all(p["status"] == "open" for p in data["data"])

    def test_get_references_with_fixture_data(
        self, sample_problems_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_references works with fixture data."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        from erdos.mcp.server import get_references

        result = get_references(problem_id=6)
        data = json.loads(result)

        assert data["success"] is True
        assert data["data"]["problem_id"] == 6
        assert len(data["data"]["references"]) == 1

    def test_search_index_with_built_index(
        self,
        sample_problems_path: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """search_index works with a built index."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        # Build a search index
        from erdos.core.problem_loader import ProblemLoader
        from erdos.core.search.facade import SearchIndex

        loader = ProblemLoader(sample_problems_path)
        index_path = tmp_path / "test.db"
        index = SearchIndex(index_path)
        for problem in loader.load_all():
            index.index_problem(problem)

        # Patch to use this index
        monkeypatch.setenv("ERDOS_INDEX_PATH", str(index_path))

        from erdos.mcp.server import search_index

        result = search_index(query="prime")
        data = json.loads(result)

        assert data["success"] is True
        assert data["data"]["query"] == "prime"

    def test_lean_check_nonexistent_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """lean_check returns error for non-existent file."""
        from erdos.mcp.server import lean_check

        result = lean_check(file="nonexistent.lean")
        data = json.loads(result)

        assert data["success"] is False
        assert data["error"]["type"] == "NotFound"

    def test_lean_formalize_creates_file(
        self,
        sample_problems_path: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """lean_formalize creates a skeleton file."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        from erdos.core.problem_loader import ProblemLoader
        from erdos.mcp.server import mcp_lean_formalize

        # Create project structure
        project_path = tmp_path / "lean"
        project_path.mkdir()

        # Use the internal function with a custom project path
        repo = ProblemLoader(sample_problems_path)
        result = mcp_lean_formalize(problem_id=6, project_path=project_path, repo=repo)

        assert result["success"] is True
        assert result["data"]["problem_id"] == 6


class TestMCPToolReturnFormats:
    """Tests that MCP tools return properly formatted JSON strings."""

    def test_all_tools_return_json_strings(
        self, sample_problems_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All MCP tool functions return JSON strings."""
        monkeypatch.setenv("ERDOS_DATA_PATH", str(sample_problems_path))

        from erdos.mcp.server import get_problem, get_references, list_problems

        # Test each tool returns valid JSON
        for tool_result in [
            get_problem(problem_id=6),
            list_problems(),
            get_references(problem_id=6),
        ]:
            assert isinstance(tool_result, str)
            data = json.loads(tool_result)
            assert "success" in data
            assert "schema_version" in data
