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

None.

### Note on Audit False Positives (DEBT-068 through DEBT-071)

The following debt IDs were drafted during an audit, then validated as **false positives** and were not retained:

- **DEBT-068**: Tests do run — pytest discovers `test*` (no underscore required)
- **DEBT-069**: `SELECT COUNT(*)` returns a row (not `None`) under SQLite semantics
- **DEBT-070**: `ReferenceRecord` is mutable (`frozen=False`)
- **DEBT-071**: Exception handling patterns were intentional design choices, not correctness bugs

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
| DEBT-059 | CodeRabbit PR#17 fixes (validation + invariants) | P2 | Fixed | 61ad15e |
| DEBT-046 | CLIOutput `success` vs exit code ambiguity | P2 | Fixed | 0046cdf |
| DEBT-056 | FallbackProvider broad exception catches | P3 | Fixed | 5a6ce89 |
| DEBT-058 | MD5 `# noqa: S324` in loop module | P3 | Fixed | 3891aeb |
| DEBT-047 | Loop logging sanitization/unification | P3 | Fixed | c090fb3 |
| DEBT-057 | Guardrails against god-file regressions | P3 | Fixed | 1f37f5c |
| DEBT-042 | Loop contract drift + god function | P1 | Fixed | 4b90005 |
| DEBT-043 | `erdos search` command god module (SRP pressure) | P2 | Fixed | 4f99202 |
| DEBT-045 | Split `SearchIndexProtocol` (ISP/DIP) | P2 | Fixed | 279928f |
| DEBT-049 | SearchIndex monolith (SRP extraction) | P2 | Fixed | 96ec69a |
| DEBT-052 | `erdos ingest` command god module | P2 | Fixed | 8c53292 |
| DEBT-050 | Ingest fetch SRP split | P2 | Fixed | 8cb7794 |
| DEBT-054 | Run logger OCP violation (registry-based summarizers) | P3 | Fixed | b1637c6 |
| DEBT-053 | Formal conjectures module monolith (SRP split) | P3 | Fixed | 1da90e7 |
| DEBT-051 | Batch module SRP split | P3 | Fixed | 8cb7794 |
| DEBT-048 | MCP server CI coverage gap | P3 | Fixed | c756f4e |
| DEBT-055 | Scattered env-based configuration (centralized AppConfig) | P2 | Fixed | b3b5730 |
| DEBT-044 | `core/` bounded-context refactor (reduce sprawl) | P2 | Fixed | b3b5730 (+ prior) |
| DEBT-061 | Remove core backward-compatibility shims | P2 | Fixed | 4466340 |
| DEBT-060 | Formalize command long Typer callback | P4 | Fixed | 7b871e5 |
| DEBT-062 | Search service "god module" claim invalid | P1 | Closed | a60fc35 |
| DEBT-064 | `loop/runner.py` direct LLM coupling | P2 | Fixed | 06ffb51 |
| DEBT-063 | `MetadataProvider` protocol ISP violation | P2 | Fixed | 8966898 |
| DEBT-065 | Command layer contains application orchestration | P2 | Fixed | 940a362 |
| DEBT-066 | Test directory structure mirrors src/ bounded contexts | P3 | Fixed | d938411 |
| DEBT-067 | Remove private helper re-exports from core packages | P3 | Fixed | 9c83b66 |
| DEBT-072 | CLI flags silently ignored | P2 | Fixed | d386add |
| DEBT-073 | Magic numbers and hardcoded values | P3 | Fixed | 0cf5747 |
| DEBT-074 | Test quality issues | P3 | Fixed | e807fbf |
| DEBT-075 | Remove remaining env fallbacks outside `AppConfig` | P3 | Fixed | 292124f |
| DEBT-076 | Group Lean modules into `core/lean/` subpackage | P3 | Fixed | 0291d1d |
| DEBT-077 | CLI helper duplication across commands (DRY) | P3 | Fixed | 2ccd49d |
| DEBT-078 | Test organization — misclassified integration test | P4 | Fixed | 596b5c4 |
| DEBT-079 | Dead code in `literature_paths.py` (SPEC-019 stubs) | P3 | Resolved | 1c8889e |
| DEBT-080 | High cyclomatic complexity functions | P3 | Fixed | f1dbe92 |
| DEBT-081 | Incomplete features — tested but never wired in | P2 | Fixed | 05a1161,4614bd8 |
| DEBT-082 | Remove unused constants in `constants.py` | P3 | Fixed | 117d510 |
| DEBT-083 | Remove internal compatibility shims + wording | P2 | Fixed | 117d510 |
| DEBT-084 | Finish batch interrupt wiring (SIGINT) | P3 | Fixed | 117d510 |
| DEBT-085 | Restore and wire removed constants (DEBT-082 regression) | P2 | Fixed | c5b5d9f,f70613a |
| DEBT-086 | Loop runner state machine refactor | P2 | Fixed | 22f14f6 |
| DEBT-087 | LLM execute error handling consolidation | P3 | Fixed | 22f14f6 |
| DEBT-088 | Patch validator multiple returns (acceptable) | P4 | Won't Fix | 22f14f6 |
| DEBT-089 | Ingest/fetch long parameter lists | P1 | Fixed | 22f14f6 |
| DEBT-090 | Cyclomatic complexity violations (C901) | P2 | Fixed | 22f14f6 |
| DEBT-091 | Blind exception catches (BLE001) | P3 | Fixed | 22f14f6 |
| DEBT-092 | Proof verification module LOC violations | P3 | Fixed | 534802f |
| DEBT-096 | Search command module LOC violation (post-MSC growth) | P3 | Fixed | 4a21f0b |
| DEBT-097 | Test suite ANSI handling inconsistency | P2 | Fixed | 3d19c58 |
| DEBT-098 | Test references deprecated std4 repository | P1 | Fixed | e49696e |
| DEBT-099 | Lean test fixture lakefile syntax outdated | P2 | Fixed | (this PR) |
| DEBT-100 | Integration tests don't load .env file | P3 | Fixed | 8410c4f |
| DEBT-101 | Lean/Mathlib version significantly behind | P2 | Fixed | 986035f,2ebb005 |
| DEBT-102 | Console instantiation DRY violation | P3 | Fixed | (this PR) |
| DEBT-103 | Untracked C901 complexity violations | P3 | Fixed | (this PR) |
| DEBT-104 | Error type naming inconsistency | P4 | Fixed | (this PR) |
| DEBT-105 | Print statements in core modules | P4 | Resolved | (this PR) |
| DEBT-106 | Broad exception catches without justification | P3 | Fixed | (this PR) |
| DEBT-107 | Missing public function docstrings | P4 | Fixed | (this PR) |
| DEBT-093 | Exa client infrastructure duplication | P2 | Fixed | (this PR) |
| DEBT-094 | Semantic Scholar client LOC violation | P3 | Fixed | (via DEBT-093) |
| DEBT-095 | zbMATH client LOC violation | P3 | Fixed | (via DEBT-093) |

**Next Debt ID:** DEBT-108

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
- `docs/_archive/debt/debt-059-coderabbit-pr17-fixes.md`
- `docs/_archive/debt/debt-046-clioutput-success-vs-exitcode.md`
- `docs/_archive/debt/debt-056-fallback-provider-broad-exceptions.md`
- `docs/_archive/debt/debt-058-md5-noqa-in-loop.md`
- `docs/_archive/debt/debt-047-loop-logging-sanitization-and-unification.md`
- `docs/_archive/debt/debt-057-guardrails-against-god-files.md`
- `docs/_archive/debt/debt-042-loop-command-contract-and-god-module.md`
- `docs/_archive/debt/debt-043-search-command-god-module.md`
- `docs/_archive/debt/debt-045-searchindexprotocol-interface-segregation.md`
- `docs/_archive/debt/debt-049-search-index-monolith.md`
- `docs/_archive/debt/debt-052-ingest-command-god-module.md`
- `docs/_archive/debt/debt-050-ingest-fetch-srp.md`
- `docs/_archive/debt/debt-054-run-logger-ocp-violation.md`
- `docs/_archive/debt/debt-053-formal-conjectures-module-monolith.md`
- `docs/_archive/debt/debt-051-batch-module-srp.md`
- `docs/_archive/debt/debt-048-mcp-server-god-module-and-ci-coverage.md`
- `docs/_archive/debt/debt-055-configuration-scattered-env-deps.md`
- `docs/_archive/debt/debt-044-core-bounded-context-refactor.md`
- `docs/_archive/debt/debt-061-remove-core-compatibility-shims.md`
- `docs/_archive/debt/debt-060-formalize-cmd-long-callback.md`
- `docs/_archive/debt/debt-062-search-service-god-module.md`
- `docs/_archive/debt/debt-064-loop-runner-dip.md`
- `docs/_archive/debt/debt-063-metadata-provider-isp.md`
- `docs/_archive/debt/debt-065-thick-cli-callbacks.md`
- `docs/_archive/debt/debt-066-test-structure-mirrors-src.md`
- `docs/_archive/debt/debt-067-remove-private-reexports.md`
- `docs/_archive/debt/debt-072-cli-flags-silently-ignored.md`
- `docs/_archive/debt/debt-073-magic-numbers-hardcoded-values.md`
- `docs/_archive/debt/debt-074-test-quality-issues.md`
- `docs/_archive/debt/debt-075-remove-remaining-env-fallbacks.md`
- `docs/_archive/debt/debt-076-group-lean-modules-into-subpackage.md`
- `docs/_archive/debt/debt-077-cli-helper-duplication.md`
- `docs/_archive/debt/debt-078-test-organization-misclassification.md`
- `docs/_archive/debt/debt-079-dead-code-literature-paths.md`
- `docs/_archive/debt/debt-080-high-cyclomatic-complexity.md`
- `docs/_archive/debt/debt-081-incomplete-features-not-wired.md`
- `docs/_archive/debt/debt-082-unused-constants.md`
- `docs/_archive/debt/debt-083-backwards-compatibility-shims.md`
- `docs/_archive/debt/debt-084-unused-ocp-patterns.md`
- `docs/_archive/debt/debt-085-restore-and-wire-constants.md`
- `docs/_archive/debt/debt-086-loop-runner-state-machine.md`
- `docs/_archive/debt/debt-087-llm-execute-error-handling.md`
- `docs/_archive/debt/debt-088-patch-validator-returns.md`
- `docs/_archive/debt/debt-089-ingest-fetch-parameter-objects.md`
- `docs/_archive/debt/debt-090-cyclomatic-complexity-violations.md`
- `docs/_archive/debt/debt-091-blind-exception-catches.md`
- `docs/_archive/debt/debt-092-proof-verification-loc.md`
- `docs/_archive/debt/debt-093-exa-client-loc.md`
- `docs/_archive/debt/debt-094-semantic-scholar-client-loc.md`
- `docs/_archive/debt/debt-095-zbmath-client-loc.md`
- `docs/_archive/debt/debt-096-search-command-msc-loc.md`
- `docs/_archive/debt/debt-097-test-suite-consistency.md`
- `docs/_archive/debt/debt-098-std4-repo-rename.md`
- `docs/_archive/debt/debt-099-lean-fixture-lakefile-syntax.md`
- `docs/_archive/debt/debt-100-test-env-file-loading.md`
- `docs/_archive/debt/debt-101-lean-mathlib-version-upgrade.md`
- `docs/_archive/debt/debt-102-console-dry-violation.md`
- `docs/_archive/debt/debt-103-c901-complexity-violations.md`
- `docs/_archive/debt/debt-104-error-type-naming-inconsistency.md`
- `docs/_archive/debt/debt-105-print-statements-in-core.md`
- `docs/_archive/debt/debt-106-broad-exception-catches.md`
- `docs/_archive/debt/debt-107-missing-public-docstrings.md`
