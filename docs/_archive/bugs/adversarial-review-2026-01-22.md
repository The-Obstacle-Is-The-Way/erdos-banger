# Adversarial Review: 2026-01-22 (Post v2.1 Architecture Sprint)

**Scope:** Post-sprint architecture sanity check and “Uncle Bob” audit of the loop/search subsystems.
**Branch audited:** `ralph-wiggum-v2.1`
**Quality gates:** `make ci` (✅ pass: 838 tests selected, 2 skipped, 81.75% coverage)

---

## Executive Summary

No new P0/P1 correctness bugs were observed in the passing test suite, but two **high-leverage maintainability risks** remain:

1. The loop subsystem has **contract ambiguity** (spec text vs implementation) and a **god function** (`run_loop`) with high change amplification risk.
2. The search command remains a **large command-layer module**, increasing future change risk (embeddings/hybrid search evolution, batch workflows).

These are now tracked as active technical debt decks:
- DEBT-042 (loop contract + god function)
- DEBT-043 (search command god module)

---

## Evidence (Reproducible)

### 1) Largest Python modules (by LOC)

Top offenders (approximate):

- `src/erdos/commands/search.py` (~791 LOC)
- `src/erdos/core/loop.py` (~683 LOC)
- `src/erdos/core/search_index.py` (~679 LOC)
- `src/erdos/core/ingest/fetch.py` (~645 LOC)

### 2) Longest functions (by AST end line)

- `src/erdos/core/loop.py:285-683 run_loop` (~399 LOC)
- `src/erdos/commands/search.py:588-791 search` (~204 LOC)

Both have complexity suppressions (`PLR091*`) indicating ruff has already identified them as SRP/complexity hotspots.

---

## SOLID / Clean Architecture Notes

### SRP

- `run_loop` mixes orchestration, IO, logging, and domain rules → high coupling.
- `commands/search.py` mixes CLI, output, orchestration, and domain decisions.

### DIP

- Provider orchestration work (SPEC-022) improved DIP by introducing `MetadataProvider` + `SearchIndexProtocol`.
- Remaining DIP pressure is largely “command-layer orchestration” rather than “core imports UI”.

---

## Recommendations

1. Resolve loop contract ambiguity by choosing the SSOT:
   - Either update archived Spec-012 to match implementation, or align implementation to Spec-012.
2. Extract loop into a bounded-context package (`core/loop/…`) and reduce `run_loop` to a small coordinator.
3. Move search orchestration into `core/search/service.py` and keep CLI thin.

---

## Outputs

Created:
- `docs/debt/debt-042-loop-command-contract-and-god-module.md`
- `docs/debt/debt-043-search-command-god-module.md`

Updated:
- `docs/debt/README.md` (active debt list)
