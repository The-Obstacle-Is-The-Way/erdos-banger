"""Shared dataclasses for proof verification (SPEC-035)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.sync.models import VerificationStatus, VerificationStrength


@dataclass
class VerificationResult:
    """Result of verifying a proof repository."""

    status: VerificationStatus
    strength: VerificationStrength
    error: str | None = None
    repo_commit: str | None = None
    toolchain: str | None = None
    verified_files: list[str] = field(default_factory=list)
    log_content: str = ""
    verification_command: str | None = None


@dataclass
class CloneResult:
    """Result of cloning a repository."""

    success: bool
    path: Path | None = None
    commit: str | None = None
    error: str | None = None
