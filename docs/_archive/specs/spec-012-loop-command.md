# Spec 012: Loop Command

> Defines `erdos loop` for an iterative "propose → apply → check" cycle to assist Lean formalization.

**Status:** Complete
**Implemented In:** b1f4bdbb
**Prerequisites (SSOT):**
- Loop design decisions (SSOT): `docs/specs/spec-012-design.md`
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Ask command (prompt + optional LLM): `docs/_archive/specs/spec-011-ask-command.md`

Note: Completed prerequisites are archived under `docs/_archive/specs/`, while pending specs live under `docs/specs/`.

---

## 0) Why Deferred?

This command is intentionally deferred because it is high-risk and high-complexity:

1. It modifies files on disk (needs strong safety guardrails).
2. It can easily become a “reward hack” loop that passes compilation while stating nonsense.
3. It depends on stable building blocks:
   - deterministic Lean project init + check (Spec 007)
   - reliable retrieval/prompt tooling (Spec 011)
   - (optional) ingested fulltext improving retrieval (Spec 010)

---

## 1) CLI Interface

### Command signature

```text
erdos loop run PROBLEM_ID [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (int, required)

**Options**

- `--max-iter, -n INT`: maximum iterations (default: `10`)
- `--no-apply`: propose changes only; never write to disk
- `--timeout SECONDS`: Lean check timeout (default: `120`)
- `--allow-sorry-increase INT`: allow a patch to increase `sorry` count by up to N (default: `0`)
- `--max-patch-lines INT`: reject patches larger than this many lines (default: `50`)
- `--max-patch-bytes INT`: reject patches larger than this many bytes (default: `8192`)
- `--rag-limit INT`: maximum retrieved context chunks to include in the loop prompt (default: `5`)
- `--llm-cmd TEXT`: override LLM command (default: from `ERDOS_LLM_COMMAND`)
- `--from-iteration INT`: resume from a previous loop log (future; optional)

**Global flags**

- `--json` must be supported (Spec 004).

### Examples

```bash
# Propose-only (safe): no file writes
uv run erdos loop run 6 --no-apply

# Auto-apply (writes under formal/lean/Erdos/ unless --no-apply)
ERDOS_LLM_COMMAND="./scripts/llm.sh" uv run erdos loop run 6 --max-iter 3

# Machine output (propose-only)
uv run erdos --json loop run 6 --no-apply
```

---

## 2) Execution Model (SSOT)

At a high level:

1. Ensure `formal/lean/` exists and is initialized (reuse `erdos lean init` logic if needed).
2. Ensure the target file exists:
   - default: `formal/lean/Erdos/Problem{PROBLEM_ID:03d}.lean`
   - create via `erdos.core.formalizer.generate_skeleton(...)` if missing
3. Run Lean check via `LeanRunner.check(...)`.
4. If compilation succeeds and there are **no `sorry`** occurrences, exit success.
5. Otherwise:
   - build a prompt containing:
     - the current Lean file (or relevant excerpt)
     - Lean errors (from `LeanCheckResult.errors`)
     - the problem statement (`ProblemRecord`)
   - optional retrieved context (via `SearchIndex.search`)
   - run the external LLM command (subprocess) to propose an edit
   - apply the patch (unless `--no-apply`)
   - repeat until success or max iterations reached

**Invariant:** When not in `--no-apply` mode, the loop applies patches automatically.

---

## 3) Safety Guardrails (Non-negotiable)

1. **Patch-only edits**
   - The LLM must output **exactly one** SEARCH/REPLACE block (SSOT: `docs/specs/spec-012-design.md`).
   - If no fix is possible, the LLM may respond with exactly `NO_FIX_POSSIBLE` (SSOT: `docs/specs/spec-012-design.md`). The loop must treat this as a terminal “no progress possible” outcome (do not apply changes).
   - Reject free-form code dumps or multi-block outputs.
2. **Scoped edits**
   - Only allow modifications under `formal/lean/Erdos/`.
3. **Hard limits**
   - max iterations
   - max patch size (lines / bytes)
   - max file size included in prompt
4. **No network by default**
   - The CLI itself does not call external APIs directly.
   - LLM usage is via a user-configured command (Spec 011 pattern).

---

## 4) Output Schema (JSON)

All JSON output must be wrapped in `CLIOutput` (Spec 003).

**Success semantics (strict):**
- `CLIOutput.success=true` only when the final Lean file compiles and contains **zero** `sorry` and **zero** `admit`.
- All other terminal outcomes are `CLIOutput.success=false` with a structured `error` object that includes the required keys (`type`, `message`, `code`) plus extra summary keys (allowed by `CLIOutput` invariants).

On success, `data` must include:

```json
{
  "problem_id": 6,
  "status": "success",
  "iterations_completed": 3,
  "iterations_max": 10,
  "file": "formal/lean/Erdos/Problem006.lean",
  "no_apply": true,
  "llm": {
    "enabled": true,
    "command": "./scripts/llm.sh"
  },
  "run_log_path": "logs/loop/run_20260118_103045_a1b2c3.jsonl",
  "last_check": {
    "success": true,
    "error_count": 0,
    "has_sorry": false,
    "has_admit": false
  },
  "iterations": [
    {
      "iteration": 1,
      "patch_applied": false,
      "reason": "no_apply"
    },
    {
      "iteration": 2,
      "patch_applied": true,
      "sorry_before": 2,
      "sorry_after": 2,
      "admit_before": 0,
      "admit_after": 0,
      "check_success": false,
      "error_count": 1
    }
  ]
}
```

Notes:

- When `--no-apply` is set, `status` may be `no_progress` even if a patch was proposed.
- When the LLM returns `NO_FIX_POSSIBLE`, `status` must be `no_fix_possible` and the command must return `CLIOutput.err(...)` with `error.type="NoFixPossible"`.
- When `--json` is enabled, no progress/human text may be written to stdout.

### 4.1 Run Log File (`run_log_path`)

`run_log_path` points to a JSON Lines file (one JSON object per line) intended for debugging and reproducibility. Minimum required fields per line:

```json
{
  "schema_version": 1,
  "iteration": 2,
  "event": "llm_prompt",
  "timestamp": "2026-01-18T10:31:12.345Z",
  "data": {}
}
```

Required `event` values:
- `llm_prompt` (includes the exact prompt text sent)
- `llm_response` (includes the raw model output)
- `patch_applied` (includes file hash before/after)
- `lean_check` (includes `LeanCheckResult` summary)
- `user_decision` (`yes`/`no`/`skip`/`quit`, omitted when no user prompt is shown, e.g., `--no-apply`)

---

## 5) Implementation (Modules to Create in v1.2)

### 5.1 `src/erdos/core/loop.py`

Responsibilities:

- Orchestrate the loop and return `CLIOutput` summaries.
- Provide helpers:
  - `count_sorries(text: str) -> int`
  - Patch parsing/application for SEARCH/REPLACE blocks (SSOT: `docs/specs/spec-012-design.md`)

### 5.2 Additional modules (SSOT: `docs/specs/spec-012-design.md`)

- `src/erdos/core/loop_config.py` (`LoopConfig`)
- `src/erdos/core/patch_validator.py` (SEARCH/REPLACE parsing + validation)
- `src/erdos/core/loop_verifier.py` (sorry/admit counting + regression checks)
- `src/erdos/templates/loop_prompt.j2` (deterministic prompt template)

### 5.3 `src/erdos/commands/loop.py`

Follow Spec 004 patterns and call core loop logic.

---

## 6) Verification (Testable Even While Deferred)

When implemented, the following tests are required:

### Unit tests (no Lean required)

- `count_sorries` correctness on small Lean snippets.
- Patch validation rejects:
  - edits outside `formal/lean/Erdos/`
  - oversized patches
  - non-SEARCH/REPLACE outputs
- Patch validation accepts `NO_FIX_POSSIBLE` as a distinct terminal outcome (no patch applied).

### Integration tests (optional; marked `requires_lean`)

- Run `erdos loop <id> --no-apply` in a temp Lean project and assert it exits 0 and does not modify files.

---

## References

- subprocess execution (Python): `https://docs.python.org/3/library/subprocess.html`
- Lean runner + skeleton generation: `docs/_archive/specs/spec-007-lean-integration.md`

---

## Implementation Deviations (SSOT: Code)

Historical deviations existed during prior iterations; the spec has since been aligned with the implementation and the code is the source of truth (SSOT):

### 1. CLI Shape: `erdos loop run` subcommand

**Spec:** `erdos loop PROBLEM_ID [OPTIONS]`
**Implementation:** `erdos loop run PROBLEM_ID [OPTIONS]`

**Rationale:** Modern CLI style with `run` subcommand enables future subcommands (e.g., `erdos loop status`, `erdos loop resume`).

### 2. `--yes/-y` flag removed (auto-apply by default)

**Spec:** `--yes, -y` for non-interactive mode with explicit confirmation
**Implementation:** Patches apply automatically when not in `--no-apply` mode; `--yes` flag removed

**Rationale:** Simpler UX for automation pipelines. Use `--no-apply` for explicit human review. The original `--yes` flag was redundant with the absence of `--no-apply`.

### 3. JSON success semantics enforced

**Spec:** `CLIOutput.success=true` only on proof completion
**Implementation:** Aligned. Non-success statuses (`max_iterations`, `llm_required`, `no_fix_possible`, etc.) now return `CLIOutput.success=false` with loop data embedded in the error object.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.3.0 | 2026-01-22 | Document implementation deviations; align JSON success semantics with spec |
| 0.2.0 | 2026-01-18 | Rewrite: align with v1 `src/erdos/core` structure and Spec 011 external LLM approach |
