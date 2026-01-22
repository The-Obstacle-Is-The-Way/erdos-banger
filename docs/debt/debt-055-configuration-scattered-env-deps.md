# DEBT-055: Configuration Is Scattered via `os.environ` Reads (Hidden Dependencies, Harder Testing)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Architecture / DIP audit

---

## Summary

Multiple core modules read configuration directly from `os.environ` (paths, API keys, mailto defaults, command strings). This creates **hidden inputs** and makes code harder to reason about and test deterministically.

In Clean Architecture terms: environment is an outer-layer concern. The deeper the `os.environ` reads are, the more the dependency arrows point the wrong way.

---

## Evidence

Reproduce env reads:

```bash
rg -n \"os\\.environ|getenv\\(\" src/erdos/core
```

Examples (as of 2026-01-22):
- `src/erdos/core/problem_loader.py` reads `ERDOS_DATA_PATH`
- `src/erdos/core/search_index.py` reads `ERDOS_INDEX_PATH`
- `src/erdos/core/openalex_client.py` reads `OPENALEX_API_KEY` / `ERDOS_MAILTO`
- `src/erdos/core/ask/service.py` reads `ERDOS_LLM_COMMAND`
- `src/erdos/core/aristotle.py` reads `ARISTOTLE_API_KEY`
- `src/erdos/core/run_logger.py` reads `ERDOS_RUN_LOG_PATH`

---

## Why This Matters

- **DIP:** core code should depend on passed-in configuration, not the global process environment.
- **Testability:** unit tests have to mutate process-wide env vars, risking cross-test pollution and order dependence.
- **Local reasoning:** “what does this function do?” becomes “what does the environment contain?”.

---

## Recommended Fix (AppConfig + Composition Root Ownership)

1. Create a single configuration object (dataclass or Pydantic model):

```text
src/erdos/core/config.py
```

2. Move `os.environ` reads into **one place**:
- `AppConfig.from_env()` (and possibly `.from_file()` later)

3. Pass config into constructors / services via `AppContext`:
- `src/erdos/core/context.py` becomes the only place wiring config → concrete deps.

4. Keep backwards compatibility:
- Existing `*.from_env()` helpers may remain temporarily, but should delegate to `AppConfig`.

---

## Acceptance Criteria

1. [ ] `os.environ` reads in deep core modules are reduced to near-zero (allow list: config module + composition root).
2. [ ] Commands build an `AppContext` from config and pass explicit values (no hidden defaults).
3. [ ] Tests can instantiate services without mutating global env.
4. [ ] `make ci` passes.

---

## Non-Goals

- Adding a full YAML config system (spec separately if desired).
- Changing CLI flags or environment variable names immediately.
