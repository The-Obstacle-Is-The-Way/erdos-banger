"""Parse upstream formalization metadata from teorth/erdosproblems."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - Used at runtime
from typing import Any

import yaml

from erdos.core.formal_conjectures.config import (
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
)
from erdos.core.formal_conjectures.paths import build_upstream_url


@dataclass(frozen=True)
class UpstreamFormalizationInfo:
    """Information about upstream formalization status."""

    problem_id: int
    formalized: bool
    state: str | None = None
    last_update: str | None = None
    source: str = FORMAL_CONJECTURES_REPO
    url: str | None = None


def parse_upstream_formalization_status(
    metadata: dict[str, Any],
) -> UpstreamFormalizationInfo:
    """Parse formalization status from upstream metadata entry.

    Args:
        metadata: Single problem entry from upstream problems.yaml

    Returns:
        UpstreamFormalizationInfo with formalized status
    """
    problem_id = int(metadata.get("number", 0))
    formalized_data = metadata.get("formalized")

    if formalized_data is None or not isinstance(formalized_data, dict):
        return UpstreamFormalizationInfo(
            problem_id=problem_id,
            formalized=False,
            state=None,
        )

    state = formalized_data.get("state")
    last_update = formalized_data.get("last_update")
    formalized = state == "yes"

    return UpstreamFormalizationInfo(
        problem_id=problem_id,
        formalized=formalized,
        state=state,
        last_update=last_update,
        url=build_upstream_url(problem_id) if formalized else None,
    )


def load_upstream_metadata(yaml_path: Path) -> dict[int, UpstreamFormalizationInfo]:
    """Load upstream formalization metadata from problems.yaml.

    Args:
        yaml_path: Path to upstream problems.yaml (e.g., data/erdosproblems/data/problems.yaml)

    Returns:
        Dict mapping problem_id to UpstreamFormalizationInfo

    Raises:
        FormalConjecturesError: If file not found or invalid
    """
    if not yaml_path.exists():
        raise FormalConjecturesError(
            f"Upstream metadata file not found: {yaml_path}",
            error_type="ConfigError",
        )

    try:
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise FormalConjecturesError(
            f"Failed to parse upstream metadata: {e}",
            error_type="ParseError",
        ) from e

    if not isinstance(data, list):
        raise FormalConjecturesError(
            f"Expected list of problems, got {type(data).__name__}",
            error_type="ParseError",
        )

    result: dict[int, UpstreamFormalizationInfo] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        info = parse_upstream_formalization_status(item)
        if info.problem_id > 0:
            result[info.problem_id] = info

    return result
