"""Provenance persistence helpers for proof sync/verification (SPEC-035)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from erdos.core.sync.models import ProofLink, ProofProvenance, VerificationStatus


if TYPE_CHECKING:
    from erdos.core.sync.proofs_types import VerificationResult


DEFAULT_CACHE_PATH = Path("data/sync_cache/proofs")


def create_provenance(
    problem_id: int,
    link: ProofLink,
    verification: VerificationResult | None = None,
) -> ProofProvenance:
    """Create a provenance record for a proof."""
    now = datetime.now(UTC)

    if verification is None:
        return ProofProvenance(
            problem_id=problem_id,
            forum_thread_url=f"https://www.erdosproblems.com/forum/thread/{problem_id}",
            extracted_at=now,
            repo_url=link.url,
            posted_by=link.author,
            posted_at=link.posted_at,
        )

    return ProofProvenance(
        problem_id=problem_id,
        forum_thread_url=f"https://www.erdosproblems.com/forum/thread/{problem_id}",
        extracted_at=now,
        repo_url=link.url,
        repo_commit=verification.repo_commit,
        posted_by=link.author,
        posted_at=link.posted_at,
        verification_status=verification.status,
        verification_strength=verification.strength,
        verification_error=verification.error,
        verified_at=now
        if verification.status != VerificationStatus.UNVERIFIED
        else None,
        verification_command=verification.verification_command,
        toolchain=verification.toolchain,
        verified_files=verification.verified_files,
    )


def save_provenance(
    provenance: ProofProvenance,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Save provenance record to disk.

    Creates: <cache_dir>/<problem_id>/provenance.json
    """
    resolved_cache_dir = DEFAULT_CACHE_PATH if cache_dir is None else cache_dir

    problem_dir = resolved_cache_dir / str(provenance.problem_id)
    problem_dir.mkdir(parents=True, exist_ok=True)

    output_path = problem_dir / "provenance.json"
    data = provenance.model_dump(mode="json")

    tmp_path = output_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp_path.replace(output_path)

    return output_path


def save_verification_log(
    problem_id: int,
    log_content: str,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Save verification log to disk.

    Creates: <cache_dir>/<problem_id>/verify.log
    """
    resolved_cache_dir = DEFAULT_CACHE_PATH if cache_dir is None else cache_dir

    problem_dir = resolved_cache_dir / str(problem_id)
    problem_dir.mkdir(parents=True, exist_ok=True)

    output_path = problem_dir / "verify.log"

    tmp_path = output_path.with_suffix(".log.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        f.write(log_content)
    tmp_path.replace(output_path)

    return output_path
