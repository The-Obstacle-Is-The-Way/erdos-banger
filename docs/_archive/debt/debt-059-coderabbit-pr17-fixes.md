# DEBT-059: CodeRabbit PR#17 Fixes (Input Validation + Invariant Bugs)

**Status:** Fixed
**Priority:** P2 (Medium - correctness issues)
**Created:** 2026-01-22
**Source:** CodeRabbit automated review on PR#17
**Fixed In:** 61ad15e

---

## Summary

PR#17 (v2.1 Architecture Sprint) introduced several minor issues flagged by CodeRabbit. This debt item consolidates the **valid** findings that need fixes.

---

## Issues to Fix

### 1. CLIOutput Invariant Violation (batch_formalize.py:221-224)

**File:** `src/erdos/commands/lean/batch_formalize.py`

**Problem:** Creates `CLIOutput.ok()` then mutates `success=False`, violating CLIOutput invariants.

```python
# Current (BAD)
if result.failed_count > 0:
    output = CLIOutput.ok(command="erdos lean formalize", data=data)
    output.success = False  # Mutation violates invariants
    return output
```

**Fix:** Return a proper partial-failure output:

```python
if result.failed_count > 0:
    return CLIOutput(
        command="erdos lean formalize",
        success=False,
        data=None,  # CLIOutput invariant: data must be None on failure
        error={
            "type": "PartialFailure",
            "message": f"{result.failed_count} problems failed",
            "code": ExitCode.ERROR,
            # Optional: include batch metadata in error extras
            "failed_ids": result.failed_ids,
        },
    )
```

### 2. max_concurrent=0 Crashes ThreadPoolExecutor (formalize_cmd.py)

**File:** `src/erdos/commands/lean/formalize_cmd.py`

**Problem:** `ThreadPoolExecutor(max_workers=0)` raises `ValueError`. No input validation.

**Fix:** Add validation before ThreadPoolExecutor:

```python
if max_concurrent < 1:
    return CLIOutput.err(
        command="erdos lean formalize",
        error_type="UsageError",
        message="--max-concurrent must be >= 1",
        code=ExitCode.USAGE_ERROR,
    )
```

### 3. --device Accepts Invalid Values (convert.py:235)

**File:** `src/erdos/commands/convert.py`

**Problem:** `--device` help says "cpu/cuda/mps" but accepts any string.

**Fix:** Validate against allowed set:

```python
if device:
    allowed = {"cpu", "cuda", "mps"}
    if device.lower() not in allowed:
        return CLIOutput.err(...)
    device = device.lower()
```

### 4. status_cmd Summary Ignores --local Flag (status_cmd.py:176)

**File:** `src/erdos/commands/lean/status_cmd.py`

**Problem:** `_get_all_problems_status` doesn't receive `check_local` flag, always scans local files.

**Fix:** Thread `check_upstream` and `check_local` through to `_get_all_problems_status`.

### 5. TORCH_DEVICE Env Var Leak (pdf_converter.py:326)

**File:** `src/erdos/core/pdf_converter.py`

**Problem:** Sets `os.environ["TORCH_DEVICE"]` but never restores original value.

**Fix:** Use context manager pattern to restore original value after conversion.

### 6. KeyError Risk in lean/common.py (lines 37, 44)

**File:** `src/erdos/commands/lean/common.py`

**Problem:** Direct `result_data["file"]` access can raise KeyError.

**Fix:** Use `.get()` with fallback:

```python
output_file = result_data.get("file", "unknown")
```

### 7. Empty Exception Messages (prove_cmd.py:86)

**File:** `src/erdos/commands/lean/prove_cmd.py`

**Problem:** `str(e)` can be empty, failing CLIOutput validation.

**Fix:** Add fallback message:

```python
message = str(e) or "Unexpected error"
```

### 8. `--no-network` Is Silently Ignored Without `--import-upstream` (formalize_cmd.py)

**File:** `src/erdos/commands/lean/formalize_cmd.py`

**Problem:** The `--no-network` option is documented as “requires --import-upstream”, but passing it without `--import-upstream` is silently ignored (no validation, no error).

**Fix:** Add early validation:

```python
if no_network and not import_upstream:
    return CLIOutput.err(
        command="erdos lean formalize",
        error_type="UsageError",
        message="--no-network may only be used with --import-upstream",
        code=ExitCode.USAGE_ERROR,
    )
```

### 9. Lean Init Should Use Lean Exit Code for Lean Failures (init_cmd.py)

**File:** `src/erdos/commands/lean/init_cmd.py`

**Problem:** `LeanRunnerError` currently maps to `ExitCode.ERROR`. Lean toolchain failures should return `ExitCode.LEAN_ERROR` for consistency with other Lean commands.

**Fix:** Change the `LeanRunnerError` handler to return `code=ExitCode.LEAN_ERROR`.

---

## False Positives / Non-Blockers (Skip)

- **batch_formalize.py:95** - CodeRabbit claimed `.lean` vs `.Lean` case mismatch. **FALSE** - both use lowercase `.lean`.
- **common.py:145** - Duck-typing routing is "fragile" - valid observation but works fine, not urgent.
- `src/erdos/core/providers/__init__.py:27` - Import order vs comment mismatch - trivial, not worth a commit.

---

## Acceptance Criteria

- [x] All 9 fixes above implemented
- [x] Tests added for validation cases (max_concurrent, device, no_network)
- [x] Lean init exit codes validated in tests
- [x] `make ci` passes
- [x] No new regressions

---

## Estimated Scope

- Files: ~8
- Lines: ~80-140
- Risk: Low (input validation + defensive coding)
