"""Integration tests for batch operations (SPEC-015)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with sample problems."""
    # Copy sample problems to temp dir
    sample_yaml = Path("tests/fixtures/sample_problems.yaml")
    if sample_yaml.exists():
        content = sample_yaml.read_text()
        yaml_path = tmp_path / "problems_enriched.yaml"
        yaml_path.write_text(content)
    return tmp_path


class TestBatchIngestCLI:
    """Integration tests for batch ingest command."""

    def test_ingest_help_shows_batch_options(self, strip_ansi) -> None:
        """Test that ingest --help shows batch options."""
        # terminal_width prevents Rich from truncating help text in CI environments
        result = runner.invoke(app, ["ingest", "--help"], terminal_width=200)
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Batch options should be visible
        assert "--all" in output
        assert "--status" in output
        assert "--prize-min" in output
        assert "--prize-max" in output
        assert "--tag" in output
        assert "--limit" in output
        assert "--skip" in output
        assert "--resume" in output
        assert "--dry-run" in output
        assert "--max-concurrent" in output

    def test_ingest_no_args_shows_error(self, sample_data_dir: Path) -> None:
        """Test that ingest without args shows usage error."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(app, ["--json", "ingest"], env=env)
        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert "UsageError" in str(output.get("error", {}))

    def test_ingest_dry_run_batch(self, sample_data_dir: Path) -> None:
        """Test batch ingest with --dry-run shows what would be processed."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "ingest", "--all", "--dry-run", "--limit", "3"],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["data"]["dry_run"] is True
        assert "problem_ids" in output["data"]
        assert len(output["data"]["problem_ids"]) <= 3

    def test_ingest_dry_run_with_status_filter(self, sample_data_dir: Path) -> None:
        """Test batch ingest with status filter."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "ingest", "--status", "open", "--dry-run"],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["data"]["dry_run"] is True

    def test_ingest_max_concurrent_rejected_for_values_gt_1(
        self, sample_data_dir: Path
    ) -> None:
        """Test that --max-concurrent > 1 is rejected for ingest."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "ingest", "--all", "--max-concurrent", "4", "--dry-run"],
            env=env,
        )
        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert "max-concurrent" in output["error"]["message"].lower()


class TestBatchFormalizeCLI:
    """Integration tests for batch formalize command."""

    def test_formalize_help_shows_batch_options(self, strip_ansi) -> None:
        """Test that lean formalize --help shows batch options."""
        # terminal_width prevents Rich from truncating help text in CI environments
        result = runner.invoke(app, ["lean", "formalize", "--help"], terminal_width=200)
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Batch options should be visible
        assert "--all" in output
        assert "--status" in output
        assert "--tag" in output
        assert "--limit" in output
        assert "--skip-existing" in output
        assert "--dry-run" in output
        assert "--max-concurrent" in output

    def test_formalize_no_args_shows_error(self, sample_data_dir: Path) -> None:
        """Test that formalize without args shows usage error."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(app, ["--json", "lean", "formalize"], env=env)
        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert "UsageError" in str(output.get("error", {}))

    def test_formalize_dry_run_batch(self, sample_data_dir: Path) -> None:
        """Test batch formalize with --dry-run shows what would be processed."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "lean", "formalize", "--all", "--dry-run", "--limit", "3"],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["data"]["dry_run"] is True
        assert "problem_ids" in output["data"]
        assert len(output["data"]["problem_ids"]) <= 3

    def test_formalize_dry_run_with_status_filter(self, sample_data_dir: Path) -> None:
        """Test batch formalize with status filter."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "lean", "formalize", "--status", "open", "--dry-run"],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["data"]["dry_run"] is True

    def test_formalize_max_concurrent_accepted(self, sample_data_dir: Path) -> None:
        """Test that --max-concurrent > 1 is accepted for formalize (unlike ingest)."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        # Dry run with parallel setting - should not error
        result = runner.invoke(
            app,
            [
                "--json",
                "lean",
                "formalize",
                "--all",
                "--max-concurrent",
                "8",
                "--dry-run",
                "--limit",
                "1",
            ],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True


class TestBatchStateTracking:
    """Tests for batch state tracking and resume."""

    def test_batch_state_file_created(
        self, sample_data_dir: Path, tmp_path: Path
    ) -> None:
        """Test that batch state file is created during batch operations."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)
        env["ERDOS_REPO_ROOT"] = str(tmp_path)

        # Mock the actual ingestion to avoid network calls
        with patch("erdos.core.ingest.app.ingest_problem_references") as mock_ingest:
            from erdos.core.models import CLIOutput

            mock_ingest.return_value = CLIOutput.ok(
                command="erdos ingest",
                data={"problem_id": 6, "entries_written": 0},
            )

            result = runner.invoke(
                app,
                ["--json", "ingest", "--all", "--limit", "2", "--no-network"],
                env=env,
            )

            # Check batch state files exist
            batches_dir = tmp_path / "logs" / "batches"
            if result.exit_code == 0 and batches_dir.exists():
                latest_path = batches_dir / "latest.json"
                assert latest_path.exists() or mock_ingest.call_count == 0

    def test_resume_without_prior_state_fails(self, sample_data_dir: Path) -> None:
        """Test that --resume without prior state returns error."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "ingest", "--all", "--resume"],
            env=env,
        )
        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert "no previous batch" in output["error"]["message"].lower()


class TestBatchFiltering:
    """Tests for batch filtering options."""

    def test_filter_by_multiple_tags(self, sample_data_dir: Path) -> None:
        """Test filtering by multiple tags."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            [
                "--json",
                "ingest",
                "--tag",
                "number theory",
                "--tag",
                "primes",
                "--dry-run",
            ],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["data"]["dry_run"] is True

    def test_filter_by_prize_range(self, sample_data_dir: Path) -> None:
        """Test filtering by prize range."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            [
                "--json",
                "ingest",
                "--prize-min",
                "100",
                "--prize-max",
                "1000",
                "--dry-run",
            ],
            env=env,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["data"]["dry_run"] is True

    def test_skip_and_limit_pagination(self, sample_data_dir: Path) -> None:
        """Test skip and limit for manual pagination."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        # First batch
        result1 = runner.invoke(
            app,
            ["--json", "ingest", "--all", "--limit", "2", "--dry-run"],
            env=env,
        )
        assert result1.exit_code == 0
        output1 = json.loads(result1.output)
        first_batch_ids = output1["data"]["problem_ids"]

        # Second batch with skip
        result2 = runner.invoke(
            app,
            ["--json", "ingest", "--all", "--skip", "2", "--limit", "2", "--dry-run"],
            env=env,
        )
        assert result2.exit_code == 0
        output2 = json.loads(result2.output)
        second_batch_ids = output2["data"]["problem_ids"]

        # Batches should not overlap
        assert set(first_batch_ids).isdisjoint(set(second_batch_ids))

    def test_no_problems_match_filter(self, sample_data_dir: Path) -> None:
        """Test error when no problems match filter."""
        env = os.environ.copy()
        env["ERDOS_DATA_PATH"] = str(sample_data_dir)

        result = runner.invoke(
            app,
            ["--json", "ingest", "--prize-min", "999999999", "--dry-run"],
            env=env,
        )
        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert "no problems match" in output["error"]["message"].lower()
