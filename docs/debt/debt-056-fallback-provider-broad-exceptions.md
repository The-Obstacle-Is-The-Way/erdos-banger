# DEBT-056: `FallbackProvider` Catches `Exception` Broadly (May Hide Provider Bugs)

**Status:** Open
**Priority:** P3
**Found:** 2026-01-22
**Found By:** SOLID / robustness audit

---

## Summary

`src/erdos/core/providers/fallback.py` intentionally provides resilience by trying multiple metadata providers. However, it currently catches `Exception` broadly in several places.

This can hide real provider bugs (programming errors) by treating them like transient provider failures and silently “falling back”.

---

## Evidence

- Reproduce: `rg -n \"except Exception\" src/erdos/core/providers/fallback.py`
- The port contract (`src/erdos/core/ports.py`) documents expected exception types:
  - `requests.RequestException` (network/API errors)
  - `ValueError` (invalid identifier / irrecoverable parse)

---

## Why This Matters

- **Fail fast:** unexpected exceptions should surface quickly during development/CI.
- **DIP + ISP:** callers rely on the port contract; catching everything defeats that contract.
- **Debuggability:** broad fallback can turn a deterministic bug into “weird behavior” that only shows up when the fallback chain changes.

---

## Recommended Fix

1. Restrict `except Exception` to the contractually expected exception types:
   - `requests.RequestException`
   - `ValueError`
2. Re-raise unknown exceptions (programmer errors) so CI fails loudly.
3. Optionally add a typed `MetadataProviderError` (raised by providers) if we want a single error type to catch.

---

## Acceptance Criteria

1. [ ] `FallbackProvider` catches only expected provider failure types.
2. [ ] Unknown exceptions propagate (unit test proves this).
3. [ ] Provider-not-found still returns `None` and proceeds to fallback correctly.
4. [ ] `make ci` passes.

---

## Non-Goals

- Changing the provider ordering strategy.
- Adding new providers.
