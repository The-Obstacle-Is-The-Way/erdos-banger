# DEBT-040: `src/erdos/core/` Module Sprawl (Bounded Contexts Needed)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-21
**Found By:** Clean Architecture / maintainability audit
**Fixed In:** 994b99c

---

## Summary

`src/erdos/core/` has become a “grab bag” of ~30 modules mixing:

- Domain-adjacent logic (search index, loop verifier, Lean runner)
- Application wiring (`context.py`)
- Infrastructure concerns (HTTP clients, retry/rate limiting)
- Utilities (`constants.py`, `timing.py`)

This is not a correctness bug, but it increases navigation cost and makes it easier to create accidental coupling as the project grows.

---

## Evidence

`src/erdos/core/` currently contains ~30 top-level entries (excluding packages like `ask/`, `ingest/`, `models/`).

Largest modules today (LOC; may drift):
- `src/erdos/core/search_index.py` (~713)
- `src/erdos/core/loop.py` (~683)
- `src/erdos/core/batch.py` (~567)
- `src/erdos/core/ingest/fetch.py` (~546)

---

## Why This Matters (Clean Architecture)

1. **Weak boundaries:** “core” is too broad—new code lands wherever it fits “for now”.
2. **Import coupling:** modules import each other directly instead of depending on small ports.
3. **Refactor friction:** restructuring later becomes expensive (import churn + circular-import risk).

We should keep Python’s “flat is better than nested” bias, but we need **bounded contexts** so the directory structure communicates architecture.

---

## Recommended Fix (Incremental, Low-Risk)

### Option A (Documentation-only, now)

Add a documented rule:

- If a domain area grows beyond **3+ related modules**, create a subpackage.
- New infrastructure adapters belong under a `clients/` (or `adapters/`) package.

### Option B (Incremental package extraction)

Introduce subpackages without changing behavior:

```
src/erdos/core/
├── clients/          # arXiv/Crossref/OpenAlex clients + http helpers
├── search/           # search_index + embeddings + index_builder
├── loop/             # loop runner + verifier + patch validation
├── lean/             # lean_runner + formalizer + formal_conjectures + aristotle
└── util/             # constants + timing + retry + rate limiting
```

Maintain backward compatibility during migration by re-exporting (or by keeping stable import paths until a major release).

### Chosen Approach (This Deck)

Implement **Option A (documentation-only)** in this sprint.

Rationale:
- Option B is a large mechanical move (import churn across many modules) and will likely exceed the “10 files / ~500 LOC per iteration” Ralph guardrail unless split into a dedicated migration plan.
- A crisp “where does new code go?” rule prevents *future* sprawl immediately and is cheap to enforce in review.

---

## Acceptance Criteria

1. [x] `CLAUDE.md` has a short "Core package boundaries" section:
   - [x] Lists the current bounded contexts (`ask/`, `ingest/`, `models/`, `search/`) plus key top-level modules that are exceptions.
   - [x] Defines the rule: **no new modules at `src/erdos/core/*.py`** without either (a) placing code into an existing subpackage or (b) creating a new subpackage for a new bounded context.
   - [x] States where infra adapters belong (e.g., `core/clients/` or `core/adapters/`) for future work.
2. [x] This debt deck is updated to reflect completion of Option A and archived per protocol.
3. [x] `make ci` passes (no behavior changes expected).

---

## Related

- DEBT-038 (P2): `MetadataProvider` port missing (key boundary for metadata fetching).
- DEBT-039 (P2): `src/erdos/commands/lean.py` god module SRP risk.
