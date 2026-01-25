# Bug Reports & Adversarial Reviews

This directory contains bug reports, adversarial code reviews, and quality audits for the erdos-banger project.

## Reviews

| Date | Type | Summary | Status |
|------|------|---------|--------|
| 2026-01-25 | Adversarial Review | Status filter validation audit (1 bug fixed in 3ab5c5c) | Archived |
| 2026-01-25 | Adversarial Review | Post-refactor CLI stress test (no new bugs; expanded regression tests) | Archived |
| 2026-01-25 | Adversarial Review | CLI stress test, input validation audit (6 bugs fixed in 92039ca) | Archived |
| 2026-01-25 | Adversarial Review | Follow-up stress test (2 bugs fixed in 6c7eef2) | Archived |
| 2026-01-22 | Adversarial Review | Post v2.1 architecture audit (loop/search SRP hotspots) | Archived |
| 2026-01-21 | Adversarial Review | Full codebase audit for bugs, debt, anti-patterns | Archived |
| 2026-01-17 | Adversarial Review | Full codebase audit covering specs 003-006 | Archived |

## Active Bugs

None.

*Note: BUG-013 was invalidated as a false positive. BUG-015 and BUG-017 were review findings that were invalidated before standalone bug decks were created.*

## Archived Bugs

All bugs below have been fixed and archived to `docs/_archive/bugs/`.

| ID | Title | Priority | Status | Commit |
|----|-------|----------|--------|--------|
| BUG-001 | Typer `CliRunner` unsupported `mix_stderr` arg | P1 | Fixed | e862a35 |
| BUG-002 | `erdos search --build-index --json` contaminates stdout | P2 | Fixed | e862a35 |
| BUG-003 | `erdos search` crashes when index exists but dataset missing | P2 | Fixed | e862a35 |
| BUG-004 | `iter_problems()` allows duplicate IDs (index overwrite risk) | P2 | Fixed | e862a35 |
| BUG-005 | Dead global flags: `--config`, `--no-network` | P2 | Fixed | a26d149 |
| BUG-006 | Ruff lints upstream submodule files | P1 | Fixed | 2f4124b |
| BUG-007 | Missing `requests` dependency in pyproject.toml | P0 | Fixed | d97b218 |
| BUG-008 | Hardcoded exit code 78 in ask.py | P0 | Fixed | d97b218 |
| BUG-009 | `erdos ask` crashes on NOT_FOUND + breaks `--json` contract | P0 | Fixed | 0310d62 |
| BUG-010 | `erdos ingest --no-network` wrong exit code on first run | P2 | Fixed | 49ba46f |
| BUG-011 | No enriched problem data for production use | P1 | Fixed | 54e2dfb |
| BUG-012 | Ask retrieval uses exact phrase match | P2 | Fixed | 89a66c2 |
| BUG-013 | `--log-level` dead code (invalidated) | P2 | Invalidated | 1d5bd51 |
| BUG-014 | Silent exception swallowing masks errors | P1 | Fixed | 1d5bd51 |
| BUG-016 | Manifest corruption silently returns None | P2 | Fixed | 1d5bd51 |
| BUG-018 | OpenAlex client `get_by_arxiv()` broken + wrong test DOIs | P1 | Fixed | b2dcdfe |
| BUG-019 | `erdos convert --format` is a no-op | P2 | Fixed | b2dcdfe |
| BUG-020 | OpenAlex `get_by_arxiv()` returns None for real arXiv IDs | P1 | Fixed | fe34ca1 |
| BUG-021 | `erdos ingest` ignores `--mailto`/`--timeout` for OpenAlex requests | P2 | Fixed | 853dde8 |
| BUG-022 | `erdos ingest --pdf` flags silently ignored | P2 | Fixed | 1c8889e |
| BUG-023 | `erdos lean import` path duplication causes crash | P1 | Fixed | 92039ca |
| BUG-024 | `erdos search --limit` crashes with traceback for invalid values | P2 | Fixed | 92039ca |
| BUG-025 | `erdos ask --limit` accepts invalid values silently | P2 | Fixed | 92039ca |
| BUG-026 | `erdos refs s2 --limit 0` causes cryptic API error | P2 | Fixed | 92039ca |
| BUG-027 | `--log-level` accepts invalid values without error | P3 | Fixed | 92039ca |
| BUG-028 | Batch commands accept negative `--limit` values | P3 | Fixed | 92039ca |
| BUG-029 | zbMATH commands accept invalid pagination/year ranges | P2 | Fixed | 6c7eef2 |
| BUG-030 | `erdos ingest` accepts invalid numeric values | P2 | Fixed | 6c7eef2 |
| BUG-031 | `make smoke` fails when Lean installed but mathlib is not | P2 | Fixed | 83bf9f6 |
| BUG-032 | Batch `--status` accepts invalid values (misclassified as NotFound) | P3 | Fixed | 3ab5c5c |

**Next Bug ID:** BUG-033

### Archived Bug Decks

- `docs/_archive/bugs/bug-001-typer-clirunner-mix-stderr.md`
- `docs/_archive/bugs/bug-007-missing-requests-dependency.md`
- `docs/_archive/bugs/bug-008-hardcoded-exit-code-78.md`
- `docs/_archive/bugs/bug-009-ask-crash-not-found-json-contract.md`
- `docs/_archive/bugs/bug-010-ingest-no-network-exit-code.md`
- `docs/_archive/bugs/bug-011-missing-enriched-data.md`
- `docs/_archive/bugs/bug-012-ask-retrieval-exact-match.md`
- `docs/_archive/bugs/bug-013-log-level-dead-code.md`
- `docs/_archive/bugs/bug-014-silent-exception-swallowing.md`
- `docs/_archive/bugs/bug-016-manifest-corruption-silent.md`
- `docs/_archive/bugs/adversarial-review-2026-01-17.md`
- `docs/_archive/bugs/adversarial-review-2026-01-21.md`
- `docs/_archive/bugs/adversarial-review-2026-01-22.md`
- `docs/_archive/bugs/adversarial-review-2026-01-25.md`
- `docs/_archive/bugs/adversarial-review-2026-01-25-followup.md`
- `docs/_archive/bugs/adversarial-review-2026-01-25-post-refactor-stress.md`
- `docs/_archive/bugs/bug-002-search-build-index-json-stdout.md`
- `docs/_archive/bugs/bug-003-search-fts-loader-missing.md`
- `docs/_archive/bugs/bug-004-iter-problems-duplicate-ids.md`
- `docs/_archive/bugs/bug-005-dead-global-flags.md`
- `docs/_archive/bugs/bug-006-ruff-lints-submodule.md`
- `docs/_archive/bugs/bug-018-openalex-client-broken.md`
- `docs/_archive/bugs/bug-019-convert-format-no-op.md`
- `docs/_archive/bugs/bug-020-openalex-get-by-arxiv-returns-none.md`
- `docs/_archive/bugs/bug-021-ingest-openalex-mailto-timeout-ignored.md`
- `docs/_archive/bugs/bug-022-ingest-pdf-flags-silently-ignored.md`
- `docs/_archive/bugs/bug-023-lean-import-path-duplication.md`
- `docs/_archive/bugs/bug-024-search-limit-validation-missing.md`
- `docs/_archive/bugs/bug-025-ask-limit-validation-missing.md`
- `docs/_archive/bugs/bug-026-refs-s2-limit-validation-missing.md`
- `docs/_archive/bugs/bug-027-log-level-invalid-values-ignored.md`
- `docs/_archive/bugs/bug-028-batch-limit-negative-values-accepted.md`
- `docs/_archive/bugs/bug-029-zbmath-validation-missing.md`
- `docs/_archive/bugs/bug-030-ingest-numeric-validation-missing.md`
- `docs/_archive/bugs/bug-031-smoke-test-lean-check-no-mathlib.md`
- `docs/_archive/bugs/adversarial-review-2026-01-25-status-validation.md`
- `docs/_archive/bugs/bug-032-batch-status-validation-missing.md`

### Active Bug Decks

None.

## Bug Priority Definitions

| Priority | Definition | Response Time |
|----------|------------|---------------|
| **P0** | Critical - Data loss, security vulnerability, crashes | Immediate |
| **P1** | High - Major functionality broken, blocks users | Next release |
| **P2** | Medium - Feature partially broken, workaround exists | Soon |
| **P3** | Low - Minor issues, cosmetic, edge cases | When convenient |
| **P4** | Enhancement - Nice to have, quality of life | Backlog |

## Quick Links

- [Adversarial Review 2026-01-21](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/bugs/adversarial-review-2026-01-21.md)
  - 2 confirmed bugs (1 P1, 1 P2) - 3 false positives invalidated
  - 7 technical debt items (4 P2, 3 P3)
  - Focus: silent failures, observability gaps, API robustness
- [Adversarial Review 2026-01-22](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/bugs/adversarial-review-2026-01-22.md)
  - No new correctness bugs found under `make ci`
  - 2 active debt items filed (loop + search SRP pressure)
- [Adversarial Review 2026-01-17](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/bugs/adversarial-review-2026-01-17.md)
  - 3 spec drift issues
  - 9 missing test scenarios
  - 2 inappropriate mock patterns
  - 5 bugs (3 P2, 2 P3)

## How to Add Bug Reports

1. Create a new markdown file: `bug-XXX-short-description.md` (preferred) or `bug-YYYY-MM-DD-short-description.md`
2. Use the template below
3. Link from this README

### Bug Report Template

```markdown
# Bug: [Short Title]

**Priority:** P0/P1/P2/P3/P4
**Status:** Open/In Progress/Fixed/Won't Fix
**Found:** YYYY-MM-DD
**Fixed:** YYYY-MM-DD (if applicable)
**Commit:** (fix commit hash)

## Description

Clear description of the bug.

## Steps to Reproduce

1. Step one
2. Step two
3. ...

## Expected Behavior

What should happen.

## Actual Behavior

What actually happens.

## Root Cause

Technical explanation.

## Fix

Description of the fix or link to PR.

## Related

- Related issues
- Related specs
```
