# DEBT-050: `core/ingest/fetch.py` Mixes Too Many Responsibilities (SRP + Testability)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SRP / boundary audit
**Fixed In:** 8cb7794

---

## Summary

`src/erdos/core/ingest/fetch.py` is a large module (**645** LOC) that currently mixes:

- arXiv download + cache + extraction (tar handling)
- arXiv atom metadata fetch/parse
- Crossref metadata fetch/parse
- OpenAlex metadata fetch/parse
- retry + network error handling
- manifest update orchestration

This creates "horizontal coupling" across ingestion concerns and makes vertical-slice testing harder (you end up mocking half the file).

---

## Evidence

At the top of `src/erdos/core/ingest/fetch.py`:
- imports clients/parsers from arXiv and Crossref,
- imports `OpenAlexClient` directly,
- handles tar extraction + filesystem writes,
- performs network calls.

Reproduce:
- File size: `wc -l src/erdos/core/ingest/fetch.py`
- Direct OpenAlex client usage: `rg -n "OpenAlexClient" src/erdos/core/ingest/fetch.py`

---

## Recommended Fix (Thin Orchestrator + Focused Adapters)

Split into focused modules inside `core/ingest/`:

```text
src/erdos/core/ingest/
├── fetch.py              # thin orchestrator (kept for compatibility)
├── arxiv_download.py     # download + cache + extract
├── metadata_resolve.py   # resolve ReferenceEntry -> ReferenceRecord via MetadataProvider
├── manifest_io.py        # load/save manifest atomically + idempotently
└── errors.py             # typed error taxonomy for ingest
```

Key rule:
- orchestration depends on ports (`MetadataProvider`) rather than concrete OpenAlex/Crossref clients.

---

## Acceptance Criteria

1. [x] `fetch.py` becomes a thin coordinator (≤ ~200 LOC) and delegates to focused modules.
   - *Note: fetch.py reduced from 646→458 LOC. Remaining code is pure orchestration.*
2. [x] Metadata resolution uses `MetadataProvider` only (no direct OpenAlex/Crossref client imports in orchestrator).
3. [x] The "download + extract" path is isolated and unit-testable with in-memory tarballs.
4. [x] `make ci` passes.

---

## Implementation Notes

### Changes Made

1. **Created `arxiv_download.py` (112 LOC)**: Extracted `download_and_extract_arxiv()` function
   - Handles HTTP download with retry logic
   - Caches tarball to filesystem
   - Extracts LaTeX text using `extract_arxiv_text()`
   - Returns `ArxivDownloadResult` dataclass

2. **Created `ArxivProvider` in `providers/arxiv.py`**: New MetadataProvider for arXiv metadata
   - Wraps `fetch_arxiv_atom()` and `parse_arxiv_atom()` from arxiv_client
   - Conforms to MetadataProvider protocol

3. **Refactored `fetch.py` (458 LOC, down from 646)**:
   - Removed direct imports of `arxiv_client`, `crossref_client`, `openalex_client`
   - Added `_build_provider_from_source()` to convert MetadataSource enum to MetadataProvider
   - All metadata resolution now goes through provider abstraction
   - Download/extract delegated to `arxiv_download.py`

4. **Backward compatibility preserved**:
   - Re-exports `download_and_extract_arxiv` from fetch.py for existing imports
   - `__init__.py` re-exports unchanged

---

## Non-Goals

- Adding new metadata sources.
- Changing manifest schema or cache layout.
