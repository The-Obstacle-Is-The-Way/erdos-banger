"""Reference fetching orchestration (thin coordinator).

This module orchestrates reference fetching by:
- Converting MetadataSource enum to MetadataProvider instances
- Delegating metadata resolution to providers
- Delegating arXiv download/extraction to arxiv_download module
- Building ManifestEntry results

Follows SRP: orchestration only, no direct client usage.
"""

from __future__ import annotations

import logging
import tarfile
import time
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, assert_never

import defusedxml.ElementTree as ET
import requests

from erdos.core.ingest.arxiv_download import download_and_extract_arxiv
from erdos.core.ingest.models import (
    ArxivDownloadResult,
    ProcessAllReferencesResult,
    ReferenceProcessResult,
)
from erdos.core.ingest.stable_key import get_stable_key
from erdos.core.models import (
    ManifestEntry,
    ProblemManifest,
    ProblemRecord,
    ReferenceEntry,
    ReferenceRecord,
)
from erdos.core.providers import ArxivProvider, CrossrefProvider, OpenAlexProvider
from erdos.core.providers.fallback import FallbackProvider


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.ports import MetadataProvider


logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "ArxivDownloadResult",
    "MetadataSource",
    "download_and_extract_arxiv",
    "fetch_reference_entry",
    "process_all_references",
    "process_single_reference",
]


class MetadataSource(str, Enum):
    """Metadata source for reference ingestion."""

    OPENALEX = "openalex"
    ARXIV = "arxiv"
    CROSSREF = "crossref"


def _build_provider_from_source(
    source: MetadataSource, *, mailto: str, timeout: float
) -> MetadataProvider:
    """Build a MetadataProvider from a MetadataSource enum.

    Args:
        source: The metadata source to use.
        mailto: Contact email for API polite pools.
        timeout: HTTP timeout in seconds.

    Returns:
        A MetadataProvider instance for the specified source.
    """
    if source == MetadataSource.OPENALEX:
        # OpenAlex primary with Crossref fallback (standard config)
        return FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider(mailto=mailto, timeout=timeout),
        )
    if source == MetadataSource.ARXIV:
        return ArxivProvider(timeout=timeout)
    if source == MetadataSource.CROSSREF:
        return CrossrefProvider(mailto=mailto, timeout=timeout)
    # Exhaustive match - type checker will catch missing enum cases
    assert_never(source)


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


def _fetch_with_provider(
    ref: ReferenceEntry,
    provider: MetadataProvider,
    *,
    repo_root: Path,
    allow_download: bool,
    timeout: float,
) -> ManifestEntry:
    """Fetch reference metadata using MetadataProvider (SPEC-022).

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
    # Prefer ref.arxiv_id (original input without version suffix) for download URL,
    # falling back to reference.arxiv_id (metadata may include version suffix)
    arxiv_id = ref.arxiv_id or reference.arxiv_id
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

    # Use injected provider or build from source enum
    actual_provider = provider or _build_provider_from_source(
        source, mailto=mailto, timeout=timeout
    )

    return _fetch_with_provider(
        ref,
        actual_provider,
        repo_root=repo_root,
        allow_download=allow_download,
        timeout=timeout,
    )


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
