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

- [x] **DEBT-059**: CodeRabbit PR#17 fixes (input validation + invariant bugs)
  Deck: `docs/_archive/debt/debt-059-coderabbit-pr17-fixes.md`
- [x] **DEBT-046**: CLIOutput `success=false` with exit code 0 ambiguity (search IndexEmpty)
  Deck: `docs/_archive/debt/debt-046-clioutput-success-vs-exitcode.md`
- [x] **DEBT-056**: FallbackProvider catches `Exception` broadly (may hide provider bugs)
  Deck: `docs/_archive/debt/debt-056-fallback-provider-broad-exceptions.md`
- [x] **DEBT-058**: MD5 `# noqa: S324` in loop module (justify or replace)
  Deck: `docs/_archive/debt/debt-058-md5-noqa-in-loop.md`
- [x] **DEBT-047**: Loop run logs are unsanitized/duplicated (LoopLogger vs RunLogger)
  Deck: `docs/_archive/debt/debt-047-loop-logging-sanitization-and-unification.md`
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

### 2026-01-22: DEBT-059 Fixed
- Fixed CLIOutput invariant violation in batch_formalize.py (use CLIOutput.err for partial failures)
- Added max_concurrent validation in formalize_cmd.py (reject < 1)
- Added --no-network validation in formalize_cmd.py (requires --import-upstream)
- Added --device validation in convert.py (cpu/cuda/mps, case-insensitive)
- Fixed --local flag threading in status_cmd.py (pass check_local to _get_all_problems_status)
- Fixed TORCH_DEVICE env var leak in pdf_converter.py (try/finally restore pattern)
- Fixed KeyError risk in lean/common.py (use .get() with fallback)
- Fixed empty exception messages in prove_cmd.py and init_cmd.py (add fallbacks)
- Fixed Lean init exit code to use LEAN_ERROR for LeanRunnerError
- Added tests for all validation cases
- `make ci` passes (850 tests, 81.85% coverage)

### 2026-01-22: DEBT-046 Fixed
- Eliminated `CLIOutput.err(..., code=0)` contract smell for IndexEmpty
- Changed `search_problems_fts` to return `None` when index is empty (signals fallback)
- Updated `_search_with_fallback` and `mcp_search_index` to handle None and fallback to basic search
- Fallback returns `CLIOutput.ok` with `fallback_reason="index_empty"` for unambiguous semantics
- Added tests: `test_empty_index_returns_none`, `test_populated_index_returns_results`, updated fallback test
- `make ci` passes (852 tests, 81.85% coverage)

### 2026-01-22: DEBT-056 Fixed
- FallbackProvider now catches only expected exception types per port contract
- Replaced `except Exception` with `except _EXPECTED_PROVIDER_ERRORS` (RequestException, ValueError)
- Unknown exceptions (RuntimeError, TypeError, AttributeError, etc.) now propagate for fail-fast debugging
- Added 4 tests: `test_propagates_unexpected_exceptions`, `test_propagates_unexpected_exceptions_arxiv`, `test_propagates_unexpected_exceptions_search`, `test_falls_back_on_value_error`
- `make ci` passes (856 tests, 81.89% coverage)

### 2026-01-22: DEBT-058 Fixed
- Replaced insecure MD5 usage in loop.py with safe primitives (Option A from deck)
- `_generate_run_id()`: replaced `hashlib.md5()` with `secrets.token_hex(3)` (consistent with run_logger.py)
- `_file_hash()`: replaced `hashlib.md5()` with `hashlib.sha256()` for file content hashing
- Removed all `# noqa: S324` suppressions from the file
- `make ci` passes (856 tests, 81.90% coverage)

### 2026-01-22: DEBT-047 Fixed
- Added shared `sanitize_secrets()` function to `run_logger.py` for consistent secret redaction
- Sanitizes both key names (api_key, token, secret, password, credential) and string values (API keys, Bearer tokens, Authorization headers)
- Updated `LoopLogger.log_event()` to sanitize data before writing to log files
- Refactored `RunLogEntry._sanitize_args()` to use shared `sanitize_secrets()` function
- Added 4 tests for LoopLogger sanitization + 8 tests for sanitize_secrets function
- `make ci` passes (867 tests, 82.00% coverage)
