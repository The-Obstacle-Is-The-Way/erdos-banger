# DEBT-043: `erdos search` Command Module Is Still a God File (SRP Pressure)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Architecture / SOLID audit
**Fixed In:** 4f99202

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

```bash
python3 - <<'PY'
import ast
import pathlib

p = pathlib.Path("src/erdos/commands/search.py")
t = p.read_text()
m = ast.parse(t)
for n in ast.walk(m):
    if isinstance(n, ast.FunctionDef) and n.name == "search":
        print("search LOC:", n.end_lineno - n.lineno + 1, "at", f"{p}:{n.lineno}")
PY
```

---

## Why This Matters

- **Change amplification:** tweaks to one mode can accidentally affect others.
- **Testing friction:** unit tests are forced to patch CLI-layer code instead of pure "search service" functions.
- **Architecture drift:** the repo pattern is "thin commands, testable core/services" (see `core/ask/`, `core/ingest/`), but search remains CLI-heavy.

---

## Recommended Fix (Incremental)

1. Create a core service layer for search orchestration:

```text
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

```text
src/erdos/commands/search/
├── __init__.py
├── cmd.py
└── printers.py
```

---

## Acceptance Criteria

1. [x] `src/erdos/commands/search.py` reduced to ≤ ~300 LOC (or split into a package).
   - **Result:** Reduced from 791 LOC to 334 LOC (58% reduction)
2. [x] Search orchestration lives in `src/erdos/core/search/service.py` (pure logic, no Typer/Rich).
   - **Result:** Created `core/search/service.py` (636 LOC) with all orchestration logic
3. [x] Public CLI behavior unchanged (help text, flags, output schema).
   - **Result:** All CLI tests pass, behavior unchanged
4. [x] Tests target the core service for most logic; CLI tests remain thin.
   - **Result:** `test_search_command_helpers.py` tests service layer directly
5. [x] `make ci` passes.
   - **Result:** 869 tests pass, 82.40% coverage

---

## Resolution

The search command module was refactored to follow the "thin commands, testable core/services" pattern:

**Before:**
- `commands/search.py`: 791 LOC (god module)
- `search()` callback: 204 LOC

**After:**
- `commands/search.py`: 334 LOC (thin CLI adapter)
- `core/search/service.py`: 636 LOC (orchestration logic)
- `core/search/types.py`: 63 LOC (contract types)
- `core/search/__init__.py`: 45 LOC (re-exports)
- `search()` callback: 137 LOC

The service layer contains:
- `SearchMode` enum and `SearchOptions` dataclass
- `search_fts()`, `search_basic()`, `search_with_fallback()` - FTS search functions
- `search_semantic()`, `search_hybrid()` - vector search functions
- `build_search_index()`, `build_embeddings()` - index building
- `execute_search()` - main entry point that routes by mode

The command module now only handles:
- CLI flag parsing via Typer
- Rich output formatting (`_print_human()`)
- Mode validation (`_validate_mode_flags()`)
- Routing to service layer and `exit_with_result()`

---

## Non-Goals

- Changing ranking algorithms or default modes.
- Reworking SQLite schema (handled by search_index specs/decks).
