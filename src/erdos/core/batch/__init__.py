"""Batch operations package (SPEC-015).

Provides batch processing with filtering, state tracking, and resume support.

Public API:
    - BatchFilters: Filter criteria for selecting problems
    - BatchState: State of a batch operation
    - BatchProgress: Progress update for batch operations
    - BatchResult: Result of a batch operation
    - BatchRunner: Orchestrator for batch operations
    - filter_problem_ids: Filter problems by criteria
    - generate_batch_id: Generate unique batch ID
    - save_batch_state / load_batch_state: State persistence
    - save_latest_batch_id / load_latest_batch_id: Latest pointer persistence
    - SCHEMA_VERSION: Current schema version for state files
"""

from erdos.core.batch.models import (
    SCHEMA_VERSION,
    BatchFilters,
    BatchProgress,
    BatchResult,
    BatchState,
    filter_problem_ids,
)
from erdos.core.batch.persistence import (
    generate_batch_id,
    load_batch_state,
    load_latest_batch_id,
    save_batch_state,
    save_latest_batch_id,
)
from erdos.core.batch.runner import BatchRunner


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
