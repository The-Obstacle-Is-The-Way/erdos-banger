# Bug Reports & Adversarial Reviews

This directory contains bug reports, adversarial code reviews, and quality audits for the erdos-banger project.

## Reviews

| Date | Type | Summary | Status |
|------|------|---------|--------|
| 2026-01-22 | Adversarial Review | Post v2.1 architecture audit (loop/search SRP hotspots) | Archived |
| 2026-01-21 | Adversarial Review | Full codebase audit for bugs, debt, anti-patterns | Archived |
| 2026-01-17 | Adversarial Review | Full codebase audit covering specs 003-006 | Archived |

## Active Bugs

*None currently active.*

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

**Next Bug ID:** BUG-021

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
- `docs/_archive/bugs/bug-002-search-build-index-json-stdout.md`
- `docs/_archive/bugs/bug-003-search-fts-loader-missing.md`
- `docs/_archive/bugs/bug-004-iter-problems-duplicate-ids.md`
- `docs/_archive/bugs/bug-005-dead-global-flags.md`
- `docs/_archive/bugs/bug-006-ruff-lints-submodule.md`
- `docs/_archive/bugs/bug-018-openalex-client-broken.md`
- `docs/_archive/bugs/bug-019-convert-format-no-op.md`
- `docs/_archive/bugs/bug-020-openalex-get-by-arxiv-returns-none.md`

## Bug Priority Definitions

| Priority | Definition | Response Time |
|----------|------------|---------------|
| **P0** | Critical - Data loss, security vulnerability, crashes | Immediate |
| **P1** | High - Major functionality broken, blocks users | Next release |
| **P2** | Medium - Feature partially broken, workaround exists | Soon |
| **P3** | Low - Minor issues, cosmetic, edge cases | When convenient |
| **P4** | Enhancement - Nice to have, quality of life | Backlog |

## Quick Links

- [Adversarial Review 2026-01-21](../_archive/bugs/adversarial-review-2026-01-21.md)
  - 2 confirmed bugs (1 P1, 1 P2) - 3 false positives invalidated
  - 7 technical debt items (4 P2, 3 P3)
  - Focus: silent failures, observability gaps, API robustness
- [Adversarial Review 2026-01-22](../_archive/bugs/adversarial-review-2026-01-22.md)
  - No new correctness bugs found under `make ci`
  - 2 active debt items filed (loop + search SRP pressure)
- [Adversarial Review 2026-01-17](../_archive/bugs/adversarial-review-2026-01-17.md)
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
