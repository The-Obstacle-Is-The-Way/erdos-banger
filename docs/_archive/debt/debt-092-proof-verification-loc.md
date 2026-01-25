# DEBT-092: Proof Verification Module LOC Violations

**Priority:** P3 (Minor; clean up when touching nearby code)
**Status:** Fixed
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Fixed In:** 534802f

## Description

At time found, the proof verification implementation (SPEC-035/5) exceeded LOC thresholds:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/sync/proofs.py` | 626 | 500 | +126 |
| `src/erdos/commands/sync/proof_cmd.py` | 439 | 400 | +39 |

## Analysis

### proofs.py (626 LOC)

This module is well-organized with clear section boundaries:

| Section | LOC | Purpose |
|---------|-----|---------|
| Module docstring + imports | ~40 | Security warning, dependencies |
| Configuration constants | ~27 | Timeouts, log limits, env vars |
| Result types | ~29 | `VerificationResult`, `CloneResult` |
| Environment sanitization | ~19 | `_sanitize_env()` |
| Git operations | ~76 | `clone_repository()` |
| Lean verification | ~155 | `run_lake_build()`, `check_no_sorries()` |
| Main verification | ~150 | `verify_proof()`, `_verify_problem_files()` |
| Provenance management | ~121 | `create_provenance()`, `save_*()` |

**Cohesion:** All functions support a single capability (proof verification). The module has clear bounded contexts separated by `# ======` markers.

**Security:** This is security-critical code (runs untrusted `lake build`). Density is justified by the need for explicit guardrails and clear audit trail.

### proof_cmd.py (439 LOC)

This module contains application logic that arguably belongs in `core/`:

| Section | LOC | Location Issue |
|---------|-----|----------------|
| Imports + setup | ~38 | Fine |
| Security warning | ~23 | CLI-specific (fine) |
| `_run_verification()` | ~115 | **Application service — should be in core/** |
| `sync_proof_links()` | ~90 | **Application service — should be in core/** |
| `_print_human()` | ~90 | CLI-specific (fine) |
| `proof()` Typer callback | ~55 | Thin (correct pattern) |

The DEBT-065 pattern (thick CLI callbacks) was previously fixed for other commands but proof_cmd.py was added after that fix. The orchestration logic (~205 LOC) should live in `core/sync/proof_service.py`.

## Justification for Exemption

### proofs.py

The module is genuinely cohesive. Splitting options would:

1. **Extract provenance to `core/sync/provenance.py`** (~70 LOC of functions, ~50 LOC of imports/types)
   - Result: proofs.py → ~555 LOC (still +55 over threshold)
   - Creates coupling: verification creates provenance records

2. **Extract git operations to `core/sync/git.py`** (~76 LOC)
   - Result: proofs.py → ~549 LOC (still +49 over)
   - Single-use: only verification clones repos

Neither extraction provides meaningful architectural benefit.

### proof_cmd.py

The exemption is weaker here. Extracting application logic would:

1. Move `sync_proof_links()` + `_run_verification()` to `core/sync/proof_service.py` (~205 LOC)
2. Result: proof_cmd.py → ~236 LOC (well under threshold)
3. Follows established pattern (thin commands, testable core)

However, the current structure works and the violation is marginal (+39 LOC).

## Resolution

Fixed in `534802f` by:
- Extracting orchestration to `src/erdos/core/sync/proof_service.py`
- Splitting provenance + dataclasses to:
  - `src/erdos/core/sync/proofs_provenance.py`
  - `src/erdos/core/sync/proofs_types.py`
- Keeping `src/erdos/core/sync/proofs.py` under the 500 LOC threshold (currently 482 LOC)
- Keeping `src/erdos/commands/sync/proof_cmd.py` as a thin CLI adapter (currently 170 LOC)

## Refactoring Recommendations

If this debt is opened:

1. **For proof_cmd.py (recommended):**
   - Create `core/sync/proof_service.py` with `sync_proof_links()` and verification orchestration
   - Keep CLI adapter thin (parse flags → call service → format output)

2. **For proofs.py (optional):**
   - Extract `save_provenance()` and `save_verification_log()` to `core/sync/provenance.py`
   - Only worthwhile if provenance is needed elsewhere

## Acceptance Criteria (If Opened)

1. [x] `proof_cmd.py` reduced to ≤400 LOC via service extraction
2. [x] `proofs.py` reduced to ≤500 LOC
3. [x] Application logic (`sync_proof_links()`) lives in `core/sync/`, not `commands/`
4. [x] `make ci` passes
5. [x] Verification behavior unchanged
