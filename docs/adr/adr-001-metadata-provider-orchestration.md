# ADR-001: Metadata Provider Orchestration (Ports + Provider Chain)

**Status:** Accepted
**Date:** 2026-01-21
**Related:** `docs/specs/spec-022-metadata-provider-orchestration.md`, `docs/debt/debt-038-metadata-provider-abstraction.md`, `docs/specs/master-qualifications.md#5-api-orchestration-strategy-rob-c-martin-principles`

## Context

`erdos-banger` fetches literature **metadata** from multiple external sources:
- OpenAlex (primary)
- Crossref (fallback)
- arXiv export API (metadata-only fallback; arXiv source tarball for content)

Today, metadata orchestration is embedded in `src/erdos/core/ingest/fetch.py` via:
- direct construction of concrete clients (`OpenAlexClient(...)`), and
- branching on `MetadataSource` to choose a code path.

This creates avoidable coupling:
- **DIP violation:** ingest policy depends on concrete clients.
- **OCP violation:** adding a new source requires editing branching logic.
- **Test friction:** unit tests must monkeypatch network clients rather than inject fakes.

## Decision

Adopt a **Clean Architecture / Ports-and-Adapters** approach for metadata retrieval:

1. Define a `MetadataProvider` **port** (a `typing.Protocol`) in `src/erdos/core/ports.py`.
2. Implement providers as thin **adapters** around existing clients:
   - `OpenAlexProvider` wraps `OpenAlexClient`
   - `CrossrefProvider` wraps `fetch_crossref_work()` + `parse_crossref_work()`
3. Implement `FallbackProvider(primary, fallback)` that conforms to the same port and provides:
   - “not found” fallback (primary returns `None`)
   - “error” fallback (primary raises)
4. Compose the default chain in the **composition root** (`AppContext`), not inside ingest functions.

Target dependency arrows:

```
commands/services ──► ports (MetadataProvider) ◄── adapters (OpenAlex/Crossref)
```

## Options Considered

### Option A (Chosen): Provider Port + Fallback Chain (In-Process)
**Pros**
- Strong DIP/OCP: new sources are new adapters, not edits to ingest logic.
- Testable: unit tests inject providers; network tests are isolated + marked.
- Small change: builds on existing `OpenAlexClient`/`crossref_client` code.
**Cons**
- Adds a small amount of indirection (provider wrappers).

### Option B: Single “Orchestrator” Service With Hardcoded Clients
**Pros**
- Keeps logic centralized in one place.
**Cons**
- Still violates DIP/OCP unless it exposes a port anyway.
- Risks becoming another “god service” as sources expand.

### Option C: Plugin Registry (Entry Points) for Providers
**Pros**
- Maximum extensibility for external providers.
**Cons**
- Overkill for a local-first CLI at ~1k problems; adds packaging complexity.

## Consequences

- `SPEC-022` is the implementation spec for this ADR.
- `ingest/fetch.py` should accept an injected `MetadataProvider` (no direct client construction).
- The CLI `--source` flag becomes a selection of provider chains rather than a branching switch inside fetch code.
- Network integration tests become explicit (`@pytest.mark.requires_network`) and optional.

## Follow-ups / Non-Goals

- Do not build “paper discovery” here; this ADR is only about **metadata retrieval** for known identifiers.
- Do not redesign the arXiv **content** path (tarball download/extract); keep it separate from metadata providers.
