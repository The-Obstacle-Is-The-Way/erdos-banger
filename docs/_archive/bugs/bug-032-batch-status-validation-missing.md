# Bug: Batch `--status` accepts invalid values (misclassified as NotFound)

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 3ab5c5c

## Description

In batch mode for `erdos ingest` and `erdos lean formalize`, passing an invalid `--status`
value (e.g., `foo`) was accepted and then treated as `unknown`. This produced a misleading
`NotFoundError` (exit code `3`) instead of a usage error (exit code `2`).

## Steps to Reproduce (before fix)

1. Run `uv run erdos --json ingest --all --status foo --dry-run`
2. Run `uv run erdos --json lean formalize --all --status foo --dry-run`

## Expected Behavior

- Exit code `2` with a clear validation error for `--status` listing valid values.

## Actual Behavior (before fix)

- Exit code `3` with JSON error:
  - `type`: `NotFoundError`
  - `message`: `No problems match the given filters`

## Root Cause

- CLI options:
  - `src/erdos/commands/ingest.py` declared `--status` as `TEXT` (no validation).
  - `src/erdos/commands/lean/formalize_cmd.py` declared `--status` as `TEXT` (no validation).
- Batch filtering:
  - `src/erdos/core/batch/models.py` (`filter_problem_ids`) parses the filter value via
    `ProblemStatus.from_string(...)`, which maps unknown strings to `ProblemStatus.UNKNOWN`.
  - The batch command then sees an empty selection and reports `NotFoundError`.

## Fix

Implemented in commit `3ab5c5c`:

- Add Click `Choice` validation for `--status` in:
  - `erdos ingest`
  - `erdos lean formalize`
- Add regression tests to ensure invalid `--status` returns exit code `2` and no traceback.

## Related

- `src/erdos/core/models/problem.py` (`ProblemStatus.from_string`)
- `src/erdos/core/batch/models.py` (`filter_problem_ids`)
- `tests/integration/test_cli_validation.py`
