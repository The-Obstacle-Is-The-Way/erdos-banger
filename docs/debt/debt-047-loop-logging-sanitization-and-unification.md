# DEBT-047: Loop Run Logs Are Unsanitized and Duplicated (LoopLogger vs RunLogger)

**Status:** Open
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Security / observability audit

---

## Summary

We have two logging systems:

- `src/erdos/core/run_logger.py` (command-level logs; includes secret redaction)
- `src/erdos/core/loop.py` `LoopLogger` (loop iteration logs; writes raw prompt/response)

`LoopLogger` currently writes full prompts/responses and does **not** sanitize secrets. Logs are gitignored, but this still matters:
- local disks get copied/backed up,
- contributors may attach logs to issues,
- prompts can include API keys if users paste them.

Also: the existence of two loggers increases long-term drift risk.

---

## Evidence

- `src/erdos/core/loop.py`:
  - `loop_logger.log_event("llm_prompt", …, {"prompt": prompt})`
  - `loop_logger.log_event("llm_response", …, {"response": response, ...})`
- `run_logger` already has recursive secret redaction (used for CLI command logs).

Reproduce:
- Loop log event payloads: `rg -n "log_event\\(\\\"llm_(prompt|response)" src/erdos/core/loop.py`
- RunLogEntry sanitizer: `rg -n \"def _sanitize_args\" src/erdos/core/run_logger.py`

---

## Recommended Fix

1. Add a shared sanitizer utility (or reuse `run_logger` sanitizer) for loop logs.
2. Decide on one of these models:

### Option A: Keep separate log files but share sanitization

- Minimal change: `LoopLogger` sanitizes `data` before writing.

### Option B: Unify logging interfaces

- `LoopLogger` becomes a thin adapter over a shared “structured event logger”.

---

## Acceptance Criteria

1. [ ] Loop log events redact common secret patterns (API keys, tokens, `Authorization:` headers).
2. [ ] Tests prove sanitization works for nested data (prompt + response).
3. [ ] `make ci` passes.

---

## Non-Goals

- Encrypting logs at rest.
- Changing log schema version.
