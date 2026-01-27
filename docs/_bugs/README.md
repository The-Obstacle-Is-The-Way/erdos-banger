# Bug Reports & Adversarial Reviews

This directory contains bug reports, adversarial code reviews, and quality audits for the erdos-banger project.

## Reviews

| Date | Type | Summary | Status |
|------|------|---------|--------|
| 2026-01-26 | Architecture Audit | Full codebase audit for SPEC-036/037 (2 bugs: GH-035, GH-036) | Archived |
| 2026-01-26 | Friction Report | CLI maximization test for Problem #848 (1 bug found: BUG-034) | Archived |
| 2026-01-25 | Adversarial Review | Status filter validation audit (1 bug fixed in 3ab5c5c) | Archived |
| 2026-01-25 | Adversarial Review | Post-refactor CLI stress test (no new bugs; expanded regression tests) | Archived |
| 2026-01-25 | Adversarial Review | CLI stress test, input validation audit (6 bugs fixed in 92039ca) | Archived |
| 2026-01-25 | Adversarial Review | Follow-up stress test (2 bugs fixed in 6c7eef2) | Archived |
| 2026-01-22 | Adversarial Review | Post v2.1 architecture audit (loop/search SRP hotspots) | Archived |
| 2026-01-21 | Adversarial Review | Full codebase audit for bugs, debt, anti-patterns | Archived |
| 2026-01-17 | Adversarial Review | Full codebase audit covering specs 003-006 | Archived |

## Active Bugs

| ID | Title | Priority | Status | Component |
|----|-------|----------|--------|-----------|
| BUG-039 | Ingest cannot discover papers - only fetches pre-defined refs | P2 | Phase 1 Fixed | `erdos ingest` |
| BUG-049 | Aristotle CLI integration friction | P2 | Fixed | `erdos lean prove` |
| BUG-047 | PDF converter thread-unsafe env mutation | P1 | Open | `erdos convert` |
| BUG-048 | Subprocess calls missing timeouts | P2 | Fixed | `erdos sync` |

**Note:** BUG-039 core workflow (`erdos refs add` + `erdos ingest`) works. Remaining phases (auto-discovery) are feature requests tracked in DEBT-110.

### Invalidated Bugs

| ID | Title | Reason |
|----|-------|--------|
| BUG-041 | Exa not exposed in CLI | FALSE POSITIVE - `erdos research exa search` works |
| BUG-043 | pdfplumber not installed | FALSE POSITIVE - intentionally optional, graceful degradation |
| BUG-045 | literature/papers/ not gitignored | FIXED - added to .gitignore |
| BUG-046 | `erdos lean` command crashes | FALSE POSITIVE - `erdos lean --help` works; real issue is `lake` not on PATH |

### Research Workflow Status (2026-01-26)

**Core workflow is functional:**

```bash
# Full working pipeline:
uv run erdos refs add 848 --arxiv 2511.16072   # Add paper to problem
uv run erdos ingest 848 --force                # Fetch metadata + download source
cat literature/extracts/arxiv/2511.16072/fulltext.txt # Extracted LaTeX
```

**What Works:**
- ✅ `erdos refs add` - Add arXiv/DOI papers to problems
- ✅ `erdos ingest` - Fetch metadata + download arXiv source
- ✅ `erdos research exa search` - Find papers, create leads
- ✅ PDF download + conversion (marker-pdf >= 1.0.0)

**Feature Requests (not bugs):**
- DEBT-110 Phase 2/3: Auto-discovery mode (`--discover`, `--search`)
- SPEC-036: Lead enrichment pipeline (leads → manifest bridging)

**Impact:** Manual workflow is complete. Auto-discovery is a future enhancement.

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
| BUG-033 | zbMATH search methods don't handle 404 errors | P2 | Fixed | 05bc9ec |
| BUG-034 | `erdos research exa --save-leads` crashes on empty title | P2 | Fixed | 6f9b423 |
| BUG-035 | Lean skeleton template uses outdated Mathlib import path | P2 | Fixed | 36d3518 |
| BUG-040 | Marker PDF conversion broken (marker-pdf API change) | P1 | Fixed | b7ceb6f |
| BUG-042 | Exa API returns empty titles | P2 | Fixed | 8ba6e32 |
| BUG-038 | BM25 search doesn't escape FTS5 special characters | P1 | Fixed | 8c55500 |
| GH-035 | Crossref/S2 clients missing JSONDecodeError handling | P1 | Fixed | json_response.py |
| GH-036 | Hardcoded `logs/loop` path breaks outside repo root | P2 | Fixed (PR#40) | 3575563 |
| BUG-044 | Environment variables not auto-loaded in Python scripts | P2 | Fixed | b43c3a7 |
| BUG-041 | Exa not exposed in CLI | N/A | Invalidated | f5557d7 |
| BUG-043 | pdfplumber not installed | N/A | Invalidated | f5557d7 |
| BUG-045 | literature/papers/ not gitignored | P3 | Fixed | f5557d7 |
| BUG-046 | `erdos lean` command crashes | N/A | Invalidated | 1ed768b |

*Naming: GH-XXX = also tracked on GitHub Issues. BUG-XXX = local docs only. Both systems maintained in parallel.*

**Next Bug ID:** BUG-050 (or GH-XXX if filing on GitHub)

### Active Bug Decks

- `docs/_bugs/bug-039-ingest-no-search-discovery.md` (BUG-039)
- `docs/_bugs/bug-049-aristotle-cli-friction.md` (BUG-049)
- `docs/_bugs/bug-047-pdf-converter-thread-unsafe-env.md` (BUG-047)
- `docs/_bugs/bug-048-subprocess-missing-timeouts.md` (BUG-048)

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
- `docs/_archive/bugs/bug-033-zbmath-search-identifier-404-not-handled.md`
- `docs/_archive/bugs/bug-036-json-decode-error-handling.md`
- `docs/_archive/bugs/bug-037-hardcoded-logs-loop-path.md`
- `docs/_archive/bugs/bug-038-bm25-fts5-query-not-escaped.md`
- `docs/_archive/bugs/bug-034-exa-save-leads-empty-title.md`
- `docs/_archive/bugs/bug-035-lean-skeleton-outdated-import.md`
- `docs/_archive/bugs/bug-042-exa-empty-titles.md`
- `docs/_archive/bugs/bug-044-env-not-auto-loaded.md`
- `docs/_archive/bugs/bug-041-exa-not-exposed-in-cli.md`
- `docs/_archive/bugs/bug-043-pdfplumber-not-installed.md`
- `docs/_archive/bugs/bug-045-literature-papers-not-gitignored.md`
- `docs/_archive/bugs/bug-046-erdos-lean-command-broken.md`
- `docs/_archive/bugs/friction-2026-01-26-cli-maximization-test.md`
- `docs/_archive/bugs/friction-2026-01-26-aristotle-onboarding.md`

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
