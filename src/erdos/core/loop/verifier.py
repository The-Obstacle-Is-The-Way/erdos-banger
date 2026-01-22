"""Loop verification for sorry/admit tracking.

Per spec-012-design.md D3: Sorry Spam Prevention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class LoopExitCondition(Enum):
    """Exit conditions for the loop."""

    SUCCESS = auto()  # compiles, no sorry/admit, file size OK
    CONTINUE = auto()  # making progress, continue loop
    STALLED = auto()  # no progress this iteration
    MAX_ITERATIONS = auto()  # hard limit reached
    REGRESSION = auto()  # file shrank (abort immediately)
    NO_FIX_POSSIBLE = auto()  # LLM indicated no fix


def count_sorries(text: str) -> int:
    """Count sorry occurrences in text.

    Uses word boundaries to avoid matching partial words.

    Args:
        text: Lean code text

    Returns:
        Number of sorry occurrences
    """
    pattern = re.compile(r"\bsorry\b")
    return len(pattern.findall(text))


def count_admits(text: str) -> int:
    """Count admit occurrences in text.

    Uses word boundaries to avoid matching partial words.

    Args:
        text: Lean code text

    Returns:
        Number of admit occurrences
    """
    pattern = re.compile(r"\badmit\b")
    return len(pattern.findall(text))


@dataclass
class LoopVerification:
    """Verification result for a loop iteration.

    Tracks compilation status, sorry/admit counts, and file size
    to determine if progress was made and if the proof is complete.

    Per spec-012-design.md D3:
    Success requires ALL of:
    1. Lean compilation succeeds (exit 0)
    2. Final file contains zero sorry keywords
    3. Final file contains zero admit keywords
    4. File size did not shrink by > 20%
    """

    compiles: bool
    sorry_count_before: int
    sorry_count_after: int
    admit_count_before: int
    admit_count_after: int
    file_size_before: int
    file_size_after: int
    min_file_size_ratio: float = 0.8

    @property
    def sorry_delta(self) -> int:
        """Change in sorry count (negative = improvement)."""
        return self.sorry_count_after - self.sorry_count_before

    @property
    def admit_delta(self) -> int:
        """Change in admit count (negative = improvement)."""
        return self.admit_count_after - self.admit_count_before

    @property
    def _file_size_ok(self) -> bool:
        """Check if file size is within acceptable range."""
        if self.file_size_before == 0:
            return True
        return self.file_size_after >= self.file_size_before * self.min_file_size_ratio

    @property
    def is_success(self) -> bool:
        """True if proof is complete (no sorry/admit, compiles, size OK)."""
        return (
            self.compiles
            and self.sorry_count_after == 0
            and self.admit_count_after == 0
            and self._file_size_ok
        )

    @property
    def is_progress(self) -> bool:
        """True if we made forward progress (even if not complete)."""
        return self.compiles and self.sorry_delta < 0

    @property
    def exit_condition(self) -> LoopExitCondition:
        """Determine the appropriate exit condition."""
        # Check for regression first (file shrinkage)
        if not self._file_size_ok:
            return LoopExitCondition.REGRESSION

        # Check for success
        if self.is_success:
            return LoopExitCondition.SUCCESS

        # Check for progress
        if self.is_progress:
            return LoopExitCondition.CONTINUE

        # No progress
        return LoopExitCondition.STALLED
