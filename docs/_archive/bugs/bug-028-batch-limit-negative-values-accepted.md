# Bug: Batch commands accept negative `--limit` values

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 92039ca

## Description

The batch modes of `erdos ingest` and `erdos lean formalize` accept negative `--limit` values without validation. The behavior is inconsistent - negative values seem to return all items instead of erroring.

## Steps to Reproduce

1. Run `uv run erdos ingest --all --limit -5 --dry-run`
2. Run `uv run erdos lean formalize --all --limit -1 --dry-run`

## Expected Behavior

A validation error like:

```text
Invalid value for '--limit': -5 is not in the range x>=1.
```

## Actual Behavior

For `ingest --all --limit -5`:

```text
Starting batch ingest...
Dry run: Would process 1 problems
  Problem IDs: [1]
```

For `formalize --all --limit -1`:

```text
Dry run: Would formalize 5 problems
  Problem IDs: [1, 6, 42, 100, 316]
```

The commands succeed but the behavior with negative limits is unpredictable - sometimes returning 1 item, sometimes all items.

## Root Cause

In `src/erdos/commands/ingest.py` (batch mode):

```python
limit: Annotated[
    int | None,
    typer.Option("--limit", help="Max problems to process"),
] = None,
```

And in `src/erdos/commands/lean/formalize_cmd.py` (batch mode):

```python
limit: Annotated[
    int | None, typer.Option("--limit", help="Max problems to process")
] = None,
```

Neither had validation constraints. The `int | None` type allows None for "no limit", but when an integer is provided, it should be validated as positive.

Downstream, the batch filter logic applies `results[:limit]` (Python slicing) in `src/erdos/core/batch/models.py`, so negative limits produce surprising subsets (e.g., “all but last N”).

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

- `src/erdos/commands/ingest.py`
- `src/erdos/commands/lean/formalize_cmd.py`
- `src/erdos/core/batch/models.py` (filtering/slicing)
