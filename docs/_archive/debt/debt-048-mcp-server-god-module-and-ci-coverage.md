# DEBT-048: `mcp/server.py` Is Large and Partially Outside CI (Optional Dependency)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Maintainability / testability audit
**Fixed In:** c756f4e

---

## Summary

`src/erdos/mcp/server.py` is a large module (~574 LOC) and its tests were skipped when the optional `mcp` dependency was not installed. This created two problems:

1. **SRP pressure:** the file was trending toward a "god module" for tool definitions + transport wiring.
2. **CI gap:** key behaviors never ran in CI (the `mcp` extra was never installed).

---

## Evidence

- `wc -l src/erdos/mcp/server.py` → **574** LOC
- Test suite showed skips:
  - `tests/integration/test_mcp_server.py` skipped when `mcp not installed`
  - `tests/unit/test_mcp_tools.py` skipped when `mcp not installed`

---

## Resolution

### A) Module cohesion justified (no split required)

The module was analyzed and found to be **cohesive despite its size**:

- **Clear internal structure**: helpers (88 LOC) → core testable functions (277 LOC) → thin MCP wrappers (200 LOC)
- **Core functions accept explicit dependencies** (`repo`, `index`) for unit testability
- **MCP wrappers are thin** (wire dependencies + `json.dumps`)
- **Not covered by audit guardrails**: the `scripts/audit_code_health.py` only audits `commands/` and `core/`, not `mcp/`
- **Splitting would create fragmentation** without meaningful benefit at this size

Splitting was deemed premature optimization. The module can be revisited if it grows significantly.

### B) CI gap closed

Added a dedicated `test-mcp` CI job in `.github/workflows/ci.yml` that:
1. Installs dependencies with `--extra mcp`
2. Runs both unit and integration MCP tests
3. Runs on every push/PR

The `pytest.importorskip("mcp")` pattern correctly handles the optional dependency - tests run when mcp is installed, skip otherwise.

---

## Acceptance Criteria

1. [x] MCP implementation split into smaller modules (≤ ~250 LOC each) OR **justified as cohesive**.
2. [x] CI runs MCP tests in at least one job (no unconditional skip in PR CI).
3. [x] `make ci` passes.
