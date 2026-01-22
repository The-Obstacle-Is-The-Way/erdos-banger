# DEBT-054: `RunLogEntry._extract_result_for_command` Violates OCP (Central `if command == ...` Chain)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-22
**Found By:** OCP / maintainability audit
**Fixed In:** b1637c6

---

## Summary

`src/erdos/core/run_logger.py` is a cohesive logging module, but it contains an extensibility smell:

- `RunLogEntry._extract_result_for_command()` uses a central `if command == "..."` chain to extract command-specific summaries.

Every time we add a new command or change a command’s output schema, we are incentivized to edit this central function. That is an **Open/Closed Principle (OCP)** violation and a classic “architecture drift” trigger.

---

## Evidence

- File size: `wc -l src/erdos/core/run_logger.py` → **449** lines
- Central dispatch chain:
  - Reproduce: `rg -n \"def _extract_result_for_command\" -n src/erdos/core/run_logger.py`

---

## Why This Matters

- **OCP:** run logging should not require modification for every new command (especially as we add v2.x workflow commands).
- **SRP:** the logger is responsible for logging; command-specific summarization is a separate concern.
- **Testability:** it’s harder to unit test per-command summarization when it’s embedded in one method.

---

## Recommended Fix (Registry-Based Summarizers)

Introduce a registry mapping `command -> summarizer(data) -> dict`, with a stable default:

```text
src/erdos/core/run_logger_summaries.py
```

Example pattern:

- `SUMMARIZERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]]`
- `register_summarizer(command: str, fn: Callable[...])`
- Each command module (or its core service) registers its summarizer at import time, OR the composition root registers them explicitly.

This keeps `run_logger.py` stable while allowing new commands without touching the logger internals.

---

## Acceptance Criteria

1. [x] No central `if command == ...` chain remains in `run_logger` (or it becomes a small fallback).
2. [x] Adding a new command summary does not require editing `run_logger.py`.
3. [x] Tests cover at least:
   - default summarizer behavior
   - one registered summarizer end-to-end
4. [x] `make ci` passes.

---

## Non-Goals

- Changing log schema version.
- Moving logs to a database or adding a server.
