# Adversarial Review: 2026-01-25 (Post-refactor CLI stress test)

**Scope:** Re-verify BUG-023..BUG-028 after refactors; validate no tracebacks on invalid CLI inputs
**Status:** Complete

## Context

This pass re-ran a focused CLI stress test after the DEBT-092/DEBT-096 refactors:

- Proof sync orchestration extracted to core (`refactor(sync): extract proof sync service`, `534802f`)
- `erdos search` split into thin adapter + impl/output modules (`refactor(commands): split search implementation`, `4a21f0b`)
- DEBT-092 and DEBT-096 archived (`docs(debt): archive DEBT-092 and DEBT-096`, `41c3e8d`)

Separately, BUG-023..BUG-028 were previously fixed in `92039ca`.

## Verification (BUG-023..BUG-028)

All six bugs remain fixed end-to-end:

- BUG-024 (`erdos search --limit 0/-1`): fails fast with Click/Typer validation (no Python traceback)
- BUG-025 (`erdos ask --limit 0/-1`): fails fast with Click/Typer validation (no silent empty-success)
- BUG-026 (`erdos refs s2 * --limit 0/-1`): fails fast with Click/Typer validation (no upstream API error)
- BUG-027 (`--log-level INVALID`): fails fast with Click enum validation (case-insensitive)
- BUG-028 (`--all --limit 0/-1` in batch commands): fails fast with Click/Typer validation (no negative slicing surprises)
- BUG-023 (`erdos lean import` relative path duplication): covered by existing integration tests (no duplicated `formal/lean/formal/lean/...`)

## Regression Tests Added

Expanded CLI validation tests to cover additional edge cases:

- `refs s2 cited-by --limit 0`
- `refs s2 references --limit 0`
- `ingest --all --limit 0`
- `lean formalize --all --limit 0`
- Assert `Traceback` never appears for usage errors

## CI / Smoke

- `make ci` ✅
- `make smoke` ✅

## New Bugs Found

None in this pass.
