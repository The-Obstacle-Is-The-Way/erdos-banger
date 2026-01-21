"""Reference fetching and download logic."""

from __future__ import annotations

import hashlib
import logging
import tarfile
import time
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

import defusedxml.ElementTree as ET
import requests

from erdos.core.arxiv_client import (
    extract_arxiv_text,
    fetch_arxiv_atom,
    parse_arxiv_atom,
)
from erdos.core.crossref_client import fetch_crossref_work, parse_crossref_work
from erdos.core.ingest.models import (
    ArxivDownloadResult,
    ProcessAllReferencesResult,
    ReferenceProcessResult,
)
from erdos.core.ingest.stable_key import get_stable_key
from erdos.core.literature_paths import (
    get_arxiv_cache_path,
    get_arxiv_extract_path,
)
from erdos.core.models import (
    ManifestEntry,
    ProblemManifest,
    ProblemRecord,
    ReferenceEntry,
    ReferenceRecord,
)
from erdos.core.openalex_client import OpenAlexClient, OpenAlexConfig
from erdos.core.retry import fetch_with_retry


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.ports import MetadataProvider


logger = logging.getLogger(__name__)


class MetadataSource(str, Enum):
    """Metadata source for reference ingestion."""

    OPENALEX = "openalex"
    ARXIV = "arxiv"
    CROSSREF = "crossref"


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


def _find_existing_manifest_entry(
    ref: ReferenceEntry,
    existing_manifest: ProblemManifest | None,
    *,
    force: bool,
) -> ManifestEntry | None:
    """Return an existing manifest entry for this reference, if available."""
    if existing_manifest is None or force:
        return None
    stable_key = get_stable_key(ref)
    for entry in existing_manifest.entries:
        if get_stable_key(entry.reference) == stable_key:
            return entry
    return None


def _error_manifest_entry(
    ref: ReferenceEntry, *, title: str, error: str
) -> ManifestEntry:
    """Create a manifest entry representing a failed ingestion attempt."""
    return ManifestEntry(
        reference=ReferenceRecord(
            doi=ref.doi,
            arxiv_id=ref.arxiv_id,
            title=title,
            authors=[],
            source="error",
        ),
        error=error,
        ingested_at=datetime.now(UTC),
    )


def _build_manifest_entry_with_arxiv(
    reference: ReferenceRecord,
    arxiv_id: str,
    *,
    repo_root: Path,
    allow_download: bool,
    timeout: float,
) -> ManifestEntry:
    """Build a ManifestEntry with optional arXiv download.

    Args:
        reference: Reference metadata (already fetched)
        arxiv_id: arXiv identifier for downloading
        repo_root: Repository root directory
        allow_download: Whether to download arXiv source
        timeout: HTTP timeout in seconds

    Returns:
        ManifestEntry with cache/extract info if downloaded
    """
    if not allow_download:
        return ManifestEntry(reference=reference, ingested_at=datetime.now(UTC))

    download_result = download_and_extract_arxiv(
        arxiv_id=arxiv_id,
        repo_root=repo_root,
        timeout=timeout,
    )
    return ManifestEntry(
        reference=reference,
        cached=download_result.cache_path is not None,
        cache_path=download_result.cache_path,
        cache_hash=download_result.cache_hash,
        extracted=download_result.extracted,
        extract_path=download_result.extract_path,
        ingested_at=datetime.now(UTC),
        error=download_result.error,
    )


def _fetch_doi_with_arxiv(
    doi: str,
    arxiv_id: str,
    *,
    mailto: str,
    timeout: float,
    repo_root: Path,
    allow_download: bool,
) -> ManifestEntry:
    """Fetch DOI metadata and optionally download arXiv source."""
    crossref_data = fetch_crossref_work(doi, mailto=mailto, timeout=timeout)
    reference = parse_crossref_work(crossref_data, doi=doi)
    reference.arxiv_id = arxiv_id
    return _build_manifest_entry_with_arxiv(
        reference,
        arxiv_id,
        repo_root=repo_root,
        allow_download=allow_download,
        timeout=timeout,
    )


def _fetch_doi_only(doi: str, *, mailto: str, timeout: float) -> ManifestEntry:
    """Fetch DOI metadata without arXiv download."""
    crossref_data = fetch_crossref_work(doi, mailto=mailto, timeout=timeout)
    reference = parse_crossref_work(crossref_data, doi=doi)
    return ManifestEntry(reference=reference, ingested_at=datetime.now(UTC))


def _fetch_arxiv_only(
    arxiv_id: str,
    *,
    timeout: float,
    repo_root: Path,
    allow_download: bool,
) -> ManifestEntry:
    """Fetch arXiv metadata and optionally download source."""
    arxiv_atom = fetch_arxiv_atom(arxiv_id, timeout=timeout)
    reference = parse_arxiv_atom(arxiv_atom)
    return _build_manifest_entry_with_arxiv(
        reference,
        arxiv_id,
        repo_root=repo_root,
        allow_download=allow_download,
        timeout=timeout,
    )


def _fetch_openalex_by_doi(
    doi: str,
    arxiv_id: str | None,
    *,
    mailto: str,
    timeout: float,
    repo_root: Path,
    allow_download: bool,
) -> ManifestEntry:
    """Fetch metadata via OpenAlex for a DOI, optionally download arXiv source."""
    config = OpenAlexConfig(email=mailto, timeout=timeout)
    client = OpenAlexClient(config)
    reference = client.get_by_doi(doi)

    # If we have an arXiv ID, download the source
    if arxiv_id:
        # Ensure arXiv ID is set on reference (OpenAlex may have found it too)
        if not reference.arxiv_id:
            reference.arxiv_id = arxiv_id
        return _build_manifest_entry_with_arxiv(
            reference,
            arxiv_id,
            repo_root=repo_root,
            allow_download=allow_download,
            timeout=timeout,
        )

    return ManifestEntry(reference=reference, ingested_at=datetime.now(UTC))


def _fetch_openalex_by_arxiv(
    arxiv_id: str,
    *,
    mailto: str,
    timeout: float,
    repo_root: Path,
    allow_download: bool,
) -> ManifestEntry:
    """Fetch metadata via OpenAlex for an arXiv ID, optionally download source."""
    config = OpenAlexConfig(email=mailto, timeout=timeout)
    client = OpenAlexClient(config)
    reference = client.get_by_arxiv(arxiv_id)

    # Ensure arXiv ID is set on reference
    if not reference.arxiv_id:
        reference.arxiv_id = arxiv_id

    return _build_manifest_entry_with_arxiv(
        reference,
        arxiv_id,
        repo_root=repo_root,
        allow_download=allow_download,
        timeout=timeout,
    )


def _fetch_with_provider(
    ref: ReferenceEntry,
    provider: MetadataProvider,
    *,
    repo_root: Path,
    allow_download: bool,
    timeout: float,
) -> ManifestEntry:
    """Fetch reference metadata using injected MetadataProvider (SPEC-022).

    Args:
        ref: Reference entry with DOI and/or arXiv ID.
        provider: MetadataProvider for fetching metadata.
        repo_root: Repository root directory.
        allow_download: Whether to download arXiv source tarballs.
        timeout: HTTP timeout in seconds.

    Returns:
        ManifestEntry with metadata and optional cache info.

    Raises:
        ValueError: If reference has no identifiers or not found.
    """
    # Try DOI first, then arXiv ID
    reference: ReferenceRecord | None = None

    if ref.doi:
        reference = provider.get_by_doi(ref.doi)
        if reference is not None and ref.arxiv_id and not reference.arxiv_id:
            reference.arxiv_id = ref.arxiv_id

    if reference is None and ref.arxiv_id:
        reference = provider.get_by_arxiv(ref.arxiv_id)

    if reference is None:
        if not ref.doi and not ref.arxiv_id:
            raise ValueError("Reference has no DOI or arXiv ID")
        raise ValueError(
            f"Reference not found in {provider.provider_name}: "
            f"DOI={ref.doi}, arXiv={ref.arxiv_id}"
        )

    # Download arXiv source if we have an arXiv ID
    arxiv_id = reference.arxiv_id or ref.arxiv_id
    if arxiv_id:
        return _build_manifest_entry_with_arxiv(
            reference,
            arxiv_id,
            repo_root=repo_root,
            allow_download=allow_download,
            timeout=timeout,
        )

    return ManifestEntry(reference=reference, ingested_at=datetime.now(UTC))


def fetch_reference_entry(
    ref: ReferenceEntry,
    *,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
    source: MetadataSource = MetadataSource.OPENALEX,
    provider: MetadataProvider | None = None,
) -> ManifestEntry:
    """Fetch metadata and optionally download content for a reference.

    Args:
        ref: Reference entry with DOI and/or arXiv ID.
        repo_root: Repository root directory.
        allow_download: Whether to download arXiv source tarballs.
        allow_network: Whether network access is allowed.
        timeout: HTTP timeout in seconds.
        mailto: Contact email for API polite pools.
        source: Metadata source to use (default: OpenAlex). Ignored if provider given.
        provider: Optional MetadataProvider for dependency injection (SPEC-022).
            When provided, source parameter is ignored.

    Returns:
        ManifestEntry with metadata and optional cache info.

    Raises:
        RuntimeError: If network access is required but disabled.
        ValueError: If reference has no identifiers.
    """
    if not allow_network:
        raise RuntimeError("Network access disabled but required for fetching")

    # SPEC-022: Use injected provider if available
    if provider is not None:
        return _fetch_with_provider(
            ref,
            provider,
            repo_root=repo_root,
            allow_download=allow_download,
            timeout=timeout,
        )

    # Legacy behavior: use MetadataSource-based branching
    # Use OpenAlex as primary source (SPEC-020)
    if source == MetadataSource.OPENALEX:
        if ref.doi:
            return _fetch_openalex_by_doi(
                ref.doi,
                ref.arxiv_id,
                mailto=mailto,
                timeout=timeout,
                repo_root=repo_root,
                allow_download=allow_download,
            )
        if ref.arxiv_id:
            return _fetch_openalex_by_arxiv(
                ref.arxiv_id,
                mailto=mailto,
                timeout=timeout,
                repo_root=repo_root,
                allow_download=allow_download,
            )
        raise ValueError("Reference has no DOI or arXiv ID")

    # Legacy behavior: use arXiv/Crossref directly
    if ref.doi and ref.arxiv_id:
        return _fetch_doi_with_arxiv(
            ref.doi,
            ref.arxiv_id,
            mailto=mailto,
            timeout=timeout,
            repo_root=repo_root,
            allow_download=allow_download,
        )

    if ref.doi:
        return _fetch_doi_only(ref.doi, mailto=mailto, timeout=timeout)

    if ref.arxiv_id:
        return _fetch_arxiv_only(
            ref.arxiv_id,
            timeout=timeout,
            repo_root=repo_root,
            allow_download=allow_download,
        )

    raise ValueError("Reference has no DOI or arXiv ID")


def _error_result(
    ref: ReferenceEntry,
    error: Exception,
    *,
    network_failed: bool,
    internal_error: Exception | None = None,
) -> ReferenceProcessResult:
    """Create a ReferenceProcessResult for an error case."""
    title = "Unexpected error" if internal_error else "Failed to fetch"
    error_msg = f"{type(error).__name__}: {error}" if internal_error else str(error)
    entry = _error_manifest_entry(ref, title=f"{title}: {ref.key}", error=error_msg)
    return ReferenceProcessResult(
        entry=entry,
        failed=True,
        network_failed=network_failed,
        internal_error=internal_error,
    )


def _success_result(entry: ManifestEntry) -> ReferenceProcessResult:
    """Create a ReferenceProcessResult from a successful fetch."""
    failed = entry.error is not None
    network_failed = (
        entry.error.startswith("Download failed:") if entry.error else False
    )
    return ReferenceProcessResult(
        entry=entry,
        failed=failed,
        network_failed=network_failed,
        internal_error=None,
    )


def process_single_reference(
    ref: ReferenceEntry,
    *,
    existing_manifest: ProblemManifest | None,
    force: bool,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
    source: MetadataSource = MetadataSource.OPENALEX,
    provider: MetadataProvider | None = None,
) -> ReferenceProcessResult:
    """Process a single reference, reusing a cached manifest entry unless forced.

    Args:
        ref: Reference entry to process.
        existing_manifest: Existing manifest for idempotence.
        force: If True, ignore existing entries.
        repo_root: Repository root directory.
        allow_download: Whether to download arXiv tarballs.
        allow_network: Whether network access is allowed.
        timeout: HTTP timeout in seconds.
        mailto: Contact email for API polite pools.
        source: Metadata source to use (default: OpenAlex). Ignored if provider given.
        provider: Optional MetadataProvider for dependency injection (SPEC-022).

    Returns:
        ReferenceProcessResult with entry and status.
    """
    if existing_entry := _find_existing_manifest_entry(
        ref, existing_manifest, force=force
    ):
        return ReferenceProcessResult(
            entry=existing_entry,
            failed=False,
            network_failed=False,
            internal_error=None,
        )

    try:
        entry = fetch_reference_entry(
            ref=ref,
            repo_root=repo_root,
            allow_download=allow_download,
            allow_network=allow_network,
            timeout=timeout,
            mailto=mailto,
            source=source,
            provider=provider,
        )
        return _success_result(entry)
    except (requests.RequestException, RuntimeError) as e:
        return _error_result(ref, e, network_failed=True)
    except (
        ET.ParseError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
    ) as e:
        return _error_result(ref, e, network_failed=False)
    except Exception as e:
        # Log unexpected errors with full traceback for debugging
        logger.exception("Unexpected error processing reference %s", ref.key)
        return _error_result(ref, e, network_failed=False, internal_error=e)


def process_all_references(
    problem: ProblemRecord,
    *,
    existing_manifest: ProblemManifest | None,
    force: bool,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
    delay: float,
    source: MetadataSource = MetadataSource.OPENALEX,
    provider: MetadataProvider | None = None,
) -> ProcessAllReferencesResult:
    """Process all references for a problem.

    Args:
        problem: Problem record with references.
        existing_manifest: Existing manifest for idempotence.
        force: If True, ignore existing entries.
        repo_root: Repository root directory.
        allow_download: Whether to download arXiv tarballs.
        allow_network: Whether network access is allowed.
        timeout: HTTP timeout in seconds.
        mailto: Contact email for API polite pools.
        delay: Rate limiting delay between requests.
        source: Metadata source to use (default: OpenAlex). Ignored if provider given.
        provider: Optional MetadataProvider for dependency injection (SPEC-022).

    Returns:
        ProcessAllReferencesResult with all entries and status.
    """
    entries: list[ManifestEntry] = []
    skipped = 0
    failed = 0
    internal_error: Exception | None = None
    network_failed = False
    non_network_failed = False

    for ref in problem.references:
        # Skip references without identifiers
        if not ref.doi and not ref.arxiv_id:
            skipped += 1
            continue

        # Process reference
        result = process_single_reference(
            ref,
            existing_manifest=existing_manifest,
            force=force,
            repo_root=repo_root,
            allow_download=allow_download,
            allow_network=allow_network,
            timeout=timeout,
            mailto=mailto,
            source=source,
            provider=provider,
        )

        entries.append(result.entry)

        if result.failed:
            failed += 1
            if result.network_failed:
                network_failed = True
            else:
                non_network_failed = True
            if result.internal_error and internal_error is None:
                internal_error = result.internal_error

        # Rate limiting
        if delay > 0:
            time.sleep(delay)

    return ProcessAllReferencesResult(
        entries=entries,
        skipped=skipped,
        failed=failed,
        internal_error=internal_error,
        network_failed=network_failed,
        non_network_failed=non_network_failed,
    )
