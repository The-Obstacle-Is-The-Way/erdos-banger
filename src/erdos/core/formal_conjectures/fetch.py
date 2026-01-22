"""Fetch and cache remote Lean files."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - Used at runtime

import requests

from erdos.core.formal_conjectures.config import FormalConjecturesError
from erdos.core.formal_conjectures.paths import build_upstream_url, get_cache_path
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of fetching upstream Lean file."""

    content: str
    sha256: str
    url: str
    etag: str | None = None
    from_cache: bool = False


def fetch_upstream_lean_file(
    project_path: Path,
    problem_id: int,
    *,
    source_url: str | None = None,
    no_network: bool = False,
) -> FetchResult:
    """Fetch upstream Lean file, using cache if available.

    Args:
        project_path: Path to Lean project
        problem_id: Problem number
        source_url: Override source URL (default: derived from formal-conjectures)
        no_network: If True, only use cached file

    Returns:
        FetchResult with content and metadata

    Raises:
        FormalConjecturesError: On network error or if no_network and not cached
    """
    cache_path = get_cache_path(project_path, problem_id)
    url = source_url or build_upstream_url(problem_id)

    # Try cache first
    if cache_path.exists():
        logger.debug("Using cached file: %s", cache_path)
        # Read bytes once, decode for content and hash for sha256
        content_bytes = cache_path.read_bytes()
        content = content_bytes.decode("utf-8")
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        return FetchResult(
            content=content,
            sha256=sha256,
            url=url,
            from_cache=True,
        )

    if no_network:
        raise FormalConjecturesError(
            f"Upstream file for problem {problem_id} is not cached and --no-network is set",
            error_type="NetworkError",
        )

    # Fetch from network
    logger.debug("Fetching upstream file: %s", url)
    try:
        response = fetch_with_retry(url, timeout=30)
    except requests.RequestException as e:
        raise FormalConjecturesError(
            f"Failed to fetch upstream file: {e}",
            error_type="NetworkError",
        ) from e

    if response.status_code != 200:
        raise FormalConjecturesError(
            f"HTTP {response.status_code} fetching {url}",
            error_type="NetworkError",
        )

    content_bytes = response.content
    content = content_bytes.decode("utf-8")
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    etag = response.headers.get("ETag")

    # Write to cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(content_bytes)
    logger.debug("Cached upstream file: %s", cache_path)

    return FetchResult(
        content=content,
        sha256=sha256,
        url=url,
        etag=etag,
        from_cache=False,
    )
