# Bug: `erdos ask --limit` accepts invalid values (0, negative) silently

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 92039ca

## Description

The `erdos ask` command accepted `--limit 0` and negative values without error, silently returning zero sources instead of validating the input.

## Steps to Reproduce

1. Run `uv run erdos ask 42 "What is this?" --limit 0 --no-llm`
2. Or run `uv run erdos ask 42 "What is this?" --limit -1 --no-llm`

## Expected Behavior

A validation error like:
```
Invalid value for '--limit' / '-n': 0 is not in the range x>=1.
```

## Actual Behavior

```
Retrieving sources for Problem 42...

Problem 42
Question: test

Retrieved 0 sources:
  (no sources found)

No answer generated (prompt-only mode)
```

The command succeeds but returns no sources, which is misleading because the problem *does* have sources when using a valid limit.

## Root Cause

In `src/erdos/commands/ask.py` line 156:

```python
limit: Annotated[int, typer.Option("--limit", "-n")] = DEFAULT_RAG_LIMIT,
```

No Typer validation constraints are applied. The defensive code in `src/erdos/core/ask/retrieval.py` line 136 silently handles this:

```python
return sources[: max(limit, 0)]
```

This `max(limit, 0)` converts negative/zero values to 0, returning an empty list without user feedback.

## Fix

Add Typer validation to the limit parameter:

```python
limit: Annotated[int, typer.Option("--limit", "-n", min=1)] = DEFAULT_RAG_LIMIT,
```

Note: The defensive `max(limit, 0)` in `retrieval.py` can remain as a core-level guard; the CLI validation prevents invalid user input.

## Related

- `src/erdos/commands/ask.py`
- `src/erdos/core/ask/retrieval.py` (defensive workaround)
- `src/erdos/commands/list_cmd.py` (reference pattern)
