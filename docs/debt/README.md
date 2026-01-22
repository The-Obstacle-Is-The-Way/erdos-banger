# Technical Debt Decks

This directory contains technical-debt writeups: spec drift, missing fixtures, incomplete implementations, or refactors that improve long-term maintainability.

## Debt Priority Definitions

| Priority | Definition |
|----------|------------|
| **P0** | Immediate risk (security/data loss) if not addressed |
| **P1** | Blocks planned work or causes frequent breakage |
| **P2** | Material quality gap; should be scheduled soon |
| **P3** | Minor; clean up when touching nearby code |
| **P4** | Enhancement / polish |

## Active Debt

| ID | Title | Priority | Status | Deck |
|----|-------|----------|--------|------|
| DEBT-042 | Loop contract drift + `core/loop.py` god function | P1 | Open | `debt-042-loop-command-contract-and-god-module.md` |
| DEBT-043 | `erdos search` command god module (SRP pressure) | P2 | Open | `debt-043-search-command-god-module.md` |
| DEBT-044 | `core/` bounded-context refactor (reduce sprawl) | P2 | Open | `debt-044-core-bounded-context-refactor.md` |
| DEBT-045 | Split `SearchIndexProtocol` (ISP/DIP) | P2 | Open | `debt-045-searchindexprotocol-interface-segregation.md` |
| DEBT-046 | CLIOutput `success` vs exit code ambiguity | P2 | Open | `debt-046-clioutput-success-vs-exitcode.md` |
| DEBT-047 | Loop logging sanitization/unification | P3 | Open | `debt-047-loop-logging-sanitization-and-unification.md` |
| DEBT-048 | MCP server module size + CI coverage gap | P3 | Open | `debt-048-mcp-server-god-module-and-ci-coverage.md` |
| DEBT-049 | SearchIndex monolith (SRP extraction) | P2 | Open | `debt-049-search-index-monolith.md` |
| DEBT-050 | Ingest fetch SRP split | P2 | Open | `debt-050-ingest-fetch-srp.md` |
| DEBT-051 | Batch module SRP split | P3 | Open | `debt-051-batch-module-srp.md` |
| DEBT-052 | `erdos ingest` command god module | P2 | Open | `debt-052-ingest-command-god-module.md` |
| DEBT-053 | Formal conjectures module monolith | P3 | Open | `debt-053-formal-conjectures-module-monolith.md` |
| DEBT-054 | Run logger OCP violation (central command switch) | P3 | Open | `debt-054-run-logger-ocp-violation.md` |
| DEBT-055 | Scattered env-based configuration | P2 | Open | `debt-055-configuration-scattered-env-deps.md` |
| DEBT-056 | FallbackProvider broad exception catches | P3 | Open | `debt-056-fallback-provider-broad-exceptions.md` |
| DEBT-057 | Guardrails against god-file regressions | P3 | Open | `debt-057-guardrails-against-god-files.md` |
| DEBT-058 | MD5 `# noqa: S324` in loop module | P3 | Open | `debt-058-md5-noqa-in-loop.md` |
| DEBT-059 | CodeRabbit PR#17 fixes (validation + invariants) | P2 | Open | `debt-059-coderabbit-pr17-fixes.md` |

## Archived Debt

All debt below has been resolved and archived to `docs/_archive/debt/`.

| ID | Title | Priority | Status | Commit |
|----|-------|----------|--------|--------|
| DEBT-001 | Spec 005 drift/inconsistency | P1 | Fixed | 19f2225 |
| DEBT-002 | Spec 006 search CLI drift | P2 | Fixed | bd21e6c |
| DEBT-003 | Spec 008 fixtures incomplete | P1 | Fixed | bfb5b70 |
| DEBT-004 | Lean scaffolding absent vs Spec 007 | P1 | Fixed | 7e17d21 |
| DEBT-005 | Placeholder tests vs "real" coverage | P2 | Fixed | 59bdeac |
| DEBT-006 | Ephemeral test data / persistence gaps | P1 | Fixed | a47d9f2,57cf739 |
| DEBT-007 | Lean compilation not enforced in CI | P1 | Fixed | c9cbf24,ec0b93d |
| DEBT-008 | Unused fixtures / no golden tests | P2 | Fixed | 57cf739 |
| DEBT-009 | Upstream data not integrated | P1 | Fixed | 70ae1ab,96eb024 |
| DEBT-010 | No smoke test | P2 | Fixed | 70ae1ab,c9cbf24 |
| DEBT-013 | Spec 010 scope planning | P1 | Fixed | 931b98b |
| DEBT-011 | SPEC-020 status clarification | P2 | Resolved | c526e10 |
| DEBT-012 | Broad exception handling in ingest.py | P1 | Fixed | 2cb6fac |
| DEBT-014 | Roadmap/tracking docs drift after v1.1 | P2 | Fixed | c526e10 |
| DEBT-015 | Minor Style Debt (code=1 vs ExitCode.ERROR) | P4 | Fixed | 9df84ca |
| DEBT-016 | SRP violation in domain models | P2 | Fixed | 3f63fab |
| DEBT-017 | Function length violations | P1 | Fixed | 94c3788,9e5de0a,b8d5395,64d3293,fb85afe,aa0b92e |
| DEBT-018 | DRY violations (duplication) | P1 | Fixed | b069060,786cd42,ff4e412,3dd1610,fbdd5a0 |
| DEBT-019 | Dependency inversion violations | P2 | Fixed | 3dd1610 |
| DEBT-020 | Magic Numbers and Naming | P3 | Fixed | 6d8981c |
| DEBT-021 | Missing abstractions | P2 | Fixed | 3dd1610 |
| DEBT-022 | Large core modules (SRP pressure) | P2 | Fixed | 8d75c8a |
| DEBT-023 | Security lint suppressions (XML + MD5) | P2 | Fixed | 764c597 |
| DEBT-024 | Placeholder metadata (authors / contact email) | P3 | Fixed | 647c86d |
| DEBT-025 | DRY violation in shell LLM wrappers | P4 | Fixed | c05d7a7 |
| DEBT-026 | Long functions remain (≥ 80 LOC) | P2 | Fixed | c31d484 |
| DEBT-027 | Broad `except Exception` catches | P3 | Fixed | e657d7c |
| DEBT-028 | Ingest manifest churn (non-idempotent writes) | P2 | Fixed | 154866b |
| DEBT-029 | Logging coverage gaps | P2 | Fixed | f806edc |
| DEBT-030 | Redundant dual --json flag | P3 | Fixed | ed2c2c8 |
| DEBT-031 | Rate limiting constant unused | P3 | Fixed | c50766c |
| DEBT-032 | HTTP responses not closed properly | P2 | Fixed | 5fd4a57 |
| DEBT-033 | No retry logic for network failures | P2 | Fixed | 11a3519 |
| DEBT-034 | Hardcoded MAX_SIZE constant | P3 | Fixed | 878aa7b |
| DEBT-035 | type: ignore in all exit paths | P2 | Fixed | 86d3856 |
| DEBT-037 | Placeholder semantic search tests | P2 | Fixed | b2dcdfe |
| DEBT-039 | `erdos lean` command module is a god file | P2 | Fixed | 8540017 |
| DEBT-041 | `ports.py` leaks concrete `search_index` types | P3 | Fixed | e27e5a3 |
| DEBT-040 | `src/erdos/core/` module sprawl (doc-only) | P3 | Fixed | 994b99c |
| DEBT-036 | Marker device selection not exposed | P3 | Fixed | 7005b65 |
| DEBT-038 | MetadataProvider abstraction missing | P2 | Resolved | SPEC-022 |

**Next Debt ID:** DEBT-060

### Archived Debt Decks

- `docs/_archive/debt/debt-001-spec-005-ssot-drift.md`
- `docs/_archive/debt/debt-013-spec-010-scope.md`
- `docs/_archive/debt/debt-011-spec-020-not-implemented.md`
- `docs/_archive/debt/debt-012-broad-exception-handling.md`
- `docs/_archive/debt/debt-014-roadmap-and-tracking-docs-drift.md`
- `docs/_archive/debt/debt-002-spec-006-search-cli-drift.md`
- `docs/_archive/debt/debt-003-spec-008-fixtures-incomplete.md`
- `docs/_archive/debt/debt-004-lean-scaffolding-missing.md`
- `docs/_archive/debt/debt-005-placeholder-tests.md`
- `docs/_archive/debt/debt-006-ephemeral-test-data.md`
- `docs/_archive/debt/debt-007-lean-ci-never-runs.md`
- `docs/_archive/debt/debt-008-unused-golden-fixtures.md`
- `docs/_archive/debt/debt-009-upstream-data-not-integrated.md`
- `docs/_archive/debt/debt-010-no-smoke-test.md`
- `docs/_archive/debt/debt-015-minor-style-debt.md`
- `docs/_archive/debt/debt-016-srp-models-violation.md`
- `docs/_archive/debt/debt-017-function-length-violations.md`
- `docs/_archive/debt/debt-018-dry-violations.md`
- `docs/_archive/debt/debt-019-dependency-inversion-violations.md`
- `docs/_archive/debt/debt-020-magic-numbers-and-naming.md`
- `docs/_archive/debt/debt-021-missing-abstractions.md`
- `docs/_archive/debt/debt-024-placeholder-metadata-identifiers.md`
- `docs/_archive/debt/debt-023-security-lint-suppressions.md`
- `docs/_archive/debt/debt-025-shell-llm-wrapper-duplication.md`
- `docs/_archive/debt/debt-022-large-core-modules-srp.md`
- `docs/_archive/debt/debt-026-long-functions-remain.md`
- `docs/_archive/debt/debt-027-broad-exception-catches.md`
- `docs/_archive/debt/debt-028-ingest-manifest-churn.md`
- `docs/_archive/debt/debt-029-no-logging-usage.md`
- `docs/_archive/debt/debt-030-redundant-json-flag.md`
- `docs/_archive/debt/debt-031-no-api-rate-limiting.md`
- `docs/_archive/debt/debt-032-http-response-not-closed.md`
- `docs/_archive/debt/debt-033-no-retry-logic.md`
- `docs/_archive/debt/debt-034-hardcoded-max-size.md`
- `docs/_archive/debt/debt-035-type-ignore-exit-paths.md`
- `docs/_archive/debt/debt-037-semantic-search-placeholder-tests.md`
- `docs/_archive/debt/debt-039-lean-command-god-module.md`
- `docs/_archive/debt/debt-041-ports-leak-search-index-types.md`
- `docs/_archive/debt/debt-040-core-package-module-sprawl.md`
- `docs/_archive/debt/debt-036-marker-mps-not-configured.md`
- `docs/_archive/debt/debt-038-metadata-provider-abstraction.md`
