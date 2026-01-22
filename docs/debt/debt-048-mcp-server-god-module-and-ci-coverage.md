# DEBT-048: `mcp/server.py` Is Large and Partially Outside CI (Optional Dependency)

**Status:** Open
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Maintainability / testability audit

---

## Summary

`src/erdos/mcp/server.py` is a large module (~564 LOC) and its tests are skipped when the optional `mcp` dependency is not installed. This creates two problems:

1. **SRP pressure:** the file is trending toward a “god module” for tool definitions + transport wiring.
2. **CI gap:** key behaviors may not run in default CI (depending on whether `mcp` extras are installed).

---

## Evidence

- `wc -l src/erdos/mcp/server.py` → **564** LOC
- Test suite shows skips:
  - `tests/integration/test_mcp_server.py` skipped when `mcp not installed`
  - `tests/unit/test_mcp_tools.py` skipped when `mcp not installed`

---

## Recommended Fix

### A) Refactor structure (SRP)

Split into a package:

```text
src/erdos/mcp/
├── server.py          # thin entrypoint
├── tools.py           # tool definitions
├── handlers.py        # command adapters
└── schemas.py         # request/response payloads
```

### B) Close the CI gap (testability)

Ensure CI installs the `mcp` extra (or runs a dedicated optional-deps job) so MCP tests run at least once per PR.

---

## Acceptance Criteria

1. [ ] MCP implementation split into smaller modules (≤ ~250 LOC each) OR justified as cohesive.
2. [ ] CI runs MCP tests in at least one job (no unconditional skip in PR CI).
3. [ ] `make ci` passes.
