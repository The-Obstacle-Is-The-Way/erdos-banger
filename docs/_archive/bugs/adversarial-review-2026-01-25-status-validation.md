# Adversarial Review: 2026-01-25 (Status Validation)

**Scope:** Follow-up CLI stress test on constrained string flags (batch filters)
**Status:** Complete

## Summary

Found **1 bug** where invalid `--status` values were accepted in batch commands and
misclassified as `NotFoundError` instead of a usage error. Fixed in `e49d9c1` with
regression tests.

## Bug Found

| ID | Title | Priority | Fix |
|----|-------|----------|-----|
| BUG-032 | Batch `--status` accepts invalid values (misclassified as NotFound) | P3 | `e49d9c1` |

## Commands Tested

- `uv run erdos --json ingest --all --status foo --dry-run` (now exits `2`)
- `uv run erdos --json lean formalize --all --status foo --dry-run` (now exits `2`)

## CI / Smoke

- `make ci` ✅
- `make smoke` ✅

