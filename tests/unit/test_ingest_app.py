"""Unit tests for ingest application service (core/ingest/app.py).

Tests pure orchestration logic without CLI concerns (Typer/Rich).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from erdos.core.exit_codes import ExitCode


if TYPE_CHECKING:
    import pytest
from erdos.core.ingest.app import (
    IngestOptions,
    batch_result_to_cli_output,
    execute_ingest,
    get_repo_root,
    is_batch_mode,
    prepare_mailto,
    run_batch_ingestion,
    run_single_ingestion,
)
from erdos.core.ingest.fetch import MetadataSource


class TestGetRepoRoot:
    """Tests for get_repo_root()."""

    def test_uses_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_repo_root uses ERDOS_REPO_ROOT env var if set."""
        test_path = "/test/repo/root"
        monkeypatch.setenv("ERDOS_REPO_ROOT", test_path)

        result = get_repo_root()

        assert result == Path(test_path)

    def test_defaults_to_cwd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_repo_root defaults to cwd if env var not set."""
        monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)

        result = get_repo_root()

        assert result == Path.cwd()


class TestPrepareMailto:
    """Tests for prepare_mailto()."""

    def test_uses_provided_mailto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test prepare_mailto uses provided value."""
        monkeypatch.delenv("ERDOS_MAILTO", raising=False)

        result = prepare_mailto("user@example.com")

        assert result == "user@example.com"

    def test_uses_env_var_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test prepare_mailto uses env var when input empty."""
        monkeypatch.setenv("ERDOS_MAILTO", "env@example.com")

        result = prepare_mailto("")

        assert result == "env@example.com"

    def test_uses_default_when_no_mailto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test prepare_mailto uses default when no mailto available."""
        monkeypatch.delenv("ERDOS_MAILTO", raising=False)

        result = prepare_mailto("")

        assert result == "erdos-banger@example.com"


class TestIsBatchMode:
    """Tests for is_batch_mode()."""

    def test_single_mode_with_problem_id(self) -> None:
        """Test single mode when problem_id is specified."""
        options = IngestOptions(problem_id=6)

        assert is_batch_mode(options) is False

    def test_batch_mode_with_all_flag(self) -> None:
        """Test batch mode when --all is specified."""
        options = IngestOptions(problem_id=None, all_problems=True)

        assert is_batch_mode(options) is True

    def test_batch_mode_with_status_filter(self) -> None:
        """Test batch mode when status filter is specified."""
        options = IngestOptions(problem_id=None, status="open")

        assert is_batch_mode(options) is True

    def test_batch_mode_with_prize_filter(self) -> None:
        """Test batch mode when prize filter is specified."""
        options = IngestOptions(problem_id=None, prize_min=100)

        assert is_batch_mode(options) is True

    def test_batch_mode_with_tags(self) -> None:
        """Test batch mode when tags are specified."""
        options = IngestOptions(problem_id=None, tags=["combinatorics"])

        assert is_batch_mode(options) is True

    def test_batch_mode_with_resume(self) -> None:
        """Test batch mode when resume is specified."""
        options = IngestOptions(problem_id=None, resume=True)

        assert is_batch_mode(options) is True

    def test_not_batch_mode_without_filters(self) -> None:
        """Test that bare no-problem-id without filters is not batch mode."""
        options = IngestOptions(problem_id=None)

        assert is_batch_mode(options) is False


class TestIngestOptions:
    """Tests for IngestOptions dataclass."""

    def test_defaults(self) -> None:
        """Test IngestOptions with default values."""
        options = IngestOptions(problem_id=6)

        assert options.problem_id == 6
        assert options.force is False
        assert options.no_download is False
        assert options.no_network is False
        assert options.timeout == 30.0
        assert options.delay == 3.0
        assert options.mailto == ""
        assert options.source == MetadataSource.OPENALEX
        assert options.max_concurrent == 1
        assert options.dry_run is False

    def test_all_values(self) -> None:
        """Test IngestOptions with all values set."""
        options = IngestOptions(
            problem_id=42,
            force=True,
            no_download=True,
            no_network=True,
            timeout=60.0,
            delay=5.0,
            mailto="test@example.com",
            source=MetadataSource.ARXIV,
            all_problems=True,
            status="open",
            prize_min=100,
            prize_max=1000,
            tags=["graph theory"],
            limit=10,
            skip=5,
            resume=True,
            dry_run=True,
            max_concurrent=2,
        )

        assert options.problem_id == 42
        assert options.force is True
        assert options.source == MetadataSource.ARXIV
        assert options.all_problems is True
        assert options.tags == ["graph theory"]
        assert options.max_concurrent == 2


class TestRunSingleIngestion:
    """Tests for run_single_ingestion()."""

    def test_requires_problem_id(self, tmp_path: Path) -> None:
        """Test that run_single_ingestion returns error when problem_id is None."""
        options = IngestOptions(problem_id=None)

        result = run_single_ingestion(
            options, tmp_path, "test@example.com", repo=MagicMock()
        )

        assert result.success is False
        assert result.error is not None
        assert "Problem ID is required" in str(result.error.get("message", ""))
        assert result.error.get("code") == ExitCode.USAGE_ERROR

    @patch("erdos.core.ingest.app.ingest_problem_references")
    def test_calls_ingest_problem_references(
        self, mock_ingest: MagicMock, tmp_path: Path
    ) -> None:
        """Test run_single_ingestion calls core logic correctly."""
        options = IngestOptions(
            problem_id=6,
            force=True,
            no_download=True,
            no_network=False,
            timeout=45.0,
            delay=5.0,
            source=MetadataSource.ARXIV,
        )
        mock_result = MagicMock()
        mock_ingest.return_value = mock_result
        repo = MagicMock()

        result = run_single_ingestion(options, tmp_path, "user@example.com", repo=repo)

        mock_ingest.assert_called_once_with(
            6,
            repo=repo,
            repo_root=tmp_path,
            force=True,
            no_download=True,
            no_network=False,
            timeout=45.0,
            delay=5.0,
            mailto="user@example.com",
            source=MetadataSource.ARXIV,
        )
        assert result is mock_result


class TestRunBatchIngestion:
    """Tests for run_batch_ingestion()."""

    def test_rejects_max_concurrent_greater_than_one(self, tmp_path: Path) -> None:
        """Test that max_concurrent > 1 is rejected for ingest."""
        options = IngestOptions(problem_id=None, all_problems=True, max_concurrent=2)

        result = run_batch_ingestion(
            options, tmp_path, "test@example.com", repo=MagicMock()
        )

        assert result.success is False
        assert result.error is not None
        assert "max-concurrent > 1" in str(result.error.get("message", ""))
        assert result.error.get("code") == ExitCode.USAGE_ERROR

    def test_returns_not_found_when_no_problems_match(self, tmp_path: Path) -> None:
        """Test that empty filter result returns NOT_FOUND."""
        options = IngestOptions(
            problem_id=None, all_problems=True, status="nonexistent"
        )
        repo = MagicMock()
        repo.load_all.return_value = []  # No problems

        result = run_batch_ingestion(options, tmp_path, "test@example.com", repo=repo)

        assert result.success is False
        assert result.error is not None
        assert "No problems match" in str(result.error.get("message", ""))
        assert result.error.get("code") == ExitCode.NOT_FOUND


class TestBatchResultToCliOutput:
    """Tests for batch_result_to_cli_output()."""

    def test_error_result(self) -> None:
        """Test conversion of error BatchResult."""
        from erdos.core.batch import BatchResult

        batch_result = BatchResult(
            batch_id="test",
            total=5,
            completed_count=0,
            failed_count=0,
            failed_ids=[],
            duration_ms=100,
            exit_code=ExitCode.NOT_FOUND,
            error_message="No previous batch",
        )

        result = batch_result_to_cli_output(batch_result, [1, 2, 3])

        assert result.success is False
        assert result.error is not None
        assert "No previous batch" in str(result.error.get("message", ""))

    def test_success_result(self) -> None:
        """Test conversion of successful BatchResult."""
        from erdos.core.batch import BatchResult

        batch_result = BatchResult(
            batch_id="batch_123",
            total=3,
            completed_count=3,
            failed_count=0,
            failed_ids=[],
            duration_ms=500,
        )

        result = batch_result_to_cli_output(batch_result, [1, 2, 3])

        assert result.success is True
        assert result.data["batch_id"] == "batch_123"
        assert result.data["completed"] == 3
        assert result.data["failed"] == 0

    def test_partial_failure_result(self) -> None:
        """Test conversion of partial failure BatchResult."""
        from erdos.core.batch import BatchResult

        batch_result = BatchResult(
            batch_id="batch_456",
            total=3,
            completed_count=2,
            failed_count=1,
            failed_ids=[2],
            duration_ms=600,
        )

        result = batch_result_to_cli_output(batch_result, [1, 2, 3])

        # Partial failure: success=False, error message includes count
        assert result.success is False
        assert result.error is not None
        assert "1 of 3 problems failed" in str(result.error.get("message", ""))
        assert result.error.get("type") == "PartialBatchFailure"

    def test_dry_run_includes_problem_ids(self) -> None:
        """Test that dry run result includes problem_ids."""
        from erdos.core.batch import BatchResult

        batch_result = BatchResult(
            batch_id="batch_789",
            total=3,
            completed_count=0,
            failed_count=0,
            failed_ids=[],
            duration_ms=50,
            dry_run=True,
        )

        result = batch_result_to_cli_output(batch_result, [1, 2, 3])

        assert result.success is True
        assert result.data["dry_run"] is True
        assert result.data["problem_ids"] == [1, 2, 3]


class TestExecuteIngest:
    """Tests for execute_ingest() - main orchestration entrypoint."""

    def test_validates_no_problem_id_without_filters(self) -> None:
        """Test execute_ingest rejects bare no-problem-id."""
        options = IngestOptions(problem_id=None)

        result = execute_ingest(options, repo=MagicMock())

        assert result.success is False
        assert result.error is not None
        assert "Provide a PROBLEM_ID" in str(result.error.get("message", ""))
        assert result.error.get("code") == ExitCode.USAGE_ERROR

    @patch("erdos.core.ingest.app.run_single_ingestion")
    @patch("erdos.core.ingest.app.prepare_mailto")
    @patch("erdos.core.ingest.app.get_repo_root")
    def test_delegates_to_single_ingestion(
        self,
        mock_repo_root: MagicMock,
        mock_mailto: MagicMock,
        mock_single: MagicMock,
    ) -> None:
        """Test execute_ingest delegates to run_single_ingestion for single mode."""
        mock_repo_root.return_value = Path("/repo")
        mock_mailto.return_value = "test@example.com"
        mock_single.return_value = MagicMock(success=True)
        repo = MagicMock()
        options = IngestOptions(problem_id=6)

        execute_ingest(options, repo=repo)

        mock_single.assert_called_once()

    @patch("erdos.core.ingest.app.run_batch_ingestion")
    @patch("erdos.core.ingest.app.prepare_mailto")
    @patch("erdos.core.ingest.app.get_repo_root")
    def test_delegates_to_batch_ingestion(
        self,
        mock_repo_root: MagicMock,
        mock_mailto: MagicMock,
        mock_batch: MagicMock,
    ) -> None:
        """Test execute_ingest delegates to run_batch_ingestion for batch mode."""
        mock_repo_root.return_value = Path("/repo")
        mock_mailto.return_value = "test@example.com"
        mock_batch.return_value = MagicMock(success=True)
        repo = MagicMock()
        options = IngestOptions(problem_id=None, all_problems=True)

        execute_ingest(options, repo=repo)

        mock_batch.assert_called_once()


class TestNoNetworkNowDownloadPolicyCombinations:
    """Tests for --no-network / --no-download policy combinations."""

    @patch("erdos.core.ingest.app.ingest_problem_references")
    def test_no_download_passed_through(
        self, mock_ingest: MagicMock, tmp_path: Path
    ) -> None:
        """Test --no-download is passed to core service."""
        options = IngestOptions(problem_id=6, no_download=True)
        mock_ingest.return_value = MagicMock(success=True)

        run_single_ingestion(options, tmp_path, "test@example.com", repo=MagicMock())

        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["no_download"] is True

    @patch("erdos.core.ingest.app.ingest_problem_references")
    def test_no_network_passed_through(
        self, mock_ingest: MagicMock, tmp_path: Path
    ) -> None:
        """Test --no-network is passed to core service."""
        options = IngestOptions(problem_id=6, no_network=True)
        mock_ingest.return_value = MagicMock(success=True)

        run_single_ingestion(options, tmp_path, "test@example.com", repo=MagicMock())

        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["no_network"] is True

    @patch("erdos.core.ingest.app.ingest_problem_references")
    def test_both_policies_passed_through(
        self, mock_ingest: MagicMock, tmp_path: Path
    ) -> None:
        """Test --no-network + --no-download both passed to core service."""
        options = IngestOptions(problem_id=6, no_download=True, no_network=True)
        mock_ingest.return_value = MagicMock(success=True)

        run_single_ingestion(options, tmp_path, "test@example.com", repo=MagicMock())

        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["no_download"] is True
        assert call_kwargs["no_network"] is True
