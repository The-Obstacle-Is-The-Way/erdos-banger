# DEBT-065: CLI Command Callbacks Too Thick (SRP Violation)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

Several CLI command callbacks in `src/erdos/commands/` exceed the recommended 50 LOC threshold and contain business logic that should be in the service layer. This violates Single Responsibility Principle - CLI callbacks should only handle:

1. Typer argument parsing
2. Calling service layer
3. Formatting output

---

## Evidence

| Command | File | Callback | LOC | Issue |
|---------|------|----------|-----|-------|
| search | `commands/search.py` | `search()` | 139 | Contains query validation, mode selection, result formatting |
| ingest | `commands/ingest.py` | `ingest()` | 153 | Contains manifest loading, reference processing orchestration |
| loop | `commands/loop.py` | `execute_loop()` | 154 | Contains project setup, LLM command handling, loop orchestration |

**Comparison with well-structured commands:**

| Command | File | Callback | LOC | Pattern |
|---------|------|----------|-----|---------|
| show | `commands/show.py` | `show()` | 35 | ✓ Thin - calls service, formats output |
| list | `commands/list_cmd.py` | `list_problems()` | 42 | ✓ Thin - calls service, formats output |
| formalize | `commands/lean/formalize_cmd.py` | `formalize()` | 106 | ✓ Fixed in DEBT-060 |

---

## Recommended Fix

For each thick callback, extract orchestration to service layer:

### 1. `commands/search.py::search()` → `core/search/service.py`

```python
# commands/search.py - thin callback
def search(ctx: typer.Context, query: str, ...):
    with measure_time_ms() as duration:
        result = execute_search(SearchOptions(...))  # Already exists
    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
```

Move query validation and mode selection into `execute_search()`.

### 2. `commands/ingest.py::ingest()` → `core/ingest/service.py`

```python
# commands/ingest.py - thin callback
def ingest(ctx: typer.Context, problem_id: int, ...):
    with measure_time_ms() as duration:
        result = ingest_problem_references(problem_id, IngestOptions(...))
    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
```

Orchestration already in `ingest_problem_references()` - just clean up callback.

### 3. `commands/loop.py::execute_loop()` → `core/loop/service.py`

Create `execute_proof_loop()` service function:

```python
# core/loop/service.py
def execute_proof_loop(
    problem_id: int,
    options: LoopOptions,
    *,
    problems_repo: ProblemRepository,
) -> CLIOutput:
    """Execute proof loop for a problem."""
    # Move all orchestration logic here
    ...
```

---

## Acceptance Criteria

1. [ ] `commands/search.py::search()` reduced to ≤ 50 LOC
2. [ ] `commands/ingest.py::ingest()` reduced to ≤ 50 LOC
3. [ ] `commands/loop.py::execute_loop()` reduced to ≤ 50 LOC
4. [ ] Business logic moved to appropriate service modules
5. [ ] CLI callbacks only handle: arg parsing → service call → output formatting
6. [ ] All existing tests pass
7. [ ] `make ci` passes

---

## Non-Goals

- Changing CLI UX or argument names
- Modifying JSON output format
- Changing service layer implementations
