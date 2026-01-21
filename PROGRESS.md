# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-21
**Status:** Ready - v2.1 Architecture Sprint
**Branch:** ralph-wiggum-v2.1
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Operating Rules (SSOT)

1. **One task per iteration** (never batch)
2. **TDD required**: add a failing test before production code
3. **No reward hacks**:
   - never delete/disable tests to "make CI green"
   - never mock the unit under test (mock only boundaries: network/subprocess/time)
   - never lower quality gates (coverage, lint, mypy)
4. **Checkpoint discipline**:
   - commit after each completed task
   - push after each commit (remote is the backup)
5. **Escalate early** (stop and request human review) if:
   - a spec is ambiguous or contradicts SSOT
   - required deps are missing / incompatible
   - quality gates fail after 3 fix attempts
   - the change would exceed ~500 LoC or touch >10 files for a single task

## Active Queue

### Priority Order: Debt Before Specs

Fix architectural debt first, then implement new features.

---

### Debt Items (Ordered to unblock SPEC-022)

- [x] **DEBT-041**: `ports.py` leaks concrete `search_index` types (P3)
  - Deck: `docs/_archive/debt/debt-041-ports-leak-search-index-types.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-039**: `erdos lean` command module is a god file (P2)
  - Deck: `docs/_archive/debt/debt-039-lean-command-god-module.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-040**: `src/erdos/core/` module sprawl (P3)
  - Deck: `docs/_archive/debt/debt-040-core-package-module-sprawl.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-036**: Marker device selection not exposed (P3)
  - Deck: `docs/debt/debt-036-marker-mps-not-configured.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

---

### Spec Items (v2.1 Architecture)

- [ ] **SPEC-022**: MetadataProvider Orchestration
  - Spec: `docs/specs/spec-022-metadata-provider-orchestration.md`
  - ADR: `docs/adr/adr-001-metadata-provider-orchestration.md`
  - Resolves: DEBT-038
  - Target: v2.1
  - Acceptance: All spec acceptance criteria met; `make ci` green.
  - Note: This is a multi-step spec. Break into subtasks if needed:
    - SPEC-022-A: Add MetadataProvider protocol to ports.py
    - SPEC-022-B: Create providers/ package with OpenAlexProvider
    - SPEC-022-C: Create CrossrefProvider wrapper
    - SPEC-022-D: Create FallbackProvider
    - SPEC-022-E: Add build_metadata_provider() to context.py
    - SPEC-022-F: Refactor ingest/fetch.py to accept provider
    - SPEC-022-G: Add unit tests for providers
    - SPEC-022-H: Add integration tests (requires_network)

---

## Guidelines

- **DEBT-* tasks follow TDD** - write tests for new behavior BEFORE refactoring
- **Pure refactors** should not change behavior - existing tests must pass
- **One task per iteration** - do not batch tasks
- **Quality gates must pass** before marking complete
- **Atomic commits** with proper format: `[DEBT-XXX] Type: description`
- **For SPEC-022**: Break into subtasks if needed (>500 LoC or >10 files)

---

## Work Log

### 2026-01-21: Architecture Audit Complete

**External audit performed.** Deliverables added:

- ADR-001: Metadata Provider Orchestration (Ports + Provider Chain)
- SPEC-022: MetadataProvider Orchestration (corrected from first draft)
- DEBT-041: `ports.py` leaks concrete `search_index` types

**Files added/modified:**
- `docs/adr/README.md` (new)
- `docs/adr/adr-001-metadata-provider-orchestration.md` (new)
- `docs/specs/spec-022-metadata-provider-orchestration.md` (corrected)
- `docs/debt/debt-041-ports-leak-search-index-types.md` (new)
- `docs/debt/README.md` (updated)
- `docs/specs/README.md` (updated)
- `docs/INDEX.md` (updated)

(entries added by Ralph loop as tasks complete)

### DEBT-039: `erdos lean` command module is a god file - FIXED

**Commit:** 8540017

Split the god module `src/erdos/commands/lean.py` (~1.4k LOC) into a well-organized package `src/erdos/commands/lean/` with focused submodules. Extracted batch formalize logic into `batch_formalize.py` to keep `formalize_cmd.py` under 300 LOC.

**Final module sizes:**
- `__init__.py`: 25 LOC
- `init_cmd.py`: 79 LOC
- `check_cmd.py`: 95 LOC
- `prove_cmd.py`: 160 LOC
- `common.py`: 176 LOC
- `batch_formalize.py`: 226 LOC (new)
- `status_cmd.py`: 257 LOC
- `formalize_cmd.py`: 269 LOC
- `import_cmd.py`: 316 LOC (justified: well-factored with thin CLI callback)

**Files added/modified:**
- `src/erdos/commands/lean.py` (deleted)
- `src/erdos/commands/lean/__init__.py` (new)
- `src/erdos/commands/lean/common.py` (new)
- `src/erdos/commands/lean/init_cmd.py` (new)
- `src/erdos/commands/lean/check_cmd.py` (new)
- `src/erdos/commands/lean/formalize_cmd.py` (new)
- `src/erdos/commands/lean/batch_formalize.py` (new)
- `src/erdos/commands/lean/status_cmd.py` (new)
- `src/erdos/commands/lean/import_cmd.py` (new)
- `src/erdos/commands/lean/prove_cmd.py` (new)
- `docs/debt/README.md` (updated)
- `docs/_archive/debt/debt-039-lean-command-god-module.md` (archived)

### DEBT-041: `ports.py` leaks concrete `search_index` types - FIXED

**Commit:** e27e5a3

Created `src/erdos/core/search/types.py` with contract types (`EmbeddingModelProtocol`, `SearchResult`, `SemanticSearchResult`). Updated `ports.py` to import from `search.types` instead of `search_index`. Updated `search_index.py` to import and re-export for backward compatibility.

**Files added/modified:**
- `src/erdos/core/search/__init__.py` (new)
- `src/erdos/core/search/types.py` (new)
- `src/erdos/core/ports.py` (updated imports)
- `src/erdos/core/search_index.py` (updated imports, added re-exports)
- `docs/debt/README.md` (moved to archived)
- `docs/_archive/debt/debt-041-ports-leak-search-index-types.md` (archived)

### DEBT-040: `src/erdos/core/` module sprawl - FIXED

**Commit:** 994b99c

Documentation-only fix (Option A from the deck). Added "Core package boundaries" section to CLAUDE.md documenting:
- Existing bounded contexts: `ask/`, `ingest/`, `models/`, `search/`
- Top-level modules (legacy exceptions)
- Rules for new code: no new top-level modules, infra adapters go in `core/clients/` or `core/adapters/`

**Files added/modified:**
- `CLAUDE.md` (added "Core package boundaries" section)
- `docs/debt/README.md` (updated: moved DEBT-040 to archived)
- `docs/_archive/debt/debt-040-core-package-module-sprawl.md` (archived with acceptance criteria checked)

---

## Completion Criteria

The queue is complete when:
1. All `[ ]` items in Active Queue are `[x]`
2. `make ci` passes
3. `make smoke` passes
4. All debt documents updated with "Fixed" status and commit hashes
5. All spec documents updated with "Complete" status and commit hashes

The loop operator verifies completion via this file's state (no unchecked items), not by parsing model output.

---

## Rollback / Recovery

- Abort the loop: stop the process / kill the tmux session.
- Inspect current state: `git status`, `git log -10 --oneline`.
- To undo the last commit (keep working tree changes): `git reset --soft HEAD~1`
- To undo the last commit (discard working tree changes): `git reset --hard HEAD~1`
- To revert a commit on a shared branch: `git revert <sha>`
