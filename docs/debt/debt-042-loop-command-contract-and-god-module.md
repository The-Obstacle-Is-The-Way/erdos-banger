# DEBT-042: Loop Command Contract Drift + `core/loop.py` God Function (SRP Pressure)

**Status:** Open
**Priority:** P1
**Found:** 2026-01-22
**Found By:** Architecture / SOLID audit (post v2.1 sprint)

---

## Summary

The loop feature is implemented and well-tested at the core level, but it currently has **two high-risk maintainability issues**:

1. **Contract drift / ambiguity** between archived spec text and the actual CLI + JSON semantics.
2. `src/erdos/core/loop.py` contains a **god function** (`run_loop`, **399** LOC) that mixes orchestration, IO, logging, and domain rules.

This combination increases the risk of “fixes that regress safety” as the loop evolves (SPEC-012 follow-ups, Aristotle integration, richer prompting, resumption, etc.).

---

## Evidence (First Principles)

### A) `run_loop` is a god function

- File size: `src/erdos/core/loop.py` is **683** LOC.
- Function size: `run_loop` is **399** LOC (`src/erdos/core/loop.py:285-683`) and has ruff complexity suppressions:
  - `# noqa: PLR0911, PLR0912, PLR0915`

This violates the repo’s stated Clean Code expectation (“avoid god files / mixed responsibilities”).

Reproduce:
- `wc -l src/erdos/core/loop.py`
- `python3 - <<'PY'\nimport ast, pathlib\np=pathlib.Path('src/erdos/core/loop.py');t=p.read_text();m=ast.parse(t)\nfor n in ast.walk(m):\n  if isinstance(n, ast.FunctionDef) and n.name=='run_loop':\n    print('run_loop LOC:', n.end_lineno-n.lineno+1, 'at', f'{p}:{n.lineno}')\nPY`

### B) Spec/contract drift for the loop command

Archived spec text and implementation diverge on key user-facing contracts:

- CLI shape:
  - Spec-012 text: `erdos loop PROBLEM_ID …`
  - Implementation/tests: `erdos loop run PROBLEM_ID …` (`tests/integration/test_cli_loop.py`)
- Safety model:
  - Spec-012 text: apply requires confirmation unless `--yes`
  - Implementation: patches are applied automatically when not in `--no-apply` mode (see `tests/unit/test_loop.py::test_applies_patch_and_checks`)
- JSON success semantics:
  - Spec-012 text: `CLIOutput.success=true` only on proof completion; all other terminal statuses are `success=false`
  - Implementation: loop statuses are returned as `CLIOutput.ok(...)` (success true) in some terminal cases (e.g., `llm_required`)

Whether the code or the archived spec is SSOT is currently ambiguous to contributors.

Reproduce:
- Spec CLI synopsis: `rg -n \"^erdos loop\" docs/_archive/specs/spec-012-loop-command.md`
- Implementation has `run` subcommand: `rg -n \"def run\\(\" src/erdos/commands/loop.py`
- Spec includes `--yes`, implementation does not: `rg -n -- \"--yes\" docs/_archive/specs/spec-012-loop-command.md && ! rg -n -- \"--yes\" src/erdos/commands/loop.py`
- Implementation returns `CLIOutput.ok(...)` for non-success statuses: `rg -n \"return CLIOutput\\.ok\" src/erdos/commands/loop.py`

---

## Why This Matters (Uncle Bob / DeepMind Standard)

- **SRP:** One function currently owns too many decisions (Lean check, LLM invocation, patch validation, file writes, stall logic, logging, termination conditions).
- **OCP:** Adding “one more rule” (e.g., `--allow-sorry-increase`, patch budgeting, tool routing) is likely to require editing `run_loop` directly, increasing regression risk.
- **Testability:** Unit tests cover some paths, but the coupling inside `run_loop` makes it hard to add targeted tests for new loop behaviors without brittle fixtures/mocking.

---

## Recommended Fix (Pick One Strategy, Then Lock the SSOT)

### Option A (Docs-first): Treat code as SSOT and update archived Spec-012

Fastest way to remove contributor confusion:
- Update `docs/_archive/specs/spec-012-loop-command.md` to match actual CLI shape, safety model, and JSON semantics.
- Add a “Drift note” section documenting intentional deviations.

**Pros:** lowest risk to behavior; unblocks contributors.
**Cons:** does not address the god function.

### Option B (Spec-first): Align implementation to Spec-012 contracts

- Implement `--yes/-y` and confirmation semantics (or refuse writes unless explicit).
- Align JSON success semantics to the spec (or formally revise the spec to match desired semantics).

**Pros:** strongest safety + CI/automation semantics.
**Cons:** behavior changes + more work.

### Option C (Balanced, recommended): Lock contracts + begin structural extraction

1. Decide on loop CLI/output contracts (SSOT: spec text).
2. Extract `core/loop.py` into a bounded-context package:
   - `src/erdos/core/loop/runner.py` (iteration orchestration)
   - `src/erdos/core/loop/logging.py` (LoopLogger)
   - `src/erdos/core/loop/prompt.py` (build_loop_prompt + budgeting)
   - `src/erdos/core/loop/result.py` (LoopResult + IterationRecord)
   - Keep `src/erdos/core/loop.py` as a compatibility shim re-exporting public symbols.

**Pros:** reduces change amplification; enables future loop features.
**Cons:** moderate refactor (but can be done incrementally with re-exports).

---

## Acceptance Criteria

1. [ ] A single SSOT exists for loop contracts:
   - Either archived Spec-012 updated to match code, or code updated to match Spec-012.
2. [ ] `run_loop` is reduced to ≤ ~120 LOC or replaced by a small coordinator calling well-named helpers/classes.
3. [ ] Public imports remain stable (re-export shim allowed):
   - `from erdos.core.loop import run_loop, LoopStatus, LoopResult` continues to work.
4. [ ] Tests cover loop contract semantics explicitly:
   - At minimum: CLI JSON contract for `llm_required`, `no_apply` behavior, and one “success” case.
5. [ ] `make ci` passes (ruff, mypy, pytest, coverage).

---

## Non-Goals

- Rewriting LeanRunner internals.
- Implementing new loop features (resume/from-iteration, tool-use JSON, etc.) beyond what’s needed to lock contracts and remove SRP pressure.
