"""Unit tests for ask_question helper functions."""

import subprocess
from unittest.mock import MagicMock, patch

from erdos.core.ask import (
    _build_response_data,
    _ensure_index_ready,
    _load_problem,
)
from erdos.core.ask.llm import execute_llm_if_enabled
from erdos.core.exit_codes import ExitCode
from erdos.core.models import ChunkSource, CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search.db import SearchIndexError
from erdos.core.search.types import SearchResult


def test_ensure_index_ready_no_build():
    """_ensure_index_ready returns provided index when no build requested."""

    mock_repo = MagicMock()
    mock_index = MagicMock()

    with patch("erdos.core.ask.service.build_index") as mock_build_index:
        result = _ensure_index_ready(
            loader=mock_repo,
            index=mock_index,
            build_index_flag=False,
        )

        assert result == mock_index
        mock_build_index.assert_not_called()


def test_ensure_index_ready_with_build():
    """_ensure_index_ready builds index when requested."""
    mock_repo = MagicMock()
    mock_index = MagicMock()

    with patch("erdos.core.ask.service.build_index") as mock_build_index:
        result = _ensure_index_ready(
            loader=mock_repo,
            index=mock_index,
            build_index_flag=True,
        )

        assert result == mock_index
        mock_build_index.assert_called_once_with(
            loader=mock_repo, index=mock_index, rebuild=True
        )


def test_ensure_index_ready_build_error():
    """_ensure_index_ready returns CLIOutput error if build fails with SearchIndexError."""
    mock_repo = MagicMock()
    mock_index = MagicMock()

    with patch("erdos.core.ask.service.build_index") as mock_build_index:
        mock_build_index.side_effect = SearchIndexError("Index build failed")

        result = _ensure_index_ready(
            loader=mock_repo,
            index=mock_index,
            build_index_flag=True,
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "Index build failed" in result.error["message"]


def test_ensure_index_ready_loader_error():
    """_ensure_index_ready returns CLIOutput error if build fails with ProblemLoaderError."""
    mock_repo = MagicMock()
    mock_index = MagicMock()

    with patch("erdos.core.ask.service.build_index") as mock_build_index:
        mock_build_index.side_effect = ProblemLoaderError("Problems not found")

        result = _ensure_index_ready(
            loader=mock_repo,
            index=mock_index,
            build_index_flag=True,
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "Problems not found" in result.error["message"]


def testexecute_llm_if_enabled_disabled():
    """execute_llm_if_enabled skips LLM when disabled."""

    result = execute_llm_if_enabled(
        prompt="Test prompt",
        enable_llm=False,
        llm_command=None,
    )

    assert isinstance(result, dict)
    assert result["answer"] is None
    assert result["llm_exit_code"] is None
    assert result["llm_enabled"] is False
    assert result["llm_command"] is None


def testexecute_llm_if_enabled_no_command():
    """execute_llm_if_enabled skips LLM when no command available."""

    result = execute_llm_if_enabled(
        prompt="Test prompt",
        enable_llm=True,
        llm_command=None,
    )

    assert isinstance(result, dict)
    assert result["answer"] is None
    assert result["llm_exit_code"] is None
    assert result["llm_enabled"] is False
    assert result["llm_command"] is None


def testexecute_llm_if_enabled_success():
    """execute_llm_if_enabled executes LLM successfully."""

    with patch("erdos.core.ask.llm.execute_llm") as mock_execute_llm:
        mock_execute_llm.return_value = ("Answer text", 0)

        result = execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, dict)
        assert result["answer"] == "Answer text"
        assert result["llm_exit_code"] == 0
        assert result["llm_enabled"] is True
        assert result["llm_command"] == "echo"


def testexecute_llm_if_enabled_nonzero_exit():
    """execute_llm_if_enabled returns error on nonzero exit code."""

    with patch("erdos.core.ask.llm.execute_llm") as mock_execute_llm:
        mock_execute_llm.return_value = ("Error output", 1)

        result = execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "exited with code 1" in result.error["message"]


def testexecute_llm_if_enabled_command_not_found():
    """execute_llm_if_enabled returns error when command not found."""

    with patch("erdos.core.ask.llm.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = FileNotFoundError()

        result = execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="nonexistent",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "not found" in result.error["message"]


def testexecute_llm_if_enabled_os_error():
    """execute_llm_if_enabled returns error on OS error."""

    with patch("erdos.core.ask.llm.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = OSError("Permission denied")

        result = execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "error" in result.error["message"].lower()


def testexecute_llm_if_enabled_value_error():
    """execute_llm_if_enabled returns error on ValueError (e.g., invalid command syntax)."""

    with patch("erdos.core.ask.llm.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = ValueError("No closing quotation")

        result = execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo 'unclosed",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "syntax" in result.error["message"].lower()


def testexecute_llm_if_enabled_timeout():
    """execute_llm_if_enabled returns error on timeout."""
    with patch("erdos.core.ask.llm.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = subprocess.TimeoutExpired(
            cmd="slow-llm", timeout=300
        )

        result = execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="slow-llm",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "timed out" in result.error["message"].lower()
        assert result.error["type"] == "TIMEOUT"


# Tests for _load_problem


def test_load_problem_success():
    """_load_problem returns problem when successful."""
    mock_problem = MagicMock(spec=ProblemRecord)
    mock_problem.id = 6
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = mock_problem

    result = _load_problem(6, repo=mock_repo)

    assert result == mock_problem
    mock_repo.get_by_id.assert_called_once_with(6)


def test_load_problem_loader_error():
    """_load_problem returns error when loader fails."""
    mock_repo = MagicMock()
    mock_repo.get_by_id.side_effect = ProblemLoaderError("Problems not found")

    result = _load_problem(6, repo=mock_repo)

    assert isinstance(result, CLIOutput)
    assert not result.success
    assert result.error is not None
    assert result.error["type"] == "LoaderError"
    assert "Problems not found" in result.error["message"]
    assert result.error["code"] == ExitCode.ERROR


def test_load_problem_not_found():
    """_load_problem returns error when problem not found."""
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = None

    result = _load_problem(999, repo=mock_repo)

    assert isinstance(result, CLIOutput)
    assert not result.success
    assert result.error is not None
    assert result.error["type"] == "NotFound"
    assert "999" in result.error["message"]
    assert result.error["code"] == ExitCode.NOT_FOUND


def test_load_problem_get_by_id_error():
    """_load_problem returns error when get_by_id raises exception."""
    mock_repo = MagicMock()
    mock_repo.get_by_id.side_effect = ProblemLoaderError("Database error")

    result = _load_problem(6, repo=mock_repo)

    assert isinstance(result, CLIOutput)
    assert not result.success
    assert result.error is not None
    assert result.error["type"] == "LoaderError"
    assert "Database error" in result.error["message"]


# Tests for _build_response_data


def test_build_response_data_basic():
    """_build_response_data builds correct structure."""
    sources = [
        SearchResult(
            chunk_id="chunk_1",
            text="Source text",
            snippet="Source...",
            score=0.9,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        )
    ]
    llm_result: dict[str, str | int | bool | None] = {
        "answer": "Test answer",
        "llm_exit_code": 0,
        "llm_enabled": True,
        "llm_command": "test-llm",
    }

    data = _build_response_data(
        problem_id=6,
        question="What is this?",
        prompt="Test prompt",
        sources=sources,
        query="Problem 6: Test. Question: What is this?",
        limit=5,
        used_fts=True,
        llm_result=llm_result,
    )

    assert data["problem_id"] == 6
    assert data["question"] == "What is this?"
    assert data["prompt"] == "Test prompt"
    assert data["answer"] == "Test answer"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["chunk_id"] == "chunk_1"
    assert data["sources"][0]["rank"] == 1
    assert data["sources"][0]["source_type"] == "problem_statement"
    assert data["retrieval"]["query"] == "Problem 6: Test. Question: What is this?"
    assert data["retrieval"]["limit"] == 5
    assert data["retrieval"]["count"] == 1
    assert data["retrieval"]["used_fts"] is True
    assert data["llm"]["enabled"] is True
    assert data["llm"]["command"] == "test-llm"
    assert data["llm"]["exit_code"] == 0


def test_build_response_data_no_llm():
    """_build_response_data handles disabled LLM."""
    llm_result: dict[str, str | int | bool | None] = {
        "answer": None,
        "llm_exit_code": None,
        "llm_enabled": False,
        "llm_command": None,
    }

    data = _build_response_data(
        problem_id=6,
        question="What is this?",
        prompt="Test prompt",
        sources=[],
        query="Query",
        limit=5,
        used_fts=False,
        llm_result=llm_result,
    )

    assert data["answer"] is None
    assert data["llm"]["enabled"] is False
    assert data["llm"]["command"] is None
    assert data["llm"]["exit_code"] is None
    assert data["retrieval"]["used_fts"] is False


def test_build_response_data_multiple_sources():
    """_build_response_data assigns correct ranks to multiple sources."""
    sources = [
        SearchResult(
            chunk_id=f"chunk_{i}",
            text=f"Text {i}",
            snippet=f"Snippet {i}",
            score=1.0 - i * 0.1,
            source_type=ChunkSource.REFERENCE_FULLTEXT,
            problem_id=6,
            reference_doi=f"10.1234/{i}" if i > 0 else None,
        )
        for i in range(3)
    ]
    llm_result: dict[str, str | int | bool | None] = {
        "answer": None,
        "llm_exit_code": None,
        "llm_enabled": False,
        "llm_command": None,
    }

    data = _build_response_data(
        problem_id=6,
        question="test",
        prompt="prompt",
        sources=sources,
        query="query",
        limit=10,
        used_fts=True,
        llm_result=llm_result,
    )

    assert len(data["sources"]) == 3
    assert data["sources"][0]["rank"] == 1
    assert data["sources"][1]["rank"] == 2
    assert data["sources"][2]["rank"] == 3
    assert data["sources"][0]["reference_doi"] is None
    assert data["sources"][1]["reference_doi"] == "10.1234/1"
    assert data["retrieval"]["count"] == 3
