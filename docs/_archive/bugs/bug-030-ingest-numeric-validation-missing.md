# Bug: `erdos ingest` accepts invalid numeric values (tracebacks / surprising batch selection)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 6c7eef2

## Description

`erdos ingest` accepts invalid values for several numeric flags. Some invalid values trigger a Rich traceback (uncaught `ValueError`), while others produce surprising behavior due to Python slicing semantics in batch mode.

## Steps to Reproduce

1. Run `uv run erdos ingest 1 --delay -1 --no-network --no-download`
2. Run `uv run erdos ingest 1 --timeout 0 --no-network --no-download`
3. Run `uv run erdos ingest --all --skip -1 --dry-run`

## Expected Behavior

- Clean Typer/Click validation errors (exit code 2) for:
  - `--delay < 0`
  - `--timeout <= 0`
  - `--skip < 0`

## Actual Behavior

`erdos ingest 1 --delay -1 ...`:

```text
Traceback ...
ValueError: delay must be >= 0
```

`erdos ingest 1 --timeout 0 ...`:

```text
Traceback ...
ValueError: timeout must be > 0
```

`erdos ingest --all --skip -1 --dry-run`:

```text
Dry run: Would process 1 problems
  Problem IDs: [<last problem id>]
```

## Root Cause

In `src/erdos/commands/ingest.py`, the Typer options for `--delay`, `--timeout`, and `--skip` lack constraints/validation.

- `--delay` and `--timeout` are passed into core ingestion configuration. `FetchConfig.__post_init__()` in `src/erdos/core/ingest/config.py` validates these values and raises `ValueError`, which bubbles up as a CLI traceback.
- `--skip` is used in batch filtering (via `BatchFilters.skip`). In `src/erdos/core/batch/models.py`, filtering uses Python slicing (`results[skip:]`), where negative skip values select items from the end of the list.

## Fix

Implemented in commit `6c7eef2`:

- Added CLI validation for:
  - `--delay` (must be `>= 0`)
  - `--timeout` (must be `> 0` when provided)
  - `--skip` (must be `>= 0` when provided)
- Added regression tests covering `--delay -1`, `--timeout 0`, and `--skip -1` (exit code 2; no traceback).

## Related

- `src/erdos/commands/ingest.py`
- `src/erdos/core/ingest/config.py`
- `src/erdos/core/batch/models.py`
