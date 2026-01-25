# Bug: Batch commands accept negative `--limit` values

**Priority:** P3
**Status:** Open
**Found:** 2026-01-25
**Fixed:** (not yet)
**Commit:** (pending)

## Description

The batch modes of `erdos ingest` and `erdos lean formalize` accept negative `--limit` values without validation. The behavior is inconsistent - negative values seem to return all items instead of erroring.

## Steps to Reproduce

1. Run `uv run erdos ingest --all --limit -5 --dry-run`
2. Run `uv run erdos lean formalize --all --limit -1 --dry-run`

## Expected Behavior

A validation error like:
```
Invalid value for '--limit': -5 is not in the range x>=1.
```

## Actual Behavior

For `ingest --all --limit -5`:
```
Starting batch ingest...
Dry run: Would process 1 problems
  Problem IDs: [1]
```

For `formalize --all --limit -1`:
```
Dry run: Would formalize 5 problems
  Problem IDs: [1, 6, 42, 100, 316]
```

The commands succeed but the behavior with negative limits is unpredictable - sometimes returning 1 item, sometimes all items.

## Root Cause

In `src/erdos/commands/ingest.py` lines 194-196:

```python
limit: Annotated[
    int | None,
    typer.Option("--limit", help="Max problems to process"),
] = None,
```

And in `src/erdos/commands/lean/formalize_cmd.py` lines 238-240:

```python
limit: Annotated[
    int | None, typer.Option("--limit", help="Max problems to process")
] = None,
```

Neither has validation constraints. The `int | None` type allows None for "no limit", but when an integer is provided, it should be validated as positive.

## Fix

Add conditional validation:

```python
limit: Annotated[
    int | None,
    typer.Option("--limit", help="Max problems to process", min=1),
] = None,
```

Note: Typer's `min=1` should work with `Optional[int]` - it only validates when a value is provided.

## Related

- `src/erdos/commands/ingest.py:194-196`
- `src/erdos/commands/lean/formalize_cmd.py:238-240`
- `src/erdos/core/batch/filters.py` (where filtering happens)
