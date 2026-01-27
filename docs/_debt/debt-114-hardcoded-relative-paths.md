# DEBT-114: Hardcoded Relative Paths Across Codebase

**Priority:** P2
**Status:** Open
**Found:** 2026-01-27
**Related:** GH-036 (partial fix in PR#40)

## Summary

The codebase has 13+ hardcoded relative paths like `Path("logs/loop")` scattered across modules. GH-036/PR#40 only fixed ONE instance. This is a systemic issue that needs consistent resolution.

## Audit Results

### Category 1: FIXED (uses `resolve_repo_root()`)

| Module | Path | Status |
|--------|------|--------|
| `core/loop/runner.py` | `logs/loop` | FIXED (PR#40) |
| `core/ask/logging.py` | `logs/ask` | CORRECT - uses `resolve_repo_root()` |
| `core/ask/service.py` | `logs/ask` | CORRECT - uses `get_repo_root()` |
| `core/loop/service.py` | `logs/loop` | CORRECT - uses `get_repo_root()` |

### Category 2: PARTIALLY SAFE (default used only when env/AppConfig override is None)

These have hardcoded defaults BUT are resolved through `XxxConfig.from_env()` which can override:

| Module | Constant | Default Path | Override Mechanism |
|--------|----------|--------------|-------------------|
| `core/clients/exa.py` | `DEFAULT_CACHE_PATH` | `literature/cache/exa` | `ERDOS_EXA_CACHE_PATH` env var |
| `core/clients/semantic_scholar.py` | `DEFAULT_CACHE_PATH` | `literature/cache/s2` | `ERDOS_S2_CACHE_PATH` env var |
| `core/clients/zbmath.py` | `DEFAULT_CACHE_PATH` | `literature/cache/zbmath` | `ERDOS_ZBMATH_CACHE_PATH` env var |
| `core/clients/cache.py` | inline default | `literature/cache/api` | constructor param |
| `core/config.py` | `DEFAULT_RUN_LOG_PATH` | `logs/runs.jsonl` | `ERDOS_RUN_LOG_PATH` env var |
| `core/config.py` | `DEFAULT_INDEX_PATH` | `index/erdos.sqlite` | `ERDOS_INDEX_PATH` env var |

**Risk:** These work when running from repo root but BREAK if running from subdirectory without env vars set.

### Category 3: BROKEN (no resolution to absolute path)

| Module | Line | Path | Issue |
|--------|------|------|-------|
| `core/problem_loader.py` | 193 | `data/problems_enriched.yaml` | `.exists()` check uses relative path |
| `core/problem_loader.py` | 207 | `data/erdosproblems/data/problems.yaml` | Same issue |
| `commands/lean/common.py` | 13 | `data/erdosproblems/data/problems.yaml` | Module-level constant |
| `core/sync/proofs_provenance.py` | 17 | `data/sync_cache/proofs` | No resolution |
| `core/sync/website.py` | 370 | `data/latex` | Inline usage |
| `core/sync/forum.py` | 317 | `data/sync_cache/proofs` | Inline usage |
| `core/sync/proof_service.py` | 36 | `data/sync_cache/proofs` | Module-level constant |
| `core/sync/submodule.py` | 30 | `data/erdosproblems` | Module-level constant |

## Pattern Analysis

### Good Pattern (ask/logging.py)

```python
def _get_default_log_dir() -> Path:
    """Get default ask log directory (logs/ask/)."""
    return resolve_repo_root(None) / "logs" / "ask"
```

### Bad Pattern (problem_loader.py)

```python
enriched_path = Path("data/problems_enriched.yaml")
if enriched_path.exists():  # BROKEN: relative to cwd, not repo root
    return cls(enriched_path)
```

### Correct Fix Pattern

```python
from erdos.core.repo_root import resolve_repo_root

def _get_default_data_path() -> Path:
    return resolve_repo_root(None) / "data" / "problems_enriched.yaml"
```

## Impact

- **Breaks when:** Running CLI from subdirectory (e.g., `cd formal/lean && uv run erdos list`)
- **Breaks when:** Running tests from different working directory
- **Breaks when:** Embedding CLI in larger applications

## Recommended Fix

1. **Add helper to `repo_root.py`:**

   ```python
   def repo_path(*parts: str) -> Path:
       """Get absolute path relative to repo root."""
       return resolve_repo_root(None).joinpath(*parts)
   ```

2. **Replace all hardcoded paths with `repo_path()` calls**

3. **Update tests to verify paths are absolute**

## Acceptance Criteria

- [ ] All `Path("data/...")`, `Path("logs/...")`, `Path("literature/...")`, `Path("index/...")` replaced
- [ ] New helper `repo_path()` added to `repo_root.py`
- [ ] Tests added to verify paths work from subdirectories
- [ ] No relative paths remain in module-level constants

## Files to Modify

1. `src/erdos/core/repo_root.py` - Add `repo_path()` helper
2. `src/erdos/core/problem_loader.py` - Lines 193, 207
3. `src/erdos/commands/lean/common.py` - Line 13
4. `src/erdos/core/sync/proofs_provenance.py` - Line 17
5. `src/erdos/core/sync/website.py` - Line 370
6. `src/erdos/core/sync/forum.py` - Line 317
7. `src/erdos/core/sync/proof_service.py` - Line 36
8. `src/erdos/core/sync/submodule.py` - Line 30
9. `src/erdos/core/clients/exa.py` - Line 32
10. `src/erdos/core/clients/semantic_scholar.py` - Line 30
11. `src/erdos/core/clients/zbmath.py` - Line 40
12. `src/erdos/core/clients/cache.py` - Line 34
13. `src/erdos/core/config.py` - Lines 33, 34

## Estimated Scope

- ~13 files to update
- ~20 path references to fix
- Medium complexity (mechanical changes)
- Risk: Low (paths are well-tested; just need to make them absolute)
