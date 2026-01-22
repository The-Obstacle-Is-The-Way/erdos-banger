"""Integration tests for erdos ask command (SPEC-011)."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from erdos.core.problem_loader import ProblemLoader
from erdos.core.search.facade import SearchIndex
from erdos.core.search.index_builder import build_index


if TYPE_CHECKING:
    from pathlib import Path


runner = CliRunner()


def _setup_test_env(tmp_path: Path, sample_problems_yaml: Path) -> tuple[Path, Path]:
    """Create test environment with data and index."""
    # Create data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")

    # Create index directory
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    index_path = index_dir / "erdos.sqlite"

    # Build search index
    loader = ProblemLoader(data_dir / "problems.yaml")
    index = SearchIndex(index_path)
    build_index(loader=loader, index=index)

    return data_dir, index_path


def _setup_test_env_no_index(
    tmp_path: Path, sample_problems_yaml: Path
) -> tuple[Path, Path]:
    """Create test environment with data but no built index."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")

    index_dir = tmp_path / "index"
    index_dir.mkdir()
    index_path = index_dir / "erdos.sqlite"
    return data_dir, index_path


def test_ask_command_json_output_no_llm(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask with --json and --no-llm flags outputs valid JSON."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "What partial results are known?", "--no-llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    # Assert exit code success
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Assert stdout is valid JSON
    data = json.loads(result.stdout)
    assert data["command"] == "erdos ask"
    assert data["success"] is True
    assert "data" in data

    # Assert expected fields in data
    result_data = data["data"]
    assert result_data["problem_id"] == 6
    assert result_data["question"] == "What partial results are known?"
    assert result_data["answer"] is None  # --no-llm
    assert "prompt" in result_data
    assert isinstance(result_data["sources"], list)
    assert len(result_data["sources"]) > 0
    assert "retrieval" in result_data
    assert result_data["retrieval"]["limit"] == 5
    assert result_data["llm"]["enabled"] is False


def test_ask_command_with_limit(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask --limit flag."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command with --limit 3
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "test", "--no-llm", "--limit", "3"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["retrieval"]["limit"] == 3


def test_ask_command_sources_returned(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask returns sources from the index."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command with a single word query that should match problem 6
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "primes", "--no-llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    sources = data["data"]["sources"]
    assert len(sources) > 0

    # Verify source structure
    source = sources[0]
    assert "chunk_id" in source
    assert "rank" in source
    assert "source_type" in source
    assert "problem_id" in source
    assert "text" in source


def test_ask_command_prompt_includes_problem_statement(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test prompt includes the actual problem statement (not mocked)."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "test?", "--no-llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    prompt = data["data"]["prompt"]

    # Verify prompt contains real problem data
    assert "Problem:" in prompt
    assert "id: 6" in prompt
    assert "Question:" in prompt
    assert "test?" in prompt


def test_ask_command_with_fake_llm(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask with a fake LLM command."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Create a fake LLM script that echoes input
    fake_llm = tmp_path / "fake_llm.sh"
    fake_llm.write_text("#!/bin/bash\necho 'Test answer from LLM'")
    fake_llm.chmod(0o755)

    # Run command with fake LLM
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "test?", "--llm-cmd", str(fake_llm)],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    result_data = data["data"]

    # Verify LLM was called
    assert result_data["answer"] is not None
    assert "Test answer from LLM" in result_data["answer"]
    assert result_data["llm"]["enabled"] is True
    assert result_data["llm"]["exit_code"] == 0


def test_ask_command_not_found_error(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask with nonexistent problem ID."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command with invalid problem ID
    result = runner.invoke(
        app,
        ["--json", "ask", "9999", "test", "--no-llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == ExitCode.NOT_FOUND
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error"]["code"] == ExitCode.NOT_FOUND
    assert "not found" in data["error"]["message"].lower()


def test_ask_command_stdin_question(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask with question from stdin."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command with '-' for stdin
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "-", "--no-llm"],
        input="What is the status?\n",
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should strip trailing newline
    assert data["data"]["question"] == "What is the status?"


def test_ask_command_empty_stdin_question_is_usage_error_json(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask '-' stdin question cannot be empty in JSON mode."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    result = runner.invoke(
        app,
        ["--json", "ask", "6", "-", "--no-llm"],
        input="\n",
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == ExitCode.USAGE_ERROR
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error"]["code"] == ExitCode.USAGE_ERROR
    assert "empty" in data["error"]["message"].lower()


def test_ask_command_falls_back_when_index_empty(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """When no index exists yet, ask should return statement/notes sources (used_fts=false)."""
    data_dir, index_path = _setup_test_env_no_index(tmp_path, sample_problems_yaml)

    result = runner.invoke(
        app,
        ["--json", "ask", "6", "primes", "--no-llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    retrieval = data["data"]["retrieval"]
    assert retrieval["used_fts"] is False
    assert data["data"]["sources"]
    assert data["data"]["sources"][0]["chunk_id"] == "problem_6_statement"


def test_ask_command_human_output(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask human-readable output."""
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command without --json
    result = runner.invoke(
        app,
        ["ask", "6", "test?", "--no-llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    assert result.exit_code == 0
    # Should contain human-friendly formatting
    assert "Problem" in result.stdout
    assert "sources" in result.stdout.lower()


def test_ask_command_config_error_exit_code(
    tmp_path: Path,
    sample_problems_yaml: Path,
) -> None:
    """Test erdos ask returns ExitCode.CONFIG_ERROR (10) not 78 when LLM not found.

    This test verifies BUG-008 is fixed: hardcoded exit code 78 should be
    replaced with ExitCode.CONFIG_ERROR (10) per SPEC-011 Section 3.2.
    """
    data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

    # Run command with nonexistent LLM command (not --no-llm)
    result = runner.invoke(
        app,
        ["--json", "ask", "6", "test?", "--llm-cmd", "/nonexistent/llm"],
        env={
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_INDEX_PATH": str(index_path),
        },
    )

    # Should fail with CONFIG_ERROR (10), not 78
    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.exit_code == 10  # Explicit value check
    assert result.exit_code != 78  # Verify old hardcoded value is gone

    # Verify error message in JSON output
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error"]["type"] == "CONFIG_ERROR"
    assert "not found" in data["error"]["message"].lower()
    assert data["error"]["code"] == 10  # ExitCode.CONFIG_ERROR value
