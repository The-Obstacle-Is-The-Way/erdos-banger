# DEBT-046: CLIOutput `success=false` With Exit Code 0 Is a Contract Smell (Search `IndexEmpty`)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** CLI contract audit / reward-hack prevention review
**Fixed In:** 0046cdf

---

## Summary

The CLI contract currently allows a "failure-shaped" JSON payload (`CLIOutput.success=false`) while still exiting with **code 0** in one case:

- `erdos search` returns `CLIOutput.err(..., code=0)` for `IndexEmpty`.

This creates ambiguous semantics for automation:
- Shell sees success (exit 0)
- JSON consumer sees failure (`success=false`)

This is a subtle "reward-hack" path: callers can accidentally treat failures as successes or vice versa.

---

## Evidence

- `src/erdos/commands/search.py` (`search_problems_fts`):
  - `IndexEmpty` returns `CLIOutput.err(... code=0)` with comment "Not really an error…"
  - Reproduce: `rg -n "IndexEmpty" src/erdos/commands/search.py`

---

## Why This Matters

For CLIs, **exit code is the primary success signal**. If we want "not an error", we should emit a success-shaped payload (`CLIOutput.ok`) and exit 0.

Keeping contradictory signals increases downstream brittleness and makes CI scripting harder.

---

## Fix Applied (Option A)

Changed `search_problems_fts` to return `None` when index is empty (instead of `CLIOutput.err`).
Callers (`_search_with_fallback` and `mcp_search_index`) now:
1. Detect `None` return from FTS
2. Fall back to basic search immediately
3. Return `CLIOutput.ok` with:
   - `data.use_fts=false`
   - `data.mode="basic"`
   - `data.fallback_reason="index_empty"`

This makes the contract unambiguous:
- Exit 0 + `success=true` + `fallback_reason` explains what happened
- No more `CLIOutput.err(..., code=0)` anywhere in the codebase

---

## Acceptance Criteria

1. [x] There are no `CLIOutput.err(... code=0)` call sites.
2. [x] Search "index empty" behavior is unambiguous in both exit code and JSON schema.
3. [x] Tests cover the chosen behavior in both human and `--json` modes.
4. [x] `make ci` passes.
