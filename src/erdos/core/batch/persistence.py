"""Batch state persistence (save/load operations).

Handles serialization and deserialization of batch state to JSON files.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from erdos.core.batch.models import BatchState


logger = logging.getLogger(__name__)


def generate_batch_id() -> str:
    """Generate a unique batch ID based on current timestamp.

    Returns:
        Batch ID in format: batch_YYYYMMDD_HHMMSS_ffffff (includes microseconds)
    """
    now = datetime.now(tz=UTC)
    return f"batch_{now.strftime('%Y%m%d_%H%M%S_%f')}"


def save_batch_state(path: Path, state: BatchState) -> None:
    """Save batch state to JSON file.

    Args:
        path: Path to save state file
        state: BatchState to save
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    logger.debug("Saved batch state to %s", path)


def load_batch_state(path: Path) -> BatchState:
    """Load batch state from JSON file.

    Args:
        path: Path to state file

    Returns:
        BatchState loaded from file

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        ValueError: If schema_version is unsupported
    """
    content = path.read_text(encoding="utf-8")
    d = json.loads(content)
    return BatchState.from_dict(d)


def save_latest_batch_id(path: Path, batch_id: str) -> None:
    """Save latest batch ID to pointer file.

    Args:
        path: Path to latest.json file
        batch_id: Batch ID to save
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"batch_id": batch_id}), encoding="utf-8")


def load_latest_batch_id(path: Path) -> str:
    """Load latest batch ID from pointer file.

    Args:
        path: Path to latest.json file

    Returns:
        Batch ID string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    content = path.read_text(encoding="utf-8")
    d: dict[str, Any] = json.loads(content)
    batch_id: str = d["batch_id"]
    return batch_id
