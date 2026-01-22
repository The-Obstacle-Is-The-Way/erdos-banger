# DEBT-044: `src/erdos/core/` Still Has Bounded-Context Drift (Module Sprawl, Harder Onboarding)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Architecture / SRP audit (post v2.1)
**Fixed In:** b3b5730 (prior commits: 4b90005, 292a07d, c045e35, 679432a, 6065e53)

---

## Summary

We have started extracting bounded contexts (`core/ask/`, `core/ingest/`, `core/models/`, `core/providers/`, `core/search/`), but `src/erdos/core/` still contains **too many top-level modules** for long-term maintainability.

This is not “just aesthetics” — it makes it harder to:
- discover the correct module to change,
- enforce dependency direction (Clean Architecture),
- prevent “god modules” from reforming,
- onboard contributors without tribal knowledge.

---

## Evidence

As of 2026-01-22:

- Top-level `src/erdos/core/*.py` count is high (**28 modules**).
  - Reproduce: `ls -1 src/erdos/core/*.py | wc -l`
- Several large “domain coordinators” still live at the package root:
  - `loop.py`, `search_index.py`, `batch.py`, `openalex_client.py`, `lean_runner.py`, etc.

The repo already documents a “no new top-level core modules” rule in `CLAUDE.md`, but the existing layout is still “legacy-heavy”, which invites more drift.

---

## Why This Matters (Uncle Bob / DeepMind Standards)

- **SRP (package-level):** the package root is a dumping ground for multiple domains.
- **DIP:** “where do I put this?” ambiguity causes higher-level code to reach for concrete modules.
- **Change amplification:** features end up coupled through shared top-level modules rather than explicit ports/services.

---

## Recommended Fix (Incremental, Vertical-Slice Friendly)

Create or expand bounded-context subpackages and move code so that:

1. **Feature-oriented domains are packages** (`core/<domain>/…`).
2. **Top-level core contains only stable shared utilities and composition root**.

Suggested target layout:

```text
src/erdos/core/
├── ask/                  # already exists
├── ingest/               # already exists
├── loop/                 # NEW (move loop.py, loop_config.py, loop_verifier.py, patch_validator.py)
├── clients/              # NEW (move openalex_client.py, crossref_client.py, arxiv_client.py)
├── models/               # already exists
├── pdf/                  # NEW (move pdf_converter.py)
├── search/               # expand existing: move search_index.py, index_builder.py, embeddings.py, search/types.py
├── providers/            # already exists (MetadataProvider implementations)
├── ports.py              # stable port contracts
├── context.py            # composition root
├── constants.py
├── exit_codes.py
└── timing.py
```

Important: keep **backwards-compatible re-exports** for one release to avoid churn:

- `erdos.core.search_index.SearchIndex` remains importable (shim module re-export).
- Same for `loop`, `pdf_converter`, `openalex_client`, etc.

---

## Acceptance Criteria

1. [x] New bounded-context packages exist (`core/loop/`, `core/clients/`, `core/pdf/`, `core/batch/`, `core/formal_conjectures/`, `core/search/`), and documented in CLAUDE.md.
2. [x] No breaking imports for existing public modules (backward-compatible shim re-exports in place).
3. [x] `CLAUDE.md` "Core Package Boundaries" section updated to reflect the new layout.
4. [x] `make ci` passes.

---

## Non-Goals

- No behavior changes; this is structural refactor only.
- No new “application/framework layers” unless explicitly specced.
