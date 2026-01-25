# Bug: `erdos search --limit` crashes with traceback for invalid values

**Priority:** P2
**Status:** Open
**Found:** 2026-01-25
**Fixed:** (not yet)
**Commit:** (pending)

## Description

The `erdos search` command shows an ugly Python traceback when `--limit 0` or `--limit -1` (or other invalid values) is provided, instead of showing a user-friendly validation error like the `erdos list` command does.

## Steps to Reproduce

1. Run `uv run erdos search "test" --limit 0`
2. Or run `uv run erdos search "test" --limit -5`

## Expected Behavior

A clean validation error like:
```
Invalid value for '--limit' / '-n': 0 is not in the range 1<=x<=1000.
```

(This is what `erdos list --limit 0` shows.)

## Actual Behavior

```
Traceback (most recent call last):
  ...
  File ".../src/erdos/core/search/options.py", line 33, in __post_init__
    raise ValueError("limit must be greater than 0")
ValueError: limit must be greater than 0
```

## Root Cause

In `src/erdos/commands/search.py` lines 330-333:

```python
limit: Annotated[
    int,
    typer.Option("--limit", "-n", help="Maximum results to return"),
] = DEFAULT_SEARCH_LIMIT,
```

The `limit` parameter lacks Typer validation constraints (`min=1`, `max=1000`).

Compare to `src/erdos/commands/list_cmd.py` lines 153-162 which correctly validates:

```python
limit: Annotated[
    int,
    typer.Option(
        "--limit",
        "-n",
        help="Maximum number of results",
        min=1,
        max=1000,
    ),
] = 100,
```

## Fix

Add Typer validation constraints to the limit parameter:

```python
limit: Annotated[
    int,
    typer.Option("--limit", "-n", help="Maximum results to return", min=1, max=1000),
] = DEFAULT_SEARCH_LIMIT,
```

## Related

- `src/erdos/commands/search.py:330-333`
- `src/erdos/commands/list_cmd.py:153-162` (correct pattern)
- `src/erdos/core/search/options.py:30-33` (late validation)
