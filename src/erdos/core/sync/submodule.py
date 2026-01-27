"""Git submodule operations for teorth/erdosproblems (SPEC-035/3).

This module provides functions for:
- Loading problem data from the submodule (data/erdosproblems)
- Checking submodule staleness (behind remote)
- Updating the submodule to latest remote commit

All operations are designed for offline-first behavior:
- Cached data is used when network is unavailable
- Network is only required for update/check operations
"""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from erdos.core.config import AppConfig
from erdos.core.constants import GIT_FETCH_TIMEOUT, GIT_OP_TIMEOUT
from erdos.core.sync.models import SubmoduleProblemData, SubmoduleSyncStatus


logger = logging.getLogger(__name__)

# Default submodule path
DEFAULT_SUBMODULE_PATH = Path("data/erdosproblems")


# =============================================================================
# Exceptions
# =============================================================================


class SubmoduleError(Exception):
    """Base exception for submodule operations."""


class SubmoduleNotInitializedError(SubmoduleError):
    """Raised when submodule is not initialized."""


class SubmoduleFetchError(SubmoduleError):
    """Raised when submodule fetch fails (network error)."""


class SubmoduleCheckError(SubmoduleError):
    """Raised when staleness check fails."""


class SubmoduleTimeoutError(SubmoduleError):
    """Raised when a git operation times out."""


# =============================================================================
# Path utilities
# =============================================================================


def get_submodule_path(config: AppConfig | None = None) -> Path:
    """
    Get the submodule path.

    Respects ERDOS_SUBMODULE_PATH environment variable for override (via AppConfig).

    Args:
        config: Optional AppConfig; if None, uses AppConfig.from_env()

    Returns:
        Path to submodule directory
    """
    if config is None:
        config = AppConfig.from_env()
    if config.submodule_path:
        return config.submodule_path
    return DEFAULT_SUBMODULE_PATH


def _get_problems_yaml_path(submodule_path: Path) -> Path:
    """Get path to problems.yaml within submodule."""
    return submodule_path / "data" / "problems.yaml"


# =============================================================================
# Git operations
# =============================================================================


def _is_submodule_initialized(submodule_path: Path) -> bool:
    """Check if submodule directory exists and appears initialized."""
    if not submodule_path.exists():
        return False
    # Check for .git file (submodules have a .git file, not directory)
    git_path = submodule_path / ".git"
    return git_path.exists()


def get_submodule_commit(submodule_path: Path) -> str:
    """
    Get current commit hash of the submodule.

    Args:
        submodule_path: Path to submodule directory

    Returns:
        Commit hash (full SHA)

    Raises:
        SubmoduleNotInitializedError: If submodule not initialized
        SubmoduleError: If git command fails
    """
    if not _is_submodule_initialized(submodule_path):
        raise SubmoduleNotInitializedError(
            f"Submodule at {submodule_path} is not initialized. "
            "Run: git submodule update --init --recursive"
        )

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_OP_TIMEOUT,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired as e:
        raise SubmoduleTimeoutError(
            f"Git rev-parse timed out after {GIT_OP_TIMEOUT}s for {submodule_path}"
        ) from e
    except subprocess.CalledProcessError as e:
        raise SubmoduleError(
            f"Failed to get commit hash for {submodule_path}: {e.stderr}"
        ) from e


def check_submodule_staleness(submodule_path: Path) -> bool:
    """
    Check if submodule is behind remote.

    This performs a network fetch to check for updates.

    Args:
        submodule_path: Path to submodule directory

    Returns:
        True if submodule is stale (behind remote), False if up-to-date

    Raises:
        SubmoduleCheckError: If check fails (network error)
    """
    if not _is_submodule_initialized(submodule_path):
        raise SubmoduleNotInitializedError(
            f"Submodule at {submodule_path} is not initialized"
        )

    try:
        # Fetch from remote
        subprocess.run(
            ["git", "fetch", "origin"],  # noqa: S607
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_FETCH_TIMEOUT,
        )

        # Count commits we're behind
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],  # noqa: S607
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_OP_TIMEOUT,
        )

        behind_count = int(result.stdout.strip())
        return behind_count > 0

    except subprocess.TimeoutExpired as e:
        raise SubmoduleTimeoutError(
            f"Git operation timed out for {submodule_path}: {e.cmd}"
        ) from e
    except subprocess.CalledProcessError as e:
        raise SubmoduleCheckError(
            f"Failed to check submodule staleness (network/fetch error): {e.stderr}"
        ) from e
    except ValueError as e:
        raise SubmoduleCheckError(f"Failed to parse commit count: {e}") from e


def update_submodule(
    submodule_path: Path,
    *,
    check_only: bool = False,
) -> SubmoduleSyncStatus:
    """
    Update submodule to latest remote commit.

    Args:
        submodule_path: Path to submodule directory
        check_only: If True, only check staleness without updating

    Returns:
        SubmoduleSyncStatus with update details

    Raises:
        SubmoduleNotInitializedError: If submodule not initialized
        SubmoduleFetchError: If fetch/update fails
        SubmoduleTimeoutError: If a git operation times out
    """
    if not _is_submodule_initialized(submodule_path):
        raise SubmoduleNotInitializedError(
            f"Submodule at {submodule_path} is not initialized. "
            "Run: git submodule update --init --recursive"
        )

    previous_commit = get_submodule_commit(submodule_path)

    if check_only:
        # Check staleness without updating
        try:
            is_stale = check_submodule_staleness(submodule_path)
            return SubmoduleSyncStatus(
                commit_hash=previous_commit,
                previous_commit_hash=previous_commit,
                synced_at=datetime.now(UTC),
                stale=is_stale,
            )
        except SubmoduleCheckError as e:
            raise SubmoduleFetchError(str(e)) from e

    # Perform update
    try:
        # Fetch updates
        subprocess.run(
            ["git", "fetch", "origin"],  # noqa: S607
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_FETCH_TIMEOUT,
        )

        # Checkout latest
        subprocess.run(
            ["git", "checkout", "origin/main"],  # noqa: S607
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_OP_TIMEOUT,
        )

    except subprocess.TimeoutExpired as e:
        raise SubmoduleTimeoutError(
            f"Git operation timed out for {submodule_path}: {e.cmd}"
        ) from e
    except subprocess.CalledProcessError as e:
        raise SubmoduleFetchError(
            f"Failed to update submodule (network/fetch error): {e.stderr}"
        ) from e

    current_commit = get_submodule_commit(submodule_path)

    return SubmoduleSyncStatus(
        commit_hash=current_commit,
        previous_commit_hash=previous_commit,
        synced_at=datetime.now(UTC),
        stale=False,  # Just updated, so not stale
    )


# =============================================================================
# Data loading
# =============================================================================


def parse_problems_yaml(data: list[dict[str, Any]]) -> dict[int, SubmoduleProblemData]:
    """
    Parse problems.yaml data into SubmoduleProblemData objects.

    Args:
        data: List of raw problem dicts from YAML

    Returns:
        Dict mapping problem_id to SubmoduleProblemData
    """
    result: dict[int, SubmoduleProblemData] = {}

    for item in data:
        try:
            problem = SubmoduleProblemData.from_upstream_yaml(item)
            result[problem.problem_id] = problem
        except (ValueError, KeyError, TypeError) as e:
            # Skip invalid entries but log warning
            number = (
                item.get("number", "unknown") if isinstance(item, dict) else "unknown"
            )
            logger.warning("Skipping invalid problem entry %s: %s", number, e)
            continue

    return result


def load_submodule_problems(
    submodule_path: Path | None = None,
) -> dict[int, SubmoduleProblemData]:
    """
    Load all problems from the submodule.

    Args:
        submodule_path: Path to submodule (uses default if None)

    Returns:
        Dict mapping problem_id to SubmoduleProblemData

    Raises:
        SubmoduleError: If problems.yaml not found or invalid
    """
    if submodule_path is None:
        submodule_path = get_submodule_path()

    problems_path = _get_problems_yaml_path(submodule_path)

    if not problems_path.exists():
        raise SubmoduleError(
            f"problems.yaml not found at {problems_path}. "
            "Ensure submodule is initialized: git submodule update --init --recursive"
        )

    try:
        with problems_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SubmoduleError(f"Failed to parse problems.yaml: {e}") from e

    if not isinstance(data, list):
        raise SubmoduleError(
            f"problems.yaml has unexpected format (expected list, got {type(data).__name__})"
        )

    return parse_problems_yaml(data)
