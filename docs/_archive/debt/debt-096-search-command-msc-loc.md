# DEBT-096: Search Command Module LOC Violation (Post-MSC Growth)

**Priority:** P3 (Minor; clean up when touching nearby code)
**Status:** Fixed
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Fixed In:** 4a21f0b

## Description

At time found, the search command module exceeded LOC thresholds after MSC search mode was added (SPEC-031/3):

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/commands/search.py` | 525 | 400 | +125 |

| Function | LOC | Threshold | Delta |
|----------|-----|-----------|-------|
| `search()` (line 330) | 196 | 120 | +76 |

## History

DEBT-043 previously reduced this module from 791→334 LOC by extracting orchestration logic to `core/search/service.py`. The module has since grown 191 LOC (57% increase) due to MSC search mode (SPEC-031/3):

| Component | Added LOC |
|-----------|-----------|
| `_print_msc_human()` | ~35 |
| `_execute_msc_search()` | ~55 |
| MSC validation in `_validate_mode_flags()` | ~20 |
| MSC parameters in `search()` | ~20 |
| MSC-specific logic in callback | ~20 |
| **Total MSC addition** | ~150 |

## Analysis

### Function Size (196 LOC)

The `search()` callback appears long but the breakdown reveals:
- **~80 LOC:** Typer parameter declarations (framework-required boilerplate)
- **~20 LOC:** Docstring with usage examples
- **~88 LOC:** Actual orchestration logic

The actual logic is well-delegated to helper functions (`_validate_mode_flags()`, `_execute_msc_search()`, `_handle_index_build()`, `_handle_embeddings_build()`) and the service layer (`execute_search()`).

### Module Size (525 LOC)

Breakdown by responsibility:
- **Imports/setup:** ~46 LOC
- **MSC output formatter:** ~35 LOC (`_print_msc_human()`)
- **General output formatter:** ~56 LOC (`_print_human()`)
- **Flag validation:** ~48 LOC (`_validate_mode_flags()`)
- **MSC execution:** ~55 LOC (`_execute_msc_search()`)
- **Index/embeddings handlers:** ~64 LOC (`_handle_index_build()`, `_handle_embeddings_build()`)
- **Mode selection:** ~8 LOC (`_get_search_mode()`)
- **Typer callback:** ~196 LOC (`search()`)

## Justification for Exemption

The exemption is appropriate because:

1. **Typer boilerplate inflation:** ~80 LOC of the function is parameter declarations required by Typer's annotation-based syntax. This is unavoidable framework overhead.

2. **Well-delegated logic:** The actual business logic (~88 LOC) is compact and well-organized. All orchestration is delegated to:
   - Helper functions for CLI-specific concerns
   - `core/search/service.py` for search orchestration

3. **Refactoring ROI is low:** Extracting MSC mode to a submodule would:
   - Save ~90 LOC in main module (still leaves 419 LOC, over threshold)
   - Create coupling issues (main callback still dispatches to MSC mode)
   - Reduce discoverability (`erdos search --help` shows all modes together)

4. **No SRP violation:** Each helper function has single responsibility. The module cohesively handles "search command CLI concerns."

## Refactoring Options (Deferred)

If the module grows further, consider:

1. **Typer sub-app structure:**

   ```text
   commands/search/
   ├── __init__.py     # Typer app composition
   ├── local.py        # BM25/semantic/hybrid modes
   └── msc.py          # MSC search mode
   ```

2. **Extract output formatters:** Move `_print_human()` and `_print_msc_human()` to `commands/search_output.py`

Currently the cognitive overhead of splitting doesn't justify the LOC savings.

## Resolution

Fixed in `4a21f0b` by:
- Splitting orchestration to `src/erdos/commands/search_impl.py`
- Splitting human rendering to `src/erdos/commands/search_output.py`
- Keeping `src/erdos/commands/search.py` as a thin Typer adapter (currently 102 LOC)
- Removing the audit exemption for `commands/search.py:search`

## Acceptance Criteria (If Opened)

If this debt is opened for work:

1. [x] Module reduced to ≤400 LOC
2. [x] `search()` function reduced to ≤120 LOC
3. [x] All search modes remain accessible via `erdos search --help`
4. [x] `make ci` passes
5. [x] No functional regression in search behavior
