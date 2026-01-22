"""Batch operation runner (orchestration logic).

Contains BatchRunner class for executing batch operations with state tracking.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from erdos.core.batch.models import (
    BatchFilters,
    BatchProgress,
    BatchResult,
    BatchState,
)
from erdos.core.batch.persistence import (
    generate_batch_id,
    load_batch_state,
    load_latest_batch_id,
    save_batch_state,
    save_latest_batch_id,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.rate_limiter import RateLimiter


if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class BatchRunner:
    """Runs batch operations with state tracking and resume support."""

    def __init__(
        self,
        command: str,
        problem_ids: list[int],
        process_fn: Callable[[int], bool],
        *,
        state_dir: Path | None = None,
        filters: BatchFilters | None = None,
        delay: float = 3.0,
        on_progress: Callable[[BatchProgress], None] | None = None,
        dry_run: bool = False,
        resume: bool = False,
    ) -> None:
        """Initialize batch runner.

        Args:
            command: Command name (e.g., "erdos ingest")
            problem_ids: List of problem IDs to process
            process_fn: Function that processes a single problem ID,
                returns True on success, False on failure
            state_dir: Directory for state files (default: logs/)
            filters: Filters used to select problems (for resume validation)
            delay: Seconds between processing each problem
            on_progress: Callback for progress updates
            dry_run: If True, don't actually process
            resume: If True, resume from prior state
        """
        self.command = command
        self.problem_ids = problem_ids
        self.process_fn = process_fn
        self.state_dir = state_dir or Path("logs")
        self.filters = filters or BatchFilters()
        self.delay = delay
        self.on_progress = on_progress
        self.dry_run = dry_run
        self.resume = resume
        self._interrupted = False

    @property
    def batches_dir(self) -> Path:
        """Return the batches subdirectory."""
        return self.state_dir / "batches"

    def run(self) -> BatchResult:
        """Execute the batch operation.

        Returns:
            BatchResult with outcome details
        """
        start_time = datetime.now(tz=UTC)

        # Handle resume
        if self.resume:
            resume_result = self._handle_resume()
            if resume_result is not None:
                return resume_result

        # Create new batch state
        batch_id = generate_batch_id()
        state = BatchState(
            batch_id=batch_id,
            command=self.command,
            filters=self.filters,
            problem_ids=self.problem_ids,
        )

        # Run the batch
        return self._execute_batch(state, start_time)

    def _handle_resume(self) -> BatchResult | None:
        """Handle resume logic. Returns error result if resume fails, else None."""
        # Try to load batch_id from latest.json
        batch_id_result = self._load_latest_batch_id_for_resume()
        if isinstance(batch_id_result, BatchResult):
            return batch_id_result
        batch_id = batch_id_result

        # Try to load prior state
        state_result = self._load_prior_state_for_resume_checked(batch_id)
        if isinstance(state_result, BatchResult):
            return state_result
        prior_state = state_result

        # Validate command matches
        if prior_state.command != self.command:
            return self._error_result(
                f"Command mismatch: prior batch was '{prior_state.command}', "
                f"current is '{self.command}'.",
                ExitCode.USAGE_ERROR,
            )

        # Validate filters match
        if not prior_state.filters.matches(self.filters):
            return self._error_result(
                "Filter mismatch: current filters don't match prior batch.",
                ExitCode.USAGE_ERROR,
            )

        # Update problem_ids to use prior state and continue
        self.problem_ids = prior_state.problem_ids
        return None

    def _load_latest_batch_id_for_resume(self) -> str | BatchResult:
        """Load latest batch ID. Returns batch_id string or error BatchResult."""
        latest_path = self.batches_dir / "latest.json"

        if not latest_path.exists():
            return self._error_result(
                "No previous batch run found. Re-run without --resume.",
                ExitCode.NOT_FOUND,
            )

        try:
            return load_latest_batch_id(latest_path)
        except (json.JSONDecodeError, KeyError) as e:
            return self._error_result(
                f"Corrupted latest.json: {e}. Delete it or re-run without --resume.",
                ExitCode.CONFIG_ERROR,
            )

    def _load_prior_state_for_resume_checked(
        self, batch_id: str
    ) -> BatchState | BatchResult:
        """Load prior batch state. Returns BatchState or error BatchResult."""
        state_path = self.batches_dir / f"{batch_id}.json"

        if not state_path.exists():
            return self._error_result(
                f"Batch state file not found: {state_path}. "
                f"Delete latest.json or re-run without --resume.",
                ExitCode.NOT_FOUND,
            )

        try:
            return load_batch_state(state_path)
        except json.JSONDecodeError as e:
            return self._error_result(
                f"Corrupted batch state file {state_path}: {e}",
                ExitCode.CONFIG_ERROR,
            )
        except ValueError as e:
            return self._error_result(str(e), ExitCode.CONFIG_ERROR)

    def _execute_batch(self, state: BatchState, start_time: datetime) -> BatchResult:
        """Execute the batch processing loop."""
        # Handle dry run
        if self.dry_run:
            duration_ms = int(
                (datetime.now(tz=UTC) - start_time).total_seconds() * 1000
            )
            return BatchResult(
                batch_id=state.batch_id,
                total=len(self.problem_ids),
                completed_count=0,
                failed_count=0,
                failed_ids=[],
                duration_ms=duration_ms,
                dry_run=True,
            )

        # Load prior state if resuming
        if self.resume:
            prior_state = self._load_prior_state_for_resume()
            if prior_state is not None:
                state = prior_state

        # Ensure batches dir exists
        self.batches_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiter for API calls
        limiter = RateLimiter(delay_seconds=self.delay)

        # Process each problem
        total = len(state.problem_ids)
        to_process = state.failed + state.pending  # Retry failed, then pending

        for i, problem_id in enumerate(to_process):
            if self._interrupted:
                break

            # Rate limit
            limiter.sleep_if_needed()

            # Process
            try:
                success = self.process_fn(problem_id)
                if success:
                    state.mark_completed(problem_id)
                    message = "OK"
                else:
                    state.mark_failed(problem_id)
                    message = "Failed"
            except Exception as e:
                logger.exception("Error processing problem %d", problem_id)
                state.mark_failed(problem_id)
                success = False
                message = str(e)

            # Progress callback
            if self.on_progress:
                self.on_progress(
                    BatchProgress(
                        problem_id=problem_id,
                        index=i,
                        total=total,
                        success=success,
                        message=message,
                    )
                )

            # Save state after each problem
            state_path = self.batches_dir / f"{state.batch_id}.json"
            save_batch_state(state_path, state)
            save_latest_batch_id(self.batches_dir / "latest.json", state.batch_id)

        # Calculate result
        duration_ms = int((datetime.now(tz=UTC) - start_time).total_seconds() * 1000)
        return BatchResult(
            batch_id=state.batch_id,
            total=total,
            completed_count=len(state.completed),
            failed_count=len(state.failed),
            failed_ids=state.failed.copy(),
            duration_ms=duration_ms,
        )

    def _load_prior_state_for_resume(self) -> BatchState | None:
        """Load prior state for resume. Returns None if not found."""
        try:
            latest_path = self.batches_dir / "latest.json"
            batch_id = load_latest_batch_id(latest_path)
            state_path = self.batches_dir / f"{batch_id}.json"
            return load_batch_state(state_path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return None

    def _error_result(self, message: str, exit_code: ExitCode) -> BatchResult:
        """Create an error BatchResult."""
        return BatchResult(
            batch_id="",
            total=len(self.problem_ids),
            completed_count=0,
            failed_count=0,
            failed_ids=[],
            duration_ms=0,
            exit_code=exit_code,
            error_message=message,
        )

    def interrupt(self) -> None:
        """Signal the runner to stop after the current problem."""
        self._interrupted = True
