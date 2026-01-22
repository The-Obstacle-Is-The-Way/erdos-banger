"""ArXiv source download and text extraction.

This module handles:
- Downloading arXiv source tarballs with retry logic
- Caching downloaded tarballs to the literature cache
- Extracting LaTeX text from tarballs

Isolated for testability - can be unit tested with in-memory tarballs.
"""

from __future__ import annotations

import hashlib
import logging
import tarfile
import time
from typing import TYPE_CHECKING

import requests

from erdos.core.clients.arxiv import extract_arxiv_text
from erdos.core.ingest.models import ArxivDownloadResult
from erdos.core.literature_paths import (
    get_arxiv_cache_path,
    get_arxiv_extract_path,
)
from erdos.core.retry import fetch_with_retry


if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


def download_and_extract_arxiv(
    arxiv_id: str,
    repo_root: Path,
    timeout: float,
) -> ArxivDownloadResult:
    """Download arXiv source tarball and extract text.

    This is the single implementation used by both DOI+arXiv and arXiv-only paths.

    Args:
        arxiv_id: arXiv identifier (e.g., "2203.00001").
        repo_root: Repository root directory.
        timeout: HTTP timeout in seconds.

    Returns:
        ArxivDownloadResult with cache/extract paths or error.
    """
    cache_path = None
    cache_hash = None
    extract_path = None
    extracted = False
    error = None

    try:
        arxiv_cache_path = repo_root / get_arxiv_cache_path(arxiv_id)
        arxiv_extract_path = repo_root / get_arxiv_extract_path(arxiv_id)

        # Download source with retry for transient failures
        source_url = f"https://arxiv.org/e-print/{arxiv_id}"
        logger.debug("Downloading arXiv source: %s", source_url)
        start_time = time.monotonic()
        response = fetch_with_retry(source_url, timeout=timeout)
        elapsed = time.monotonic() - start_time
        logger.debug(
            "arXiv download: %d bytes in %.2fs (status %d)",
            len(response.content),
            elapsed,
            response.status_code,
        )
        tarball_bytes = response.content

        # Write cache
        arxiv_cache_path.parent.mkdir(parents=True, exist_ok=True)
        arxiv_cache_path.write_bytes(tarball_bytes)
        logger.debug("Cached arXiv source: %s", arxiv_cache_path)

        # Compute hash (SHA256 for cache integrity, not crypto)
        cache_hash = hashlib.sha256(tarball_bytes).hexdigest()
        cache_path = get_arxiv_cache_path(arxiv_id)

        # Extract text
        try:
            text_bytes = extract_arxiv_text(tarball_bytes)
            text = text_bytes.decode("utf-8", errors="replace")
            arxiv_extract_path.parent.mkdir(parents=True, exist_ok=True)
            arxiv_extract_path.write_text(text, encoding="utf-8")
            extract_path = get_arxiv_extract_path(arxiv_id)
            extracted = True
            logger.debug(
                "Extracted arXiv text: %s (%d chars)", arxiv_extract_path, len(text)
            )
        except (OSError, ValueError, tarfile.TarError) as e:
            logger.warning("arXiv extraction failed for %s: %s", arxiv_id, e)
            error = f"Extraction failed: {e}"
            extracted = False
    except (OSError, requests.RequestException) as e:
        logger.warning("arXiv download failed for %s: %s", arxiv_id, e)
        error = f"Download failed: {e}"

    return ArxivDownloadResult(
        cache_path=cache_path,
        cache_hash=cache_hash,
        extract_path=extract_path,
        extracted=extracted,
        error=error,
    )
