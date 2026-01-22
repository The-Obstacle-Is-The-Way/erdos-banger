# DEBT-064: `loop/runner.py` Violates Dependency Inversion (LLM Coupling)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

`src/erdos/core/loop/runner.py` directly imports and uses `execute_llm` function from `core/ask/llm.py`. This violates Dependency Inversion Principle (DIP) because:

- High-level loop orchestration depends on low-level LLM execution details
- Unit tests must patch a module-global symbol (`erdos.core.loop.runner.execute_llm`), coupling tests to import paths
- Cannot swap LLM execution mechanism (subprocess vs API) without editing imports

---

## Evidence

```python
# src/erdos/core/loop/runner.py:12
from erdos.core.ask.llm import execute_llm

# Used in _run_single_iteration() (currently around line ~248)
response, exit_code = execute_llm(llm_command, prompt)
```

**DIP violation**: `runner.py` (high-level policy) depends directly on `llm.py` (low-level mechanism).

**Testing impact (current SSOT):**

- Tests patch `@patch("erdos.core.loop.runner.execute_llm")` to avoid subprocess calls.
- This is workable, but it’s brittle: changing import structure breaks tests even if behavior is unchanged.

---

## Recommended Fix

Inject LLM execution as a dependency (callable), so `runner.py` depends on an abstraction.

1. Define a callable protocol (or type alias) in `src/erdos/core/ports.py`:

```python
class LLMExecute(Protocol):
    """Callable for executing an LLM command."""
    def __call__(self, llm_command: str, prompt: str) -> tuple[str, int]: ...
```

1. Update the loop runner entrypoints to accept an injected executor with a default:

```python
def run_loop(..., llm_execute: LLMExecute = execute_llm) -> LoopResult:
    ...

def _run_single_iteration(..., llm_execute: LLMExecute) -> tuple[...]:
    ...
```

1. Update tests to pass a fake executor instead of patching module globals:
   - Replace `@patch("erdos.core.loop.runner.execute_llm")` with `llm_execute=fake_llm`
   - Keep the fake deterministic (no filesystem/network), return `(response_text, exit_code)`

---

## Acceptance Criteria

1. [ ] `LLMExecute` protocol exists (in `src/erdos/core/ports.py` or `src/erdos/core/loop/runner.py`)
2. [ ] `run_loop()` and `_run_single_iteration()` accept an injected `llm_execute` dependency
3. [ ] Tests no longer patch `erdos.core.loop.runner.execute_llm` (they pass `llm_execute=` instead)
4. [ ] All existing tests pass
5. [ ] `make ci` passes

---

## Non-Goals

- Changing LLM execution logic
- Adding new LLM backends (that would be a feature)
- Modifying CLI
