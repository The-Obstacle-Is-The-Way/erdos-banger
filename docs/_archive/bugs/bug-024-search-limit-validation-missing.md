# Bug: `erdos search --limit` crashes with traceback for invalid values

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 92039ca

## Description

The `erdos search` command showed a traceback when `--limit 0` or `--limit -1` (or other invalid values) was provided, instead of a user-friendly validation error like `erdos list` does.

## Steps to Reproduce

1. Run `uv run erdos search "test" --limit 0`
2. Or run `uv run erdos search "test" --limit -5`

## Expected Behavior

A clean validation error like:

```text
Invalid value for '--limit' / '-n': 0 is not in the range 1<=x<=1000.
```

(This is what `erdos list --limit 0` shows.)

## Actual Behavior


```text
Traceback (most recent call last):
  ...
  File ".../src/erdos/core/search/options.py", line 33, in __post_init__
    raise ValueError("limit must be greater than 0")
ValueError: limit must be greater than 0
```

## Root Cause

In `src/erdos/commands/search.py`, the `limit` option had no Typer constraints:

```python
limit: Annotated[
    int,
    typer.Option("--limit", "-n", help="Maximum results to return"),
] = DEFAULT_SEARCH_LIMIT,
```

Invalid values then reached `SearchOptions.__post_init__()`, which raised `ValueError`, surfacing as a traceback.

## Fix

Add Typer validation constraints to the limit parameter:

```python
limit: Annotated[
    int,
    typer.Option("--limit", "-n", help="Maximum results to return", min=1, max=1000),
] = DEFAULT_SEARCH_LIMIT,
```

## Related

- `src/erdos/commands/search.py`
- `src/erdos/commands/list_cmd.py` (reference pattern)
- `src/erdos/core/search/options.py` (late validation)
