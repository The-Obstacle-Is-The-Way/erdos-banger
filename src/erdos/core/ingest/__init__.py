"""Ingest package: reference ingestion for Erdős problems.

This package provides:
- stable_key: Stable key generation for deduplication
- models: Result dataclasses
- fetch: Reference fetching and download
- service: Single-problem orchestration (ingest_problem_references)
- app: Application service (batch + single orchestration)

All public APIs are re-exported for backward compatibility.
"""

# Re-export public APIs for backward compatibility
from erdos.core.ingest.app import (
    IngestOptions,
    batch_result_to_cli_output,
    create_batch_process_fn,
    execute_ingest,
    get_repo_root,
    is_batch_mode,
    prepare_mailto,
    run_batch_ingestion,
    run_single_ingestion,
)
from erdos.core.ingest.fetch import (
    MetadataSource,
    download_and_extract_arxiv,
    fetch_reference_entry,
    process_all_references,
    process_single_reference,
)
from erdos.core.ingest.models import (
    ArxivDownloadResult,
    ProcessAllReferencesResult,
    ReferenceProcessResult,
)
from erdos.core.ingest.service import ingest_problem_references
from erdos.core.ingest.stable_key import HasIdentifiers, get_stable_key


# Private name aliases for backward compatibility with internal/test imports
_download_and_extract_arxiv = download_and_extract_arxiv
_fetch_reference_entry = fetch_reference_entry
_process_all_references = process_all_references
_process_single_reference = process_single_reference
_ReferenceProcessResult = ReferenceProcessResult
_ProcessAllReferencesResult = ProcessAllReferencesResult

__all__ = [
    "ArxivDownloadResult",
    "HasIdentifiers",
    "IngestOptions",
    "MetadataSource",
    "ProcessAllReferencesResult",
    "ReferenceProcessResult",
    "_ProcessAllReferencesResult",
    "_ReferenceProcessResult",
    "_download_and_extract_arxiv",
    "_fetch_reference_entry",
    "_process_all_references",
    "_process_single_reference",
    "batch_result_to_cli_output",
    "create_batch_process_fn",
    "download_and_extract_arxiv",
    "execute_ingest",
    "fetch_reference_entry",
    "get_repo_root",
    "get_stable_key",
    "ingest_problem_references",
    "is_batch_mode",
    "prepare_mailto",
    "process_all_references",
    "process_single_reference",
    "run_batch_ingestion",
    "run_single_ingestion",
]
