"""Run logging for CLI commands.

Provides structured logging of all CLI command invocations to a JSON Lines file.
Each invocation creates one log entry with timing, success/failure, and result data.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, Field

from erdos.core.models.base import ErdosBaseModel, utc_now
from erdos.core.run_logger_summaries import get_summarizer


if TYPE_CHECKING:
    from erdos.core.models.output import CLIOutput


logger = logging.getLogger(__name__)

# Schema version for log entries (increment on breaking changes)
LOG_SCHEMA_VERSION = 1

# Default log file location
DEFAULT_LOG_FILE = Path("logs/runs.jsonl")

# Secret keys to redact from args (matched case-insensitively in key names)
SECRET_KEY_PATTERNS = ("key", "token", "secret", "password", "credential")

# Regex patterns to redact from string values (API keys, Authorization headers, etc.)
SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style API keys
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE),  # Bearer tokens
    re.compile(
        r"Authorization:\s*\S+(\s+\S+)?", re.IGNORECASE
    ),  # Authorization headers
    re.compile(r"[a-zA-Z0-9_-]{32,}"),  # Generic long tokens (32+ chars)
)


def generate_run_id() -> str:
    """Generate a unique run ID with timestamp and random suffix."""
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_suffix = secrets.token_hex(3)  # 6 hex chars
    return f"run_{timestamp}_{random_suffix}"


def parse_since(since: str) -> datetime:
    """Parse a since value into a datetime.

    Supports:
    - Relative: '7d' (days), '2h' (hours), '30m' (minutes)
    - ISO 8601: '2026-01-15T00:00:00Z' or '2026-01-15'

    Args:
        since: Time specification string

    Returns:
        Datetime threshold

    Raises:
        ValueError: If format is invalid
    """
    now = datetime.now(UTC)

    # Try relative format: Nd, Nh, Nm
    relative_match = re.match(r"^(\d+)([dhm])$", since.strip().lower())
    if relative_match:
        value = int(relative_match.group(1))
        unit = relative_match.group(2)
        if unit == "d":
            return now - timedelta(days=value)
        elif unit == "h":
            return now - timedelta(hours=value)
        elif unit == "m":
            return now - timedelta(minutes=value)

    # Try ISO 8601 with time
    try:
        # Try full ISO format with Z suffix
        if "T" in since:
            dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        # Try date-only format
        dt = datetime.strptime(since, "%Y-%m-%d")
        return dt.replace(tzinfo=UTC)
    except ValueError:
        pass

    raise ValueError(f"Invalid since format: {since}. Use Nd/Nh/Nm or ISO 8601.")


def sanitize_secrets(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values from a dictionary, including nested structures.

    This sanitizes both:
    1. Keys containing sensitive patterns (key, token, secret, password, credential)
    2. String values matching secret patterns (API keys, Authorization headers, etc.)

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized copy with secrets redacted
    """

    def sanitize_string(value: str) -> str:
        """Redact secret patterns in a string value."""
        result = value
        for pattern in SECRET_VALUE_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    def sanitize_value(key: str, value: Any) -> Any:
        """Recursively sanitize a value."""
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SECRET_KEY_PATTERNS):
            return "[REDACTED]"
        if isinstance(value, str):
            return sanitize_string(value)
        if isinstance(value, dict):
            return {k: sanitize_value(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [
                sanitize_value("", item)
                if not isinstance(item, dict)
                else {k: sanitize_value(k, v) for k, v in item.items()}
                for item in value
            ]
        return value

    return {key: sanitize_value(key, value) for key, value in data.items()}


class RunLogEntry(ErdosBaseModel):
    """A single run log entry."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,  # Allow datetime from ISO strings on load
        extra="allow",  # Allow extra fields for future extensions
    )

    schema_version: int = Field(default=LOG_SCHEMA_VERSION)
    id: str = Field(default_factory=generate_run_id)
    timestamp: datetime = Field(default_factory=utc_now)
    command: str
    args: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    success: bool
    problem_id: int | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    context: dict[str, Any] | None = None

    @classmethod
    def from_cli_output(
        cls,
        cli_output: CLIOutput,
        args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RunLogEntry:
        """Create a log entry from a CLIOutput.

        Args:
            cli_output: The CLI output to log
            args: Command arguments (will be sanitized)
            context: Optional environment context

        Returns:
            RunLogEntry ready to serialize
        """
        sanitized_args = cls._sanitize_args(args)
        problem_id = cls._extract_problem_id(sanitized_args, cli_output)
        result = cls._extract_result(cli_output)
        error = cls._extract_error(cli_output)

        return cls(
            timestamp=cli_output.timestamp,
            command=cli_output.command,
            args=sanitized_args,
            duration_ms=cli_output.duration_ms,
            success=cli_output.success,
            problem_id=problem_id,
            result=result,
            error=error,
            context=context,
        )

    @staticmethod
    def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive values from args, including nested structures."""
        return sanitize_secrets(args)

    @staticmethod
    def _extract_problem_id(args: dict[str, Any], cli_output: CLIOutput) -> int | None:
        """Extract problem_id from args or data."""
        # First check args
        if "problem_id" in args:
            val = args["problem_id"]
            if isinstance(val, int):
                return val

        # Then check data
        if cli_output.success and isinstance(cli_output.data, dict):
            if "id" in cli_output.data:
                val = cli_output.data["id"]
                if isinstance(val, int):
                    return val
            if "problem_id" in cli_output.data:
                val = cli_output.data["problem_id"]
                if isinstance(val, int):
                    return val

        return None

    @staticmethod
    def _extract_result(cli_output: CLIOutput) -> dict[str, Any] | None:
        """Extract command-specific result summary."""
        if not cli_output.success:
            return None

        data = cli_output.data
        if not isinstance(data, dict):
            return None

        return RunLogEntry._extract_result_for_command(cli_output.command, data)

    @staticmethod
    def _extract_result_for_command(
        command: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract result based on command type.

        Delegates to the summarizer registry for command-specific extraction.
        See run_logger_summaries.py for adding new command summarizers.
        """
        summarizer = get_summarizer(command)
        return summarizer(data)

    @staticmethod
    def _extract_error(cli_output: CLIOutput) -> dict[str, Any] | None:
        """Extract error details from failed output."""
        if cli_output.success:
            return None
        if cli_output.error is None:
            return None
        return {
            "type": cli_output.error.get("type"),
            "message": cli_output.error.get("message"),
        }


class RunLogger:
    """Handles logging and querying of run entries."""

    def __init__(self, log_file: Path | None = None) -> None:
        """Initialize the run logger.

        Args:
            log_file: Path to the log file. Defaults to ERDOS_RUN_LOG_PATH
                     env var or logs/runs.jsonl
        """
        if log_file is None:
            env_path = os.environ.get("ERDOS_RUN_LOG_PATH")
            log_file = Path(env_path) if env_path else DEFAULT_LOG_FILE
        self.log_file = log_file

    def log(
        self,
        cli_output: CLIOutput,
        args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RunLogEntry:
        """Log a CLI command invocation.

        Args:
            cli_output: The CLI output to log
            args: Command arguments
            context: Optional environment context

        Returns:
            The created log entry
        """
        entry = RunLogEntry.from_cli_output(cli_output, args, context)

        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Append to file
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

        logger.debug("Logged run entry: %s", entry.id)
        return entry

    def query(
        self,
        *,
        problem_id: int | None = None,
        command: str | None = None,
        since: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[RunLogEntry]:
        """Query log entries with optional filters.

        Args:
            problem_id: Filter by problem ID
            command: Filter by command name
            since: Filter by timestamp (e.g., '7d', '2h', ISO 8601)
            status: Filter by 'success' or 'failure'
            limit: Maximum entries to return

        Returns:
            List of matching entries, most recent first
        """
        if not self.log_file.exists():
            return []

        since_dt = parse_since(since) if since else None

        entries: list[RunLogEntry] = []
        with self.log_file.open(encoding="utf-8") as f:
            for raw_line in f:
                stripped_line = raw_line.strip()
                if not stripped_line:
                    continue
                try:
                    data = json.loads(stripped_line)
                    entry = RunLogEntry.model_validate(data)

                    # Apply filters
                    if problem_id is not None and entry.problem_id != problem_id:
                        continue
                    if command is not None and entry.command != command:
                        continue
                    if status == "success" and not entry.success:
                        continue
                    if status == "failure" and entry.success:
                        continue
                    if since_dt is not None and entry.timestamp < since_dt:
                        continue

                    entries.append(entry)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning("Skipping invalid log line: %s", e)
                    continue

        # Sort by timestamp descending (most recent first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        return entries[:limit]

    def summary(
        self,
        *,
        problem_id: int | None = None,
        command: str | None = None,
        since: str | None = None,
    ) -> dict[str, Any]:
        """Compute aggregated summary of log entries.

        Args:
            problem_id: Filter by problem ID
            command: Filter by command name
            since: Filter by timestamp

        Returns:
            Summary dict with by_command, by_problem, and metrics
        """
        # Get all matching entries (no limit for summary)
        entries = self.query(
            problem_id=problem_id,
            command=command,
            since=since,
            limit=100000,  # Effectively unlimited
        )

        by_command: dict[str, dict[str, int]] = {}
        by_problem: dict[str, dict[str, Any]] = {}
        problems_seen: set[int] = set()
        lean_pass = 0
        lean_fail = 0

        for entry in entries:
            # Aggregate by command
            cmd = entry.command
            if cmd not in by_command:
                by_command[cmd] = {"runs": 0, "success": 0, "failure": 0}
            by_command[cmd]["runs"] += 1
            if entry.success:
                by_command[cmd]["success"] += 1
            else:
                by_command[cmd]["failure"] += 1

            # Aggregate by problem
            if entry.problem_id is not None:
                pid = str(entry.problem_id)
                problems_seen.add(entry.problem_id)
                if pid not in by_problem:
                    by_problem[pid] = {"runs": 0, "last_success": None}
                by_problem[pid]["runs"] += 1
                if entry.success and by_problem[pid]["last_success"] is None:
                    by_problem[pid]["last_success"] = entry.timestamp.isoformat()

            # Track lean compile stats
            if "lean check" in cmd:
                if entry.success:
                    lean_pass += 1
                else:
                    lean_fail += 1

        # Compute period
        period_from = None
        period_to = None
        if entries:
            timestamps = [e.timestamp for e in entries]
            period_from = min(timestamps).isoformat()
            period_to = max(timestamps).isoformat()

        return {
            "period": {"from": period_from, "to": period_to},
            "total_runs": len(entries),
            "by_command": by_command,
            "by_problem": by_problem,
            "metrics": {
                "problems_attempted": len(problems_seen),
                "lean_compiles_passed": lean_pass,
                "lean_compiles_failed": lean_fail,
            },
        }


def get_run_logger() -> RunLogger:
    """Get a run logger instance configured from environment.

    Note: Creates a new instance each time to support env var changes in tests.
    The overhead is minimal since it's just path resolution.
    """
    return RunLogger()
