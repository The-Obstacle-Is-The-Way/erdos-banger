# Bug: `erdos refs s2 --limit 0` causes cryptic API error

**Priority:** P2
**Status:** Open
**Found:** 2026-01-25
**Fixed:** (not yet)
**Commit:** (pending)

## Description

The `erdos refs s2 citations` (and other s2 subcommands) accept `--limit 0` without validation, passing the invalid value to the Semantic Scholar API which returns a 400 Bad Request error with a cryptic message.

## Steps to Reproduce

1. Run `uv run erdos refs s2 citations "10.1016/j.jnt.2004.08.012" --limit 0`

## Expected Behavior

A validation error like:
```
Invalid value for '--limit': 0 is not in the range x>=1.
```

## Actual Behavior

```
Error: Semantic Scholar API error: 400 Client Error: Bad Request for url:
https://api.semanticscholar.org/graph/v1/paper/.../citations?...&limit=0
```

The error message doesn't clearly indicate that the `--limit 0` is the problem.

## Root Cause

In `src/erdos/commands/refs_s2.py` lines 178-181, 245-248, 320-323, all three commands (`citations`, `cited-by`, `references`) have:

```python
limit: Annotated[
    int,
    typer.Option("--limit", help="Maximum citations to return."),
] = 10,
```

No `min=1` constraint is applied. The invalid value passes through to the API call, which rejects it.

## Fix

Add Typer validation constraints to all three limit parameters:

```python
limit: Annotated[
    int,
    typer.Option("--limit", help="Maximum citations to return.", min=1),
] = 10,
```

## Related

- `src/erdos/commands/refs_s2.py:178-181` (citations)
- `src/erdos/commands/refs_s2.py:245-248` (cited-by)
- `src/erdos/commands/refs_s2.py:320-323` (references)
- `src/erdos/commands/list_cmd.py:153-162` (correct pattern)
