# Bug: zbMATH commands accept invalid pagination/year ranges

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 6c7eef2

## Description

The zbMATH-backed commands accept invalid values for pagination and year filtering and pass them through to the zbMATH API, which returns cryptic HTTP errors (400/404) instead of a clean CLI validation error.

This affects:
- `erdos refs zbmath` (`--limit 0`, negative limits; invalid `--year-min/--year-max` ranges)
- `erdos search --msc` (invalid `--year-min/--year-max` ranges)

## Steps to Reproduce

1. Run `uv run erdos refs zbmath --msc "11B05" --limit 0`
2. Run `uv run erdos refs zbmath --msc "11B05" --year-min 2020 --year-max 2010 --limit 1`
3. Run `uv run erdos search --msc "11B05" --year-min 2020 --year-max 2010 --limit 1`

## Expected Behavior

- Invalid `--limit` values should fail fast with Click/Typer validation (no network call).
- Invalid year ranges should error clearly (e.g., "`--year-min` must be <= `--year-max`") with exit code 2.

## Actual Behavior

`erdos refs zbmath --msc "11B05" --limit 0`:

```text
Error: zbMATH API error: 400 Client Error: Bad Request for url: ...results_per_page=0
```

`erdos refs zbmath --msc "11B05" --year-min 2020 --year-max 2010 --limit 1`:

```text
Error: zbMATH API error: 404 Client Error: Not Found for url: ...search_string=...py:2020-2010...
```

`erdos search --msc "11B05" --year-min 2020 --year-max 2010 --limit 1` shows the same 404 pattern.

## Root Cause

In `src/erdos/commands/refs_zbmath.py`, `--limit` has no Typer constraints and the command does not validate `year_min` / `year_max` ordering. Invalid values are forwarded to `ZbMathClient.search_by_msc()`, which constructs the query string and passes it to the zbMATH Open API, which rejects invalid pagination / ranges.

`src/erdos/commands/search.py` MSC mode similarly forwards invalid year ranges to the zbMATH client without validation.

## Fix

Implemented in commit `6c7eef2`:

1. Added Typer validation constraints to `erdos refs zbmath --limit` (`min=1, max=1000`).
2. Validated `--year-min/--year-max` ordering when `--msc` is used (reject `year_min > year_max`) in:
   - `erdos refs zbmath`
   - `erdos search --msc`
3. Added regression tests for the failing cases in `tests/integration/test_cli_validation.py`.

## Related

- `src/erdos/commands/refs_zbmath.py`
- `src/erdos/commands/search.py`
- `src/erdos/core/clients/zbmath.py`
