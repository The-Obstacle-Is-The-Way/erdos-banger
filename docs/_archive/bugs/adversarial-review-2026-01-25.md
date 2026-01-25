# Adversarial Review: 2026-01-25

**Scope:** Full CLI stress test and input validation audit
**Duration:** ~30 minutes of automated testing
**Status:** Complete

## Summary

Comprehensive stress test of all CLI commands and flags. Found **6 bugs** (1 P1, 3 P2, 2 P3), all related to missing input validation. The codebase is generally robust - 1555 unit tests pass, linting and type checking clean.

## Resolution

All six bugs (BUG-023..BUG-028) were fixed in commit `92039ca` and their bug decks archived under `docs/_archive/bugs/`.

## Bugs Found

### P1 (High Priority)

| ID | Title | Command | Root Cause |
|----|-------|---------|------------|
| BUG-023 | Path duplication causes crash | `erdos lean import` | `get_local_file_path` returns path with project prefix, then `LeanRunner._resolve_lean_path` prepends it again |

### P2 (Medium Priority)

| ID | Title | Command | Root Cause |
|----|-------|---------|------------|
| BUG-024 | Traceback on invalid limit | `erdos search --limit 0` | Missing Typer `min=1` constraint; late validation in SearchOptions throws ValueError |
| BUG-025 | Silently accepts invalid limit | `erdos ask --limit 0` | Missing Typer `min=1` constraint; defensive `max(limit, 0)` returns empty list |
| BUG-026 | Cryptic API error on invalid limit | `erdos refs s2 --limit 0` | Missing Typer `min=1` constraint; API rejects with 400 |

### P3 (Low Priority)

| ID | Title | Command | Root Cause |
|----|-------|---------|------------|
| BUG-027 | Invalid log levels ignored | `--log-level INVALID` | No validation on log level enum |
| BUG-028 | Negative limits accepted | `--all --limit -5` | Missing `min=1` constraint on optional batch limit |

## Pattern Analysis

The bugs follow a common pattern: **inconsistent input validation across commands**.

- `erdos list` correctly validates `--limit` with `min=1, max=1000`
- Other commands (`search`, `ask`, `refs s2`, `ingest`, `formalize`) lack equivalent validation
- Some have late validation (SearchOptions.__post_init__), others have defensive code (max(limit, 0)), others pass to external APIs

**Recommendation:** Audit all `--limit` options and add consistent Typer constraints matching the `list` command pattern.

## Commands Tested

| Command | Status | Notes |
|---------|--------|-------|
| `erdos list` | PASS | Proper validation |
| `erdos show` | PASS | Handles not found correctly |
| `erdos search` | BUG-024 | Missing limit validation |
| `erdos ask` | BUG-025 | Missing limit validation |
| `erdos refs problem` | PASS | |
| `erdos refs s2 *` | BUG-026 | Missing limit validation |
| `erdos refs zbmath` | PASS | |
| `erdos ingest` | BUG-028 | Batch limit accepts negative |
| `erdos lean init` | PASS | |
| `erdos lean check` | PASS | |
| `erdos lean formalize` | BUG-028 | Batch limit accepts negative |
| `erdos lean import` | BUG-023 | Path duplication |
| `erdos lean prove` | PASS | |
| `erdos lean status` | PASS | |
| `erdos loop run` | PASS | Proper validation |
| `erdos convert` | PASS | |
| `erdos logs` | PASS | Proper validation |
| `erdos research *` | PASS | |
| `erdos sync *` | PASS | |
| `erdos dashboard` | PASS | Proper validation |
| `--log-level` | BUG-027 | Invalid values ignored |
| `--json` | PASS | Works correctly |

## CI Status

```
make lint     ✅ All checks passed
make typecheck ✅ Success: no issues found in 328 source files
make test     ✅ 1555 passed, 2 skipped, 56 deselected
make audit    ✅ Code health audit passed (9 exempted violations)
```

## Recommendations

1. **Standardize limit validation** - Create a shared pattern or utility for limit options
2. **Add edge case tests** - None of the existing tests cover `--limit 0` or `--limit -1`
3. **Fix BUG-023 first** - It's the only P1 and blocks `lean import` functionality entirely
4. **Consider using enums** - For constrained string options like `--log-level`, `--status`

## Files Changed in This Review

- `docs/bugs/README.md` - Updated with new bugs
- `docs/bugs/bug-023-lean-import-path-duplication.md` - New
- `docs/bugs/bug-024-search-limit-validation-missing.md` - New
- `docs/bugs/bug-025-ask-limit-validation-missing.md` - New
- `docs/bugs/bug-026-refs-s2-limit-validation-missing.md` - New
- `docs/bugs/bug-027-log-level-invalid-values-ignored.md` - New
- `docs/bugs/bug-028-batch-limit-negative-values-accepted.md` - New
- `docs/bugs/adversarial-review-2026-01-25.md` - This file
