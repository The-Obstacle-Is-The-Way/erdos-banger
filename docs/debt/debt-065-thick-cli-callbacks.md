# DEBT-065: Command Layer Still Contains Application Logic (SRP Pressure)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

Several command-layer entrypoints in `src/erdos/commands/` exceed the code-health guardrail `FUNCTION_LOC_THRESHOLD=120` and/or contain orchestration that belongs in the core bounded contexts (application/service layer). This creates SRP pressure:

1. Typer argument parsing
2. Calling service layer
3. Formatting output

In a CLI app, option-heavy signatures will always be “long”; the actionable part of this debt is **keeping application policy out of command modules** (and removing exemptions once the guardrail is satisfied).

---

## Evidence

`scripts/audit_code_health.py --strict` currently reports these command functions as **exempt** long-functions:

```text
src/erdos/commands/convert.py:173 convert(): 159 LOC (threshold: 120)  [EXEMPT]
src/erdos/commands/loop.py:95 execute_loop(): 154 LOC (threshold: 120) [EXEMPT]
src/erdos/commands/ingest.py:152 ingest(): 153 LOC (threshold: 120)    [EXEMPT]
src/erdos/commands/loop.py:257 run(): 140 LOC (threshold: 120)         [EXEMPT]
src/erdos/commands/search.py:198 search(): 139 LOC (threshold: 120)    [EXEMPT]
```

**Key nuance (avoid false positives):**

- `commands/search.py::search()` and `commands/ingest.py::ingest()` are long largely due to **Typer option declarations + docstrings**; their bodies already mostly delegate to core services.
- `commands/loop.py::execute_loop()` is **application orchestration** (Lean project init, skeleton generation, running the loop, mapping statuses). This is the strongest SRP violation in the command layer.

**Guardrail note (SSOT):**

`commands/loop.py::execute_loop()` is currently exempted from the long-function guardrail via an inline docstring marker:

- `src/erdos/commands/loop.py` → `execute_loop()` contains `# exempt: DEBT-042`
- Problem: **DEBT-042 is archived**; the exemption pointer is stale.

This deck’s work should remove the need for that exemption entirely (preferred). If an intermediate step is needed, temporarily update the exemption marker to `DEBT-065`.

---

## Scope (This Deck)

This deck is scoped to removing **command-layer orchestration** by moving it into the appropriate bounded context. It is **not** a crusade to make every Typer callback <50 lines.

---

## Recommended Fix

### 1) Move loop orchestration out of `commands/loop.py`

Create a core service entrypoint (location within the loop bounded-context):

```python
# src/erdos/core/loop/service.py
def execute_proof_loop(
    problem_id: int,
    *,
    repo: ProblemRepository,
    project_path: Path,
    config: LoopConfig,
    llm_command: str | None,
    no_apply: bool,
) -> CLIOutput: ...
```

Then make `src/erdos/commands/loop.py` a thin adapter:

- `run()` parses flags → builds `LoopConfig` → calls `execute_proof_loop()` → `exit_with_result()`
- `execute_loop()` helper disappears from `commands/loop.py` (or becomes a thin wrapper around the core service, but prefer deletion in a greenfield repo)

### 2) Optional follow-ups (separate decks if needed)

- If we want to remove `commands/search.py::search()` and `commands/ingest.py::ingest()` exemptions, revisit the guardrail methodology (Typer signatures inflate AST LOC). Don’t do this in the same change as loop extraction.

---

## Acceptance Criteria

1. [ ] `commands/loop.py` no longer contains loop orchestration (Lean init/skeleton/runner setup)
2. [ ] New core entrypoint exists in `src/erdos/core/loop/` (service/app module) returning `CLIOutput`
3. [ ] `scripts/audit_code_health.py --strict` no longer reports `commands/loop.py:execute_loop` as an exempt long-function (deleted or reduced ≤ 120 LOC)
4. [ ] CLI UX unchanged (`erdos loop --help` options and behavior preserved)
5. [ ] All existing tests pass
6. [ ] `make ci` passes

---

## Non-Goals

- Changing CLI UX or argument names
- Modifying JSON output format
- Changing loop semantics (Lean checks, patch validation, status mapping)
