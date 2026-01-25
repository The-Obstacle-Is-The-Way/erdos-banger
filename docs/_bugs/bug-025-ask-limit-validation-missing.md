# Bug: `erdos ask --limit` accepts invalid values (0, negative) silently

**Priority:** P2
**Status:** Open
**Found:** 2026-01-25
**Fixed:** (not yet)
**Commit:** (pending)

## Description

The `erdos ask` command accepts `--limit 0` and negative values without error, silently returning zero sources instead of validating the input.

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

And remove the defensive `max(limit, 0)` in retrieval.py since validation will prevent invalid values.

## Related

- `src/erdos/commands/ask.py:156`
- `src/erdos/core/ask/retrieval.py:136` (defensive workaround)
- `src/erdos/commands/list_cmd.py:153-162` (correct pattern)
