# Adversarial Review: 2026-01-25 (Follow-up)

**Scope:** Post-fix CLI stress test (validation + edge cases)
**Status:** Complete

## Summary

Follow-up stress testing after fixing BUG-023..028 (commit `92039ca`) found additional input-validation gaps, primarily in zbMATH and ingest.

## Resolution

BUG-029..030 were fixed in commit `6c7eef2` and their bug decks archived under `docs/_archive/bugs/`.

## Bugs Found

| ID | Priority | Title |
|----|----------|-------|
| BUG-029 | P2 | zbMATH commands accept invalid pagination/year ranges |
| BUG-030 | P2 | `erdos ingest` accepts invalid numeric values (tracebacks / surprising batch selection) |

## Notes

- Both issues follow the same pattern as the 2026-01-25 initial audit: missing CLI-side validation leading to either:
  - cryptic upstream API errors (zbMATH), or
  - uncaught `ValueError` from core dataclass validation (ingest).

## Recommendations

1. Standardize numeric validation for all CLI flags that feed into core `__post_init__` validators.
2. Add a small set of CLI validation regression tests (similar to `tests/integration/test_cli_validation.py`) for each new bug.
