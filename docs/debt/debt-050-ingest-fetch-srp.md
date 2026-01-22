# DEBT-050: `core/ingest/fetch.py` Mixes Too Many Responsibilities (SRP + Testability)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SRP / boundary audit

---

## Summary

`src/erdos/core/ingest/fetch.py` is a large module (**645** LOC) that currently mixes:

- arXiv download + cache + extraction (tar handling)
- arXiv atom metadata fetch/parse
- Crossref metadata fetch/parse
- OpenAlex metadata fetch/parse
- retry + network error handling
- manifest update orchestration

This creates “horizontal coupling” across ingestion concerns and makes vertical-slice testing harder (you end up mocking half the file).

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

1. [ ] `fetch.py` becomes a thin coordinator (≤ ~200 LOC) and delegates to focused modules.
2. [ ] Metadata resolution uses `MetadataProvider` only (no direct OpenAlex/Crossref client imports in orchestrator).
3. [ ] The “download + extract” path is isolated and unit-testable with in-memory tarballs.
4. [ ] `make ci` passes.

---

## Non-Goals

- Adding new metadata sources.
- Changing manifest schema or cache layout.
