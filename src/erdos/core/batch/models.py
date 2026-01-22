"""Batch operation data models (SPEC-015).

Contains dataclasses for batch state, filters, progress, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from erdos.core.exit_codes import ExitCode
from erdos.core.models import ProblemStatus


if TYPE_CHECKING:
    from erdos.core.models import ProblemRecord

# Schema version for batch state files
SCHEMA_VERSION = 1


@dataclass
class BatchFilters:
    """Filters for selecting problems in batch operations."""

    status: str | None = None
    prize_min: int | None = None
    prize_max: int | None = None
    tags: list[str] | None = None
    limit: int | None = None
    skip: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status,
            "prize_min": self.prize_min,
            "prize_max": self.prize_max,
            "tags": self.tags,
            "limit": self.limit,
            "skip": self.skip,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BatchFilters:
        """Create from dictionary."""
        return cls(
            status=d.get("status"),
            prize_min=d.get("prize_min"),
            prize_max=d.get("prize_max"),
            tags=d.get("tags"),
            limit=d.get("limit"),
            skip=d.get("skip"),
        )

    def matches(self, other: BatchFilters) -> bool:
        """Check if filters match (for resume validation)."""
        # Use set comparison for tags to ignore ordering differences
        self_tags = set(self.tags) if self.tags else set()
        other_tags = set(other.tags) if other.tags else set()
        return (
            self.status == other.status
            and self.prize_min == other.prize_min
            and self.prize_max == other.prize_max
            and self_tags == other_tags
            # limit/skip not compared since they may differ on resume
        )


def filter_problem_ids(
    problems: list[ProblemRecord], filters: BatchFilters
) -> list[int]:
    """Filter problems by criteria and return matching IDs.

    Args:
        problems: List of ProblemRecord objects
        filters: Filter criteria to apply

    Returns:
        List of matching problem IDs
    """
    results: list[int] = []

    for problem in problems:
        # Filter by status
        if filters.status is not None:
            expected_status = ProblemStatus.from_string(filters.status)
            if problem.status != expected_status:
                continue

        # Filter by prize range
        if filters.prize_min is not None and problem.prize < filters.prize_min:
            continue
        if filters.prize_max is not None and problem.prize > filters.prize_max:
            continue

        # Filter by tags (any match, case insensitive)
        if filters.tags:
            tag_set = {t.lower() for t in filters.tags}
            problem_tags = {t.lower() for t in problem.tags}
            if not tag_set.intersection(problem_tags):
                continue

        results.append(problem.id)

    # Apply skip/limit after filtering
    # Use explicit None check so skip=0 and limit=0 work correctly
    if filters.skip is not None:
        results = results[filters.skip :]
    if filters.limit is not None:
        results = results[: filters.limit]

    return results


@dataclass
class BatchState:
    """State of a batch operation for persistence and resume."""

    batch_id: str
    command: str
    filters: BatchFilters
    problem_ids: list[int]
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed: list[int] = field(default_factory=list)
    failed: list[int] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def pending(self) -> list[int]:
        """Return IDs that haven't been processed yet."""
        processed = set(self.completed) | set(self.failed)
        return [pid for pid in self.problem_ids if pid not in processed]

    @property
    def is_complete(self) -> bool:
        """Return True if all problems have been processed."""
        return len(self.pending) == 0

    def mark_completed(self, problem_id: int) -> None:
        """Mark a problem as successfully completed."""
        if problem_id not in self.completed:
            self.completed.append(problem_id)
        # Remove from failed if present (on retry success)
        if problem_id in self.failed:
            self.failed.remove(problem_id)
        self.last_updated = datetime.now(tz=UTC)

    def mark_failed(self, problem_id: int) -> None:
        """Mark a problem as failed."""
        # Remove from completed if present (on retry failure after previous success)
        if problem_id in self.completed:
            self.completed.remove(problem_id)
        if problem_id not in self.failed:
            self.failed.append(problem_id)
        self.last_updated = datetime.now(tz=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "schema_version": SCHEMA_VERSION,
            "batch_id": self.batch_id,
            "command": self.command,
            "filters": self.filters.to_dict(),
            "started_at": self.started_at.isoformat(),
            "problem_ids": self.problem_ids,
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.pending,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BatchState:
        """Create from dictionary.

        Raises:
            ValueError: If schema_version is unsupported
        """
        schema_version = d.get("schema_version", 1)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version {schema_version}, expected {SCHEMA_VERSION}"
            )

        started_at = d.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        else:
            started_at = datetime.now(tz=UTC)

        last_updated = d.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        else:
            last_updated = datetime.now(tz=UTC)

        return cls(
            batch_id=d["batch_id"],
            command=d["command"],
            filters=BatchFilters.from_dict(d.get("filters", {})),
            problem_ids=d["problem_ids"],
            started_at=started_at,
            completed=d.get("completed", []),
            failed=d.get("failed", []),
            last_updated=last_updated,
        )


@dataclass
class BatchProgress:
    """Progress update for batch operations."""

    problem_id: int
    index: int
    total: int
    success: bool
    message: str


@dataclass
class BatchResult:
    """Result of a batch operation."""

    batch_id: str
    total: int
    completed_count: int
    failed_count: int
    failed_ids: list[int]
    duration_ms: int
    dry_run: bool = False
    exit_code: ExitCode = ExitCode.SUCCESS
    error_message: str = ""

    @property
    def success(self) -> bool:
        """Return True if all problems succeeded (no failures)."""
        return self.failed_count == 0 and self.exit_code == ExitCode.SUCCESS
