# DEBT-057: No Automated Guardrails Against “God Files” Regressing (Commands/Core)

**Status:** Fixed
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Clean Code audit (post v2.1 refactors)
**Fixed In:** 1f37f5c

---

## Summary

We’ve made major progress reducing SRP/DIP/DRY violations, but the codebase currently has **no automated guardrail** preventing future regressions into:

- giant command modules (`src/erdos/commands/*.py`)
- giant orchestration functions (`run_loop`, `search`, `ingest`, …)
- “god interfaces” (ports that accrete unrelated methods)

Humans and agents will keep adding features. Without a backpressure mechanism, the highest-risk architectural debt will slowly return.

---

## Evidence

Current size hotspots (examples; see debt decks for details):
- `wc -l src/erdos/commands/search.py` → 791
- `wc -l src/erdos/core/loop.py` → 683
- `python3 - <<'PY'\nimport ast, pathlib\np=pathlib.Path('src/erdos/core/loop.py');t=p.read_text();m=ast.parse(t)\nfor n in ast.walk(m):\n  if isinstance(n, ast.FunctionDef) and n.name=='run_loop':\n    print('run_loop LOC:', n.end_lineno-n.lineno+1)\nPY`

---

## Why This Matters

- **SRP/OCP:** large modules/functions become the default “where changes go”, increasing change amplification.
- **Reward hacking risk:** it’s easy for an agent to “implement a feature” by adding more branches to an already-complex function.
- **Reviewability:** PRs become harder to audit (exactly the opposite of our “plumbing first” goal).

---

## Recommended Fix (Lightweight, CI-Enforced)

Add a small audit script + CI step that fails when thresholds are exceeded **unless** a documented justification exists.

Example:

- `scripts/audit_code_health.py`
  - enforce max file LOC for `src/erdos/commands/*` and `src/erdos/core/*`
  - enforce max function LOC (e.g., 120)
  - allow exceptions via an inline docstring marker (similar to DEBT-026 pattern)

Run in CI:

```bash
uv run python scripts/audit_code_health.py
```

---

## Acceptance Criteria

1. [x] CI fails if new code introduces a module/function above agreed thresholds without explicit justification.
2. [x] The audit script reports the worst offenders with file:line locations.
3. [x] Thresholds are documented in `AGENTS.md` (or `CLAUDE.md`) for contributors.
4. [x] `make ci` passes.

---

## Non-Goals

- Enforcing dogmatic line limits everywhere.
- Reformatting existing code solely to satisfy the guardrail.
