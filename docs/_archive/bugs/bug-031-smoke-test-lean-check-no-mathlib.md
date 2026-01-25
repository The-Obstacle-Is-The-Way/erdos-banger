# Bug: `make smoke` fails when Lean is installed but mathlib is not

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 83bf9f6

## Description

`make smoke` fails on systems where `lean` and `lake` are installed, because the smoke test initializes a Lean project without mathlib but then attempts to compile a generated skeleton that imports `Mathlib.*`.

## Steps to Reproduce

1. Ensure `lean` and `lake` are on `PATH`.
2. Run `make smoke`.

## Expected Behavior

Smoke test should pass offline; the optional Lean compilation check should not require mathlib when `--no-mathlib` is used.

## Actual Behavior

The smoke test fails during the optional Lean check step with an exit code of `5` (build failure).

## Root Cause

In `scripts/smoke-test.sh`, the smoke test initializes the Lean project with `erdos lean init --no-mathlib`, but unconditionally runs:

- `erdos lean check .../Erdos/Problem006.lean`

The generated `Problem006.lean` imports `Mathlib.*`, which is unavailable in a `--no-mathlib` project, causing `lake build` to fail.

## Fix

Implemented in commit `83bf9f6`:

- Always compile `Erdos/Basic.lean` (works without mathlib).
- Only compile `Erdos/Problem006.lean` when mathlib exists in the project (`.lake/packages/mathlib` or `lake-packages/mathlib`).

## Related

- `scripts/smoke-test.sh`
- `src/erdos/core/lean/runner.py` (`--no-mathlib` support)
