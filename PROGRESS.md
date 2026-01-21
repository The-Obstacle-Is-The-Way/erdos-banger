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

- [x] **DEBT-036**: Marker device selection not exposed (P3)
  - Deck: `docs/_archive/debt/debt-036-marker-mps-not-configured.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

---

### Spec Items (v2.1 Architecture)

- [x] **SPEC-022**: MetadataProvider Orchestration
  - Spec: `docs/_archive/specs/spec-022-metadata-provider-orchestration.md`
  - ADR: `docs/adr/adr-001-metadata-provider-orchestration.md`
  - Resolves: DEBT-038
  - Target: v2.1
  - Acceptance: All spec acceptance criteria met; `make ci` green.

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

### DEBT-036: Marker device selection not exposed - FIXED

**Commit:** 7005b65

Added `--device` CLI option to `erdos convert` command for selecting torch device (cpu/cuda/mps) for Marker PDF conversions. The option sets `TORCH_DEVICE` env var which Marker uses for device selection.

**Implementation:**
- Added `torch_device: str | None` field to `PDFConversionConfig` dataclass
- Added `--device` / `-d` option to `erdos convert` command with help text documenting supported devices
- `convert_pdf()` sets `TORCH_DEVICE` env var when `torch_device` is specified
- TDD approach: wrote failing tests first, then implemented

**Files added/modified:**
- `src/erdos/core/pdf_converter.py` (added torch_device field and env var wiring)
- `src/erdos/commands/convert.py` (added --device option)
- `tests/unit/test_pdf_converter.py` (added config and env var tests)
- `tests/integration/test_pdf_convert.py` (added help output test)
- `docs/debt/README.md` (moved DEBT-036 to archived)
- `docs/_archive/debt/debt-036-marker-mps-not-configured.md` (archived)

### SPEC-022: MetadataProvider Orchestration - COMPLETE

**Commit:** 6e599a1

Implemented the MetadataProvider abstraction following ADR-001 (Ports + Provider Chain architecture). All acceptance criteria satisfied:

1. `MetadataProvider` protocol in `src/erdos/core/ports.py` (lines 23-68)
2. `OpenAlexProvider` wrapper in `src/erdos/core/providers/openalex.py`
3. `CrossrefProvider` wrapper in `src/erdos/core/providers/crossref.py`
4. `FallbackProvider` chain in `src/erdos/core/providers/fallback.py`
5. `build_metadata_provider(mailto, timeout)` factory in `src/erdos/core/context.py`
6. `ingest/fetch.py` accepts `MetadataProvider` via dependency injection (`provider` parameter)
7. Unit tests with mock providers in `tests/unit/test_providers.py`
8. Integration tests in `tests/integration/test_providers_network.py` (marked `requires_network`)

**This resolves DEBT-038** - the ingest layer now depends on the `MetadataProvider` protocol, not concrete clients.

**Files added/modified:**
- `src/erdos/core/ports.py` (MetadataProvider protocol added)
- `src/erdos/core/providers/__init__.py` (new package)
- `src/erdos/core/providers/openalex.py` (new)
- `src/erdos/core/providers/crossref.py` (new)
- `src/erdos/core/providers/fallback.py` (new)
- `src/erdos/core/context.py` (updated with build_metadata_provider)
- `src/erdos/core/ingest/fetch.py` (accepts provider parameter)
- `tests/unit/test_providers.py` (new)
- `tests/integration/test_providers_network.py` (new)
- `docs/specs/spec-022-metadata-provider-orchestration.md` (status → Complete)
- `docs/adr/adr-001-metadata-provider-orchestration.md` (status → Accepted)
- `docs/debt/debt-038-metadata-provider-abstraction.md` (status → Resolved)
- `docs/specs/README.md` (updated)
- `docs/debt/README.md` (updated)
- `docs/adr/README.md` (updated)

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
