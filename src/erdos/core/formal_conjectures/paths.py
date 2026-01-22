"""Path helpers for cache and local file mapping."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Used at runtime

from erdos.core.formal_conjectures.config import (
    FORMAL_CONJECTURES_BASE_URL,
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
)


def build_upstream_url(problem_id: int, source: str = FORMAL_CONJECTURES_REPO) -> str:
    """Build URL to fetch upstream Lean file.

    Args:
        problem_id: Problem number
        source: Source repository (currently only formal-conjectures supported)

    Returns:
        URL to raw Lean file content
    """
    if source == FORMAL_CONJECTURES_REPO:
        return f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/{problem_id}.lean"
    raise FormalConjecturesError(f"Unknown source repository: {source}")


def get_cache_path(project_path: Path, problem_id: int) -> Path:
    """Get cache path for upstream Lean file.

    Args:
        project_path: Path to Lean project (e.g., formal/lean)
        problem_id: Problem number

    Returns:
        Path to cache file
    """
    return (
        project_path
        / ".upstream_cache"
        / "formal-conjectures"
        / "ErdosProblems"
        / f"{problem_id}.lean"
    )


def get_local_file_path(project_path: Path, problem_id: int) -> Path:
    """Get local Lean file path for a problem.

    Args:
        project_path: Path to Lean project (e.g., formal/lean)
        problem_id: Problem number

    Returns:
        Path to local Lean file (e.g., formal/lean/Erdos/Problem006.lean)
    """
    return project_path / "Erdos" / f"Problem{problem_id:03d}.lean"
