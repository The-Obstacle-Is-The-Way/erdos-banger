"""Batch operations for ingest and formalize commands (SPEC-015).

Backward-compatible shim that re-exports from the batch/ subpackage.
All public symbols remain available from `erdos.core.batch`.

See `erdos.core.batch/` for the actual implementation:
    - models.py: Data models (BatchFilters, BatchState, BatchProgress, BatchResult)
    - persistence.py: State file save/load functions
    - runner.py: BatchRunner orchestration class
"""

# Re-export all public symbols from subpackage
from erdos.core.batch import (
    SCHEMA_VERSION,
    BatchFilters,
    BatchProgress,
    BatchResult,
    BatchRunner,
    BatchState,
    filter_problem_ids,
    generate_batch_id,
    load_batch_state,
    load_latest_batch_id,
    save_batch_state,
    save_latest_batch_id,
)


__all__ = [
    "SCHEMA_VERSION",
    "BatchFilters",
    "BatchProgress",
    "BatchResult",
    "BatchRunner",
    "BatchState",
    "filter_problem_ids",
    "generate_batch_id",
    "load_batch_state",
    "load_latest_batch_id",
    "save_batch_state",
    "save_latest_batch_id",
]
