"""Unit tests for run_logger module."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from erdos.core.models import CLIOutput
from erdos.core.run_logger import (
    LOG_SCHEMA_VERSION,
    RunLogEntry,
    RunLogger,
    generate_run_id,
    parse_since,
    sanitize_secrets,
)


if TYPE_CHECKING:
    from pathlib import Path


class TestGenerateRunId:
    """Tests for generate_run_id()."""

    def test_generates_unique_ids(self) -> None:
        """Run IDs should be unique."""
        ids = [generate_run_id() for _ in range(100)]
        assert len(ids) == len(set(ids))

    def test_format_includes_prefix(self) -> None:
        """Run ID should start with 'run_'."""
        run_id = generate_run_id()
        assert run_id.startswith("run_")

    def test_format_includes_timestamp(self) -> None:
        """Run ID should include timestamp components."""
        with patch("erdos.core.run_logger.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 18, 10, 30, 45, tzinfo=UTC)
            run_id = generate_run_id()
            assert "20260118" in run_id
            assert "103045" in run_id


class TestParseSince:
    """Tests for parse_since() helper."""

    def test_parse_days(self) -> None:
        """Parse '7d' as 7 days ago."""
        now = datetime.now(UTC)
        result = parse_since("7d")
        delta = now - result
        # Allow small time drift between now() calls
        assert 6 <= delta.days <= 7

    def test_parse_hours(self) -> None:
        """Parse '2h' as 2 hours ago."""
        now = datetime.now(UTC)
        result = parse_since("2h")
        delta = now - result
        assert 1.9 < delta.total_seconds() / 3600 < 2.1

    def test_parse_minutes(self) -> None:
        """Parse '30m' as 30 minutes ago."""
        now = datetime.now(UTC)
        result = parse_since("30m")
        delta = now - result
        assert 29 < delta.total_seconds() / 60 < 31

    def test_parse_iso8601(self) -> None:
        """Parse ISO 8601 date string."""
        result = parse_since("2026-01-15T00:00:00Z")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_parse_iso8601_date_only(self) -> None:
        """Parse ISO 8601 date-only string."""
        result = parse_since("2026-01-15")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_invalid_format_raises(self) -> None:
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid since format"):
            parse_since("invalid")


class TestRunLogEntry:
    """Tests for RunLogEntry model."""

    def test_create_from_cli_output_success(self) -> None:
        """Create entry from successful CLIOutput."""
        cli_output = CLIOutput.ok(
            command="erdos show",
            data={"id": 6, "status": "open"},
            duration_ms=123,
        )
        entry = RunLogEntry.from_cli_output(
            cli_output=cli_output,
            args={"problem_id": 6},
        )
        assert entry.command == "erdos show"
        assert entry.success is True
        assert entry.args == {"problem_id": 6}
        assert entry.duration_ms == 123
        assert entry.problem_id == 6
        assert entry.result == {"status": "open", "has_prize": False}
        assert entry.error is None

    def test_create_from_cli_output_failure(self) -> None:
        """Create entry from failed CLIOutput."""
        cli_output = CLIOutput.err(
            command="erdos show",
            error_type="NotFound",
            message="Problem 999 not found",
            code=2,
        )
        entry = RunLogEntry.from_cli_output(
            cli_output=cli_output,
            args={"problem_id": 999},
        )
        assert entry.command == "erdos show"
        assert entry.success is False
        assert entry.error == {"type": "NotFound", "message": "Problem 999 not found"}

    def test_sanitize_args_redacts_secrets(self) -> None:
        """Args containing secrets should be redacted."""
        cli_output = CLIOutput.ok(command="erdos ingest", data={})
        entry = RunLogEntry.from_cli_output(
            cli_output=cli_output,
            args={
                "problem_id": 6,
                "api_key": "sk-12345",
                "token": "tok_secret",
                "secret_value": "hidden",
            },
        )
        assert entry.args["problem_id"] == 6
        assert entry.args["api_key"] == "[REDACTED]"
        assert entry.args["token"] == "[REDACTED]"  # noqa: S105
        assert entry.args["secret_value"] == "[REDACTED]"  # noqa: S105

    def test_extract_problem_id_from_args(self) -> None:
        """problem_id should be extracted from args."""
        cli_output = CLIOutput.ok(command="erdos show", data={})
        entry = RunLogEntry.from_cli_output(
            cli_output=cli_output,
            args={"problem_id": 42},
        )
        assert entry.problem_id == 42

    def test_extract_problem_id_from_data(self) -> None:
        """problem_id should be extracted from data if not in args."""
        cli_output = CLIOutput.ok(
            command="erdos show",
            data={"id": 42, "title": "Test"},
        )
        entry = RunLogEntry.from_cli_output(
            cli_output=cli_output,
            args={},
        )
        assert entry.problem_id == 42

    def test_serialization_to_json(self) -> None:
        """Entry should serialize to valid JSON."""
        cli_output = CLIOutput.ok(command="erdos show", data={"id": 6})
        entry = RunLogEntry.from_cli_output(cli_output=cli_output, args={})
        json_str = entry.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == LOG_SCHEMA_VERSION
        assert parsed["command"] == "erdos show"
        assert parsed["success"] is True


class TestRunLogger:
    """Tests for RunLogger class."""

    def test_log_writes_to_file(self, tmp_path: Path) -> None:
        """log() should append an entry to the log file."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        cli_output = CLIOutput.ok(command="erdos show", data={"id": 6})
        logger.log(cli_output=cli_output, args={"problem_id": 6})

        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["command"] == "erdos show"

    def test_log_appends_multiple_entries(self, tmp_path: Path) -> None:
        """Multiple log() calls should append entries."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        for i in range(3):
            cli_output = CLIOutput.ok(command=f"erdos test{i}", data={})
            logger.log(cli_output=cli_output, args={})

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_log_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """log() should create parent directories."""
        log_file = tmp_path / "subdir" / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        cli_output = CLIOutput.ok(command="erdos show", data={})
        logger.log(cli_output=cli_output, args={})
        assert log_file.exists()

    def test_query_returns_all_entries(self, tmp_path: Path) -> None:
        """query() with no filters returns all entries."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        for i in range(5):
            cli_output = CLIOutput.ok(command=f"erdos test{i}", data={})
            logger.log(cli_output=cli_output, args={})

        entries = logger.query()
        assert len(entries) == 5

    def test_query_filters_by_command(self, tmp_path: Path) -> None:
        """query() should filter by command name."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})
        logger.log(CLIOutput.ok(command="erdos search", data={}), args={})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})

        entries = logger.query(command="erdos show")
        assert len(entries) == 2
        assert all(e.command == "erdos show" for e in entries)

    def test_query_filters_by_problem_id(self, tmp_path: Path) -> None:
        """query() should filter by problem_id."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 7})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})

        entries = logger.query(problem_id=6)
        assert len(entries) == 2
        assert all(e.problem_id == 6 for e in entries)

    def test_query_filters_by_status(self, tmp_path: Path) -> None:
        """query() should filter by success/failure status."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})
        logger.log(
            CLIOutput.err(
                command="erdos show", error_type="NotFound", message="Not found", code=2
            ),
            args={},
        )
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})

        entries = logger.query(status="failure")
        assert len(entries) == 1
        assert entries[0].success is False

        entries = logger.query(status="success")
        assert len(entries) == 2
        assert all(e.success for e in entries)

    def test_query_filters_by_since(self, tmp_path: Path) -> None:
        """query() should filter by timestamp."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)

        # Create an old entry manually
        old_entry = {
            "schema_version": 1,
            "id": "run_old",
            "timestamp": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
            "command": "erdos old",
            "args": {},
            "duration_ms": 100,
            "success": True,
        }
        log_file.write_text(json.dumps(old_entry) + "\n")

        # Add a recent entry
        logger.log(CLIOutput.ok(command="erdos new", data={}), args={})

        # Query for last 7 days
        entries = logger.query(since="7d")
        assert len(entries) == 1
        assert entries[0].command == "erdos new"

    def test_query_applies_limit(self, tmp_path: Path) -> None:
        """query() should respect limit parameter."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        for i in range(10):
            logger.log(CLIOutput.ok(command=f"erdos test{i}", data={}), args={})

        entries = logger.query(limit=5)
        assert len(entries) == 5

    def test_query_returns_most_recent_first(self, tmp_path: Path) -> None:
        """query() should return entries in reverse chronological order."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        for i in range(3):
            logger.log(CLIOutput.ok(command=f"erdos test{i}", data={}), args={})

        entries = logger.query()
        # Most recent should be first
        assert entries[0].command == "erdos test2"
        assert entries[2].command == "erdos test0"

    def test_query_empty_file(self, tmp_path: Path) -> None:
        """query() should handle empty/missing log file."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        entries = logger.query()
        assert entries == []

    def test_summary_aggregates_data(self, tmp_path: Path) -> None:
        """summary() should aggregate log data."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)

        # Add mixed entries
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(
            CLIOutput.err(
                command="erdos lean check",
                error_type="Error",
                message="Failed",
                code=1,
            ),
            args={"problem_id": 6},
        )
        logger.log(
            CLIOutput.ok(command="erdos lean check", data={}), args={"problem_id": 7}
        )
        logger.log(CLIOutput.ok(command="erdos search", data={}), args={})

        summary = logger.summary()
        assert summary["total_runs"] == 5
        assert summary["by_command"]["erdos show"]["runs"] == 2
        assert summary["by_command"]["erdos show"]["success"] == 2
        assert summary["by_command"]["erdos lean check"]["runs"] == 2
        assert summary["by_command"]["erdos lean check"]["failure"] == 1
        assert summary["by_problem"]["6"]["runs"] == 3
        assert summary["by_problem"]["7"]["runs"] == 1
        assert summary["metrics"]["problems_attempted"] == 2

    def test_summary_with_filters(self, tmp_path: Path) -> None:
        """summary() should respect filters."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(CLIOutput.ok(command="erdos search", data={}), args={})

        summary = logger.summary(command="erdos show")
        assert summary["total_runs"] == 1
        assert "erdos search" not in summary["by_command"]

    def test_summary_empty_logs(self, tmp_path: Path) -> None:
        """summary() should handle empty logs gracefully."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)
        summary = logger.summary()
        assert summary["total_runs"] == 0
        assert summary["by_command"] == {}
        assert summary["by_problem"] == {}


class TestRunLoggerLeanIntegration:
    """Tests for Lean-specific log entry handling."""

    def test_lean_check_extracts_result(self, tmp_path: Path) -> None:
        """Lean check results should include error count and sorry status."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)

        cli_output = CLIOutput.ok(
            command="erdos lean check",
            data={
                "success": False,
                "errors": [{"line": 15, "message": "type mismatch"}],
                "has_sorry": True,
            },
        )
        logger.log(cli_output=cli_output, args={"file": "Erdos/Problem006.lean"})

        entries = logger.query()
        assert len(entries) == 1
        result = entries[0].result
        assert result is not None
        assert result.get("error_count") == 1
        assert result.get("has_sorry") is True


class TestRunLoggerSearchIntegration:
    """Tests for search-specific log entry handling."""

    def test_search_extracts_hit_count(self, tmp_path: Path) -> None:
        """Search results should include hit count."""
        log_file = tmp_path / "runs.jsonl"
        logger = RunLogger(log_file=log_file)

        cli_output = CLIOutput.ok(
            command="erdos search",
            data={
                "query": "prime",
                "results": [{"id": 4}, {"id": 6}, {"id": 123}],
            },
        )
        logger.log(cli_output=cli_output, args={"query": "prime"})

        entries = logger.query()
        result = entries[0].result
        assert result is not None
        assert result.get("hit_count") == 3
        assert result.get("top_problem_ids") == [4, 6, 123]


class TestSanitizeSecrets:
    """Tests for the sanitize_secrets() function."""

    def test_redacts_api_key_in_string_values(self) -> None:
        """API keys embedded in string values should be redacted."""
        data = {"prompt": "Use this key: sk-abcdefghij1234567890abcd"}
        result = sanitize_secrets(data)
        assert "sk-abcdefghij1234567890abcd" not in result["prompt"]
        assert "[REDACTED]" in result["prompt"]

    def test_redacts_bearer_tokens(self) -> None:
        """Bearer tokens should be redacted."""
        data = {"text": "Token: Bearer my_secret_token_value"}
        result = sanitize_secrets(data)
        assert "my_secret_token_value" not in result["text"]
        assert "[REDACTED]" in result["text"]

    def test_redacts_authorization_headers(self) -> None:
        """Authorization headers should be redacted."""
        data = {"headers": "Authorization: Basic dXNlcjpwYXNz"}
        result = sanitize_secrets(data)
        assert "dXNlcjpwYXNz" not in result["headers"]
        assert "[REDACTED]" in result["headers"]

    def test_redacts_by_key_name(self) -> None:
        """Keys containing secret patterns should have values redacted."""
        data = {
            "api_key": "my-key",
            "auth_token": "tok123",
            "password": "secret",
            "credential_data": "creds",
        }
        result = sanitize_secrets(data)
        redacted = "[REDACTED]"
        assert result["api_key"] == redacted
        assert result["auth_token"] == redacted
        assert result["password"] == redacted
        assert result["credential_data"] == redacted

    def test_handles_nested_dicts(self) -> None:
        """Nested dictionaries should be sanitized recursively."""
        data = {
            "outer": {
                "api_key": "secret-val",
                "inner": {"text": "Use sk-test1234567890abcdefghij"},
            }
        }
        result = sanitize_secrets(data)
        assert result["outer"]["api_key"] == "[REDACTED]"
        assert "sk-test1234567890abcdefghij" not in result["outer"]["inner"]["text"]

    def test_handles_lists(self) -> None:
        """Lists should be sanitized recursively."""
        data = {
            "items": [
                "normal text",
                "has key: sk-abcdefghij1234567890abcd",
                {"api_key": "secret"},
            ]
        }
        result = sanitize_secrets(data)
        assert result["items"][0] == "normal text"
        assert "sk-abcdefghij1234567890abcd" not in result["items"][1]
        assert result["items"][2]["api_key"] == "[REDACTED]"

    def test_preserves_non_secret_data(self) -> None:
        """Non-secret data should be preserved unchanged."""
        data = {
            "message": "Hello world",
            "count": 42,
            "flag": True,
            "nested": {"value": 123},
        }
        result = sanitize_secrets(data)
        assert result["message"] == "Hello world"
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["nested"]["value"] == 123
