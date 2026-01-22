# Bug 020: OpenAlex `get_by_arxiv()` Returns None for Real arXiv IDs

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-22
**Fixed In:** fe34ca1

---

## Description

`OpenAlexProvider.get_by_arxiv()` returns `None` for real arXiv IDs even when OpenAlex contains the work. This breaks network integration tests and any ingest flow that expects OpenAlex to resolve arXiv IDs.

Observed failures:

- `tests/integration/test_providers_network.py::TestOpenAlexProviderIntegration::test_get_by_arxiv_real`
- `tests/integration/test_providers_network.py::TestFallbackProviderIntegration::test_openalex_to_crossref_fallback_arxiv`

---

## Steps to Reproduce

```bash
uv run pytest -m requires_network tests/integration/test_providers_network.py -v
```

Expected: `test_get_by_arxiv_real` passes for `1706.03762`.

Actual: `result is None`.

---

## Root Cause

`src/erdos/core/clients/openalex.py:OpenAlexClient.get_by_arxiv()` currently assumes every arXiv paper is directly addressable via a canonical OpenAlex DOI lookup:

- Constructs DataCite DOI: `10.48550/arxiv.<id>`
- Calls: `GET /works/https://doi.org/10.48550/arxiv.<id>`

However, OpenAlex may assign a **different canonical DOI** for a work and only include the arXiv landing pages / arXiv DOI in **locations**, not as the canonical DOI. In those cases, `GET /works/https://doi.org/10.48550/arxiv.<id>` returns **404** even though the work exists.

Evidence (real API):

- `filter=locations.landing_page_url:https://doi.org/10.48550/arxiv.1706.03762` returns 1 result
- `GET /works/https://doi.org/10.48550/arxiv.1706.03762` returns 404

---

## Fix

Update `OpenAlexClient.get_by_arxiv()` to:

1. Keep the current fast path (DOI lookup) for works where OpenAlex’s canonical DOI is the DataCite arXiv DOI.
2. On 404, fall back to searching `works` via a locations filter:
   - `locations.landing_page_url:https://doi.org/10.48550/arxiv.<id>`
   - `locations.landing_page_url:http://arxiv.org/abs/<id>`
   - (and optionally `https://arxiv.org/abs/<id>`)
3. Ensure `ReferenceRecord.arxiv_id` is set to the cleaned ID (no version suffix).

Also harden `extract_arxiv_id_from_work()` to scan *all* `locations[*].landing_page_url`, not just `primary_location`.

---

## Acceptance Criteria

1. `uv run pytest -m requires_network tests/integration/test_providers_network.py -v` passes
2. Unit tests updated/added to cover the fallback path (mocked response with arXiv landing page only)
3. `make ci` passes
