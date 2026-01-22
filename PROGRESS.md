# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-22
**Status:** Ready - Debt First (Search/Loop Cleanups)
**Branch:** ralph-wiggum-v2.4 (create from `dev` before starting)
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

- [x] **DEBT-061**: Remove core backward-compatibility shims
  Deck: `docs/_archive/debt/debt-061-remove-core-compatibility-shims.md`
- [x] **DEBT-060**: Formalize command long Typer callback
  Deck: `docs/_archive/debt/debt-060-formalize-cmd-long-callback.md`
- [ ] **DEBT-062**: Split `core/search/service.py` god-module (remove stale exemption)
  Deck: `docs/debt/debt-062-search-service-god-module.md`
- [ ] **DEBT-064**: Inject LLM executor into loop runner (DIP)
  Deck: `docs/debt/debt-064-loop-runner-dip.md`
- [ ] **DEBT-063**: Split `MetadataProvider` protocol (ISP)
  Deck: `docs/debt/debt-063-metadata-provider-isp.md`
- [ ] **DEBT-065**: Move loop orchestration out of command layer (SRP)
  Deck: `docs/debt/debt-065-thick-cli-callbacks.md`

---

## Work Log

- **2026-01-22 (DEBT-060)**: Refactored `formalize_cmd.py` to reduce function LOC. Extracted `_FormalizeArgs` dataclass, `_validate_args()` and `_execute_formalize()` helpers. `register()` now 80 LOC (from 194), `formalize()` now 76 LOC (from 190). Removed DEBT-060 exemptions from audit script. `make ci` passes.
- **2026-01-22 (DEBT-061)**: Removed 10 backward-compatibility shim files from `src/erdos/core/` and updated all imports to use bounded-context modules directly. Added regression guard tests in `test_dependencies.py`. `make ci` passes.
