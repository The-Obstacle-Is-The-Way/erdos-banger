"""Loop result types and data structures.

Per spec-012-loop-command.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.models import LeanCheckResult


class LoopStatus(str, Enum):
    """Status of a loop execution."""

    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"
    NO_PROGRESS = "no_progress"
    NO_FIX_POSSIBLE = "no_fix_possible"
    REGRESSION = "regression"
    LLM_REQUIRED = "llm_required"
    ERROR = "error"


@dataclass
class IterationRecord:
    """Record of a single loop iteration."""

    iteration: int
    patch_applied: bool
    sorry_before: int = 0
    sorry_after: int = 0
    admit_before: int = 0
    admit_after: int = 0
    check_success: bool = False
    error_count: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "iteration": self.iteration,
            "patch_applied": self.patch_applied,
            "sorry_before": self.sorry_before,
            "sorry_after": self.sorry_after,
            "admit_before": self.admit_before,
            "admit_after": self.admit_after,
            "check_success": self.check_success,
            "error_count": self.error_count,
            "reason": self.reason if self.reason else None,
        }


@dataclass
class LoopResult:
    """Result of a loop execution."""

    problem_id: int
    status: LoopStatus
    iterations_completed: int
    iterations_max: int
    file: Path
    no_apply: bool
    llm_enabled: bool
    llm_command: str | None
    run_log_path: Path | None
    last_check: LeanCheckResult | None
    iterations: list[IterationRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        last_check_dict = None
        if self.last_check is not None:
            last_check_dict = {
                "success": self.last_check.success,
                "error_count": len(self.last_check.errors),
                # has_sorry/has_admit are None (unknown) - LeanCheckResult doesn't track these.
                # Callers should compute from file content if needed.
                "has_sorry": None,
                "has_admit": None,
            }

        return {
            "problem_id": self.problem_id,
            "status": self.status.value,
            "iterations_completed": self.iterations_completed,
            "iterations_max": self.iterations_max,
            "file": str(self.file),
            "no_apply": self.no_apply,
            "llm": {
                "enabled": self.llm_enabled,
                "command": self.llm_command,
            },
            "run_log_path": str(self.run_log_path) if self.run_log_path else None,
            "last_check": last_check_dict,
            "iterations": [it.to_dict() for it in self.iterations],
        }
