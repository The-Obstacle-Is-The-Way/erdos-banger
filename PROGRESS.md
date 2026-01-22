# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-22
**Status:** Ready - Clean Code / SOLID Debt Sweep
**Branch:** ralph-wiggum-v2.2 (create from `dev` before starting)
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Operating Rules (SSOT)

1. **One task per iteration** (never batch)
2. **TDD required**: add a failing test before production code for behavior changes
3. **No reward hacks**
   - never delete/disable tests to "make CI green"
   - never mock the unit under test (mock boundaries only: network/subprocess/time)
   - never lower quality gates (coverage/lint/mypy)
4. **Checkpoint discipline**
   - commit after each completed task
   - push after each commit (remote is the backup)
5. **Escalate early** (stop and request human review) if:
   - a debt doc contradicts SSOT / code reality
   - the change exceeds ~500 LOC or >10 files for a single task (split into subtasks)
   - quality gates fail after 3 fix attempts for the same root cause

---

## Active Queue (Debt Before Specs)

Work strictly top-to-bottom unless blocked by dependencies.

- [ ] **DEBT-059**: CodeRabbit PR#17 fixes (input validation + invariant bugs)
  Deck: `docs/debt/debt-059-coderabbit-pr17-fixes.md`
- [ ] **DEBT-046**: CLIOutput `success=false` with exit code 0 ambiguity (search IndexEmpty)
  Deck: `docs/debt/debt-046-clioutput-success-vs-exitcode.md`
- [ ] **DEBT-056**: FallbackProvider catches `Exception` broadly (may hide provider bugs)
  Deck: `docs/debt/debt-056-fallback-provider-broad-exceptions.md`
- [ ] **DEBT-058**: MD5 `# noqa: S324` in loop module (justify or replace)
  Deck: `docs/debt/debt-058-md5-noqa-in-loop.md`
- [ ] **DEBT-047**: Loop run logs are unsanitized/duplicated (LoopLogger vs RunLogger)
  Deck: `docs/debt/debt-047-loop-logging-sanitization-and-unification.md`
- [ ] **DEBT-057**: Add CI guardrails against god-file regressions
  Deck: `docs/debt/debt-057-guardrails-against-god-files.md`
- [ ] **DEBT-042**: Loop contract drift + `core/loop.py` god function
  Deck: `docs/debt/debt-042-loop-command-contract-and-god-module.md`
- [ ] **DEBT-043**: `erdos search` command god module
  Deck: `docs/debt/debt-043-search-command-god-module.md`
- [ ] **DEBT-045**: Split `SearchIndexProtocol` (ISP/DIP)
  Deck: `docs/debt/debt-045-searchindexprotocol-interface-segregation.md`
- [ ] **DEBT-049**: `SearchIndex` monolith (schema + indexing + retrieval + embeddings)
  Deck: `docs/debt/debt-049-search-index-monolith.md`
- [ ] **DEBT-052**: `erdos ingest` command god module
  Deck: `docs/debt/debt-052-ingest-command-god-module.md`
- [ ] **DEBT-050**: `core/ingest/fetch.py` SRP split (thin orchestrator + adapters)
  Deck: `docs/debt/debt-050-ingest-fetch-srp.md`
- [ ] **DEBT-054**: Run logger OCP violation (central `if command == ...` chain)
  Deck: `docs/debt/debt-054-run-logger-ocp-violation.md`
- [ ] **DEBT-053**: `core/formal_conjectures.py` monolith
  Deck: `docs/debt/debt-053-formal-conjectures-module-monolith.md`
- [ ] **DEBT-051**: `core/batch.py` SRP split
  Deck: `docs/debt/debt-051-batch-module-srp.md`
- [ ] **DEBT-048**: MCP server module size + CI coverage gap
  Deck: `docs/debt/debt-048-mcp-server-god-module-and-ci-coverage.md`
- [ ] **DEBT-055**: Scattered env-based configuration (hidden dependencies)
  Deck: `docs/debt/debt-055-configuration-scattered-env-deps.md`
- [ ] **DEBT-044**: `core/` bounded-context refactor (reduce sprawl)
  Deck: `docs/debt/debt-044-core-bounded-context-refactor.md`

---

## Work Log

(Ralph appends a short entry per completed task.)
