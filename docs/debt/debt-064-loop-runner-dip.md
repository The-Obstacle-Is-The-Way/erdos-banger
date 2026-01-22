# DEBT-064: `loop/runner.py` Violates Dependency Inversion (LLM Coupling)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

`src/erdos/core/loop/runner.py` directly imports and uses `execute_llm` function from `core/ask/llm.py`. This violates Dependency Inversion Principle (DIP) because:

- High-level loop orchestration depends on low-level LLM execution details
- Cannot test loop logic without subprocess/network calls
- Cannot swap LLM implementations without modifying imports

---

## Evidence

```python
# src/erdos/core/loop/runner.py line 12
from erdos.core.ask.llm import execute_llm

# Used in _run_single_iteration() around line 237
response, exit_code = execute_llm(prompt, config.llm_command)
```

**DIP violation**: `runner.py` (high-level policy) depends directly on `llm.py` (low-level mechanism).

**Testing impact**: Tests must either:
- Mock `execute_llm` at import time (fragile)
- Run actual LLM subprocess (slow, requires API key)
- Skip testing LLM integration paths (incomplete coverage)

---

## Recommended Fix

1. Define `LLMExecutor` protocol in `core/ports.py`:

```python
class LLMExecutor(Protocol):
    """Protocol for executing LLM commands."""
    def execute(self, prompt: str, command: str) -> tuple[str, int]:
        """Execute LLM and return (response, exit_code)."""
        ...
```

2. Update `LoopRunner` to accept executor as dependency:

```python
class LoopRunner:
    def __init__(
        self,
        config: LoopConfig,
        lean_runner: LeanRunner,
        llm_executor: LLMExecutor,  # Injected dependency
        logger: LoopLogger | None = None,
    ):
        self._llm_executor = llm_executor
```

3. Create concrete implementation in `core/ask/llm.py`:

```python
class SubprocessLLMExecutor:
    """LLM executor using subprocess."""
    def execute(self, prompt: str, command: str) -> tuple[str, int]:
        return execute_llm(prompt, command)
```

4. Wire in composition root (`core/context.py`):

```python
def build_loop_runner(config: LoopConfig) -> LoopRunner:
    return LoopRunner(
        config=config,
        lean_runner=LeanRunner(config.project_path),
        llm_executor=SubprocessLLMExecutor(),
    )
```

---

## Acceptance Criteria

1. [ ] `LLMExecutor` protocol defined in `core/ports.py`
2. [ ] `LoopRunner` accepts `llm_executor` parameter
3. [ ] `SubprocessLLMExecutor` concrete implementation created
4. [ ] Wiring updated in composition root
5. [ ] Tests can inject mock `LLMExecutor` for fast, isolated testing
6. [ ] All existing tests pass
7. [ ] `make ci` passes

---

## Non-Goals

- Changing LLM execution logic
- Adding new LLM backends (that would be a feature)
- Modifying CLI interface
