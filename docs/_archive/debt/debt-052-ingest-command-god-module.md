# DEBT-052: `erdos ingest` Command Module Is a God File (CLI + Batch + Printing + Policy)

**Status:** Fixed
**Fixed In:** 8c53292
**Priority:** P2
**Found:** 2026-01-22
**Found By:** SRP / vertical-slice audit (post v2.1)

---

## Summary

`src/erdos/commands/ingest.py` has grown into a large module that mixes:

- CLI parsing/wiring (Typer)
- Human output formatting (Rich tables)
- Batch orchestration and progress reporting
- Ingest policy (delay/mailto/source selection)
- Cross-cutting behavior (PDF conversion flags, rate limiting)

The code works, but this is a classic Clean Code failure mode: a feature keeps accreting options, and the command file becomes the de facto “application layer”.

This is not just a “line length” issue — it makes it hard to add ingest-related features safely (OpenAlex/Crossref orchestration, retries, batch resume semantics, rate limiting) without unintentional coupling.

---

## Evidence (First Principles)

- File size: `wc -l src/erdos/commands/ingest.py` → **550** lines
- Long Typer callback:

```bash
python3 - <<'PY'
import ast
import pathlib

p = pathlib.Path("src/erdos/commands/ingest.py")
t = p.read_text()
m = ast.parse(t)
for n in ast.walk(m):
    if isinstance(n, ast.FunctionDef) and n.name == "ingest":
        print("ingest LOC:", n.end_lineno - n.lineno + 1, "at", f"{p}:{n.lineno}")
PY
```

---

## Why This Matters (Uncle Bob / DeepMind Standards)

- **SRP:** CLI parsing, printing, batch orchestration, and ingest policy are distinct reasons to change.
- **OCP:** adding one new ingest mode (e.g., `--provider-chain`, `--retry-policy`) pushes edits into the same file and often the same function.
- **Testability:** meaningful unit tests should target pure orchestration/policy code, not Typer callbacks.

---

## Recommended Fix (Incremental, No UX Change)

### 1) Extract a core ingest “application service”

Create a single testable entrypoint that:
- accepts a typed options object (e.g., `IngestOptions`)
- performs validation and orchestration (single vs batch)
- returns `CLIOutput` data payloads

Example target module:

```text
src/erdos/core/ingest/app.py
```

### 2) Keep command module thin

`src/erdos/commands/ingest.py` should:
- parse flags → options
- call `core.ingest.app.ingest(...)`
- render output via `presenter.exit_with_result(...)`

### 3) Split printing and Typer help text if needed

If the module is still >~300 LOC after extraction, split into:

```text
src/erdos/commands/ingest/
├── __init__.py
├── cmd.py
└── printers.py
```

---

## Acceptance Criteria

1. [x] `src/erdos/commands/ingest.py` reduced to ≤ ~300 LOC (or split into package).
   - **Actual:** 302 LOC (thin adapter)
2. [x] Ingest orchestration exists in a pure core module (no Typer/Rich imports).
   - **Actual:** `src/erdos/core/ingest/app.py` (340 LOC) - pure orchestration
3. [x] Unit tests cover ingest orchestration for:
   - single-problem ingest: `TestRunSingleIngestion`
   - batch ingest filters + resume validation: `TestIsBatchMode`, `TestRunBatchIngestion`
   - `--no-network` / `--no-download` policy combinations: `TestNoNetworkNowDownloadPolicyCombinations`
   - **Actual:** `tests/unit/test_ingest_app.py` (440 LOC)
4. [x] `make ci` passes (891 tests, 82.81% coverage).

---

## Non-Goals

- Changing ingest CLI UX or output schema.
- Adding new metadata providers (handled by SPEC-022 follow-ups).
