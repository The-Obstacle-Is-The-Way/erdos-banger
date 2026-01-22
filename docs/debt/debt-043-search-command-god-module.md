# DEBT-043: `erdos search` Command Module Is Still a God File (SRP Pressure)

**Status:** Open
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Architecture / SOLID audit

---

## Summary

`src/erdos/commands/search.py` has grown into a large module (**791** LOC) with a large Typer callback (`search`, **204** LOC). It mixes:

- CLI parsing/wiring (Typer)
- Human output formatting (Rich)
- Index building / embedding orchestration
- Multiple search modes (BM25/FTS/semantic/hybrid)
- Validation and error mapping

This violates SRP and makes future changes (SPEC-014 embeddings, batch workflows, metadata integration) higher risk than necessary.

---

## Evidence

- File size: `wc -l src/erdos/commands/search.py` → **791** lines
- Long CLI callback:
  - `src/erdos/commands/search.py:588-791 def search(...)` (**204** LOC)
  - ruff complexity suppressions: `# noqa: PLR0912, PLR0915`

Reproduce:
- `wc -l src/erdos/commands/search.py`
- `python3 - <<'PY'\nimport ast, pathlib\np=pathlib.Path('src/erdos/commands/search.py');t=p.read_text();m=ast.parse(t)\nfor n in ast.walk(m):\n  if isinstance(n, ast.FunctionDef) and n.name=='search':\n    print('search LOC:', n.end_lineno-n.lineno+1, 'at', f'{p}:{n.lineno}')\nPY`

---

## Why This Matters

- **Change amplification:** tweaks to one mode can accidentally affect others.
- **Testing friction:** unit tests are forced to patch CLI-layer code instead of pure “search service” functions.
- **Architecture drift:** the repo pattern is “thin commands, testable core/services” (see `core/ask/`, `core/ingest/`), but search remains CLI-heavy.

---

## Recommended Fix (Incremental)

1. Create a core service layer for search orchestration:

```
src/erdos/core/search/service.py
```

Responsibilities:
- Validate `SearchOptions`
- Ensure index/embeddings are built when requested
- Call `SearchIndexProtocol` methods (FTS/semantic/hybrid)
- Return `CLIOutput` data payloads (no Rich/Typer)

2. Keep `src/erdos/commands/search.py` as a thin adapter:
- Parse CLI flags → `SearchOptions`
- Call `core.search.service.search(...)`
- Route output via `exit_with_result(...)`

3. If file size still grows, split command module into a package:

```
src/erdos/commands/search/
├── __init__.py
├── cmd.py
└── printers.py
```

---

## Acceptance Criteria

1. [ ] `src/erdos/commands/search.py` reduced to ≤ ~300 LOC (or split into a package).
2. [ ] Search orchestration lives in `src/erdos/core/search/service.py` (pure logic, no Typer/Rich).
3. [ ] Public CLI behavior unchanged (help text, flags, output schema).
4. [ ] Tests target the core service for most logic; CLI tests remain thin.
5. [ ] `make ci` passes.

---

## Non-Goals

- Changing ranking algorithms or default modes.
- Reworking SQLite schema (handled by search_index specs/decks).
