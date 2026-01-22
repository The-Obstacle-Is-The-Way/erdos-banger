"""Loop logging utilities.

Per spec-012-loop-command.md section 4.1 (Run Log File).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TextIO

from erdos.core.run_logger import sanitize_secrets


if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType


def generate_run_id() -> str:
    """Generate a unique run ID."""
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_suffix = secrets.token_hex(3)  # 6 hex chars, cryptographically secure
    return f"run_{timestamp}_{random_suffix}"


def file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file content for logging/cache purposes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LoopLogger:
    """JSON Lines logger for loop iterations.

    Logs events to a JSONL file with automatic secret sanitization.
    Schema version 1 per spec-012-loop-command.md.

    Supports context manager protocol for safe resource management:
        with LoopLogger(log_path) as logger:
            logger.log_event(...)
    """

    def __init__(self, log_path: Path) -> None:
        """Initialize the logger.

        Args:
            log_path: Path to the JSONL log file.
        """
        self.log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO = log_path.open("a", encoding="utf-8")

    def __enter__(self) -> LoopLogger:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, ensuring file is closed."""
        self.close()

    def log_event(self, event: str, iteration: int, data: dict[str, Any]) -> None:
        """Log an event to the run log.

        Data is sanitized to redact secrets (API keys, tokens, Authorization headers).

        Args:
            event: Event type (e.g., 'llm_prompt', 'llm_response', 'patch_applied').
            iteration: Current iteration number.
            data: Event-specific data to log.
        """
        entry = {
            "schema_version": 1,
            "iteration": iteration,
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": sanitize_secrets(data),
        }
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        if not self._file.closed:
            self._file.close()
