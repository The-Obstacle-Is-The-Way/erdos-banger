"""Loop runner - main iteration orchestration.

Per spec-012-loop-command.md execution model.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from erdos.core.ask.llm import execute_llm as default_execute_llm
from erdos.core.loop.iteration import _IterationRunner
from erdos.core.loop.logging import LoopLogger, generate_run_id
from erdos.core.loop.result import IterationRecord, LoopResult, LoopStatus
from erdos.core.loop.verifier import count_admits, count_sorries
from erdos.core.repo_root import resolve_repo_root


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.lean import LeanRunner
    from erdos.core.loop.config import LoopConfig
    from erdos.core.models import LeanCheckResult, ProblemRecord
    from erdos.core.ports import LLMExecute


logger = logging.getLogger(__name__)


def _check_initial_completion(
    file_path: Path,
    lean_runner: LeanRunner,
    config: LoopConfig,
) -> tuple[bool, LeanCheckResult | None]:
    """Check if the file is already complete (no sorry/admit, compiles).

    Returns:
        (is_complete, last_check) tuple.
    """
    file_content = file_path.read_text(encoding="utf-8")
    if count_sorries(file_content) == 0 and count_admits(file_content) == 0:
        check_result = lean_runner.check(file_path, timeout=config.lean_timeout_seconds)
        if check_result.success:
            return True, check_result
    return False, None


def _create_result(
    *,
    problem_id: int,
    status: LoopStatus,
    iterations_completed: int,
    config: LoopConfig,
    file_path: Path,
    no_apply: bool,
    llm_command: str | None,
    log_path: Path,
    last_check: LeanCheckResult | None,
    iterations: list[IterationRecord],
) -> LoopResult:
    """Create a LoopResult with common fields."""
    return LoopResult(
        problem_id=problem_id,
        status=status,
        iterations_completed=iterations_completed,
        iterations_max=config.max_iterations,
        file=file_path,
        no_apply=no_apply,
        llm_enabled=llm_command is not None,
        llm_command=llm_command,
        run_log_path=log_path,
        last_check=last_check,
        iterations=iterations,
    )


def run_loop(
    *,
    problem: ProblemRecord,
    file_path: Path,
    config: LoopConfig,
    lean_runner: LeanRunner,
    llm_command: str | None,
    no_apply: bool = False,
    rag_chunks: list[Any] | None = None,
    llm_execute: LLMExecute | None = None,
    log_dir: Path | None = None,
) -> LoopResult:
    """Run the iterative proof loop per spec-012-loop-command.md execution model."""
    if rag_chunks is None:
        rag_chunks = []
    if llm_execute is None:
        llm_execute = default_execute_llm

    # Set up logging - use repo root to ensure absolute path (GH-036)
    effective_log_dir = (
        log_dir if log_dir is not None else resolve_repo_root(None) / "logs" / "loop"
    )
    log_path = effective_log_dir / f"{generate_run_id()}.jsonl"
    with LoopLogger(log_path) as loop_logger:
        iterations: list[IterationRecord] = []
        last_check: LeanCheckResult | None = None

        # Helper to create results with common fields
        def make_result(
            status: LoopStatus,
            completed: int,
            check: LeanCheckResult | None,
            iters: list[IterationRecord],
        ) -> LoopResult:
            return _create_result(
                problem_id=problem.id,
                status=status,
                iterations_completed=completed,
                config=config,
                file_path=file_path,
                no_apply=no_apply,
                llm_command=llm_command,
                log_path=log_path,
                last_check=check,
                iterations=iters,
            )

        # Check if already complete
        is_complete, last_check = _check_initial_completion(
            file_path, lean_runner, config
        )
        if is_complete:
            return make_result(LoopStatus.SUCCESS, 0, last_check, [])

        # LLM required but not configured
        if llm_command is None:
            return make_result(LoopStatus.LLM_REQUIRED, 0, None, [])

        # Main loop
        stall_count = 0
        iteration_runner = _IterationRunner(
            file_path=file_path,
            problem=problem,
            config=config,
            lean_runner=lean_runner,
            llm_command=llm_command,
            no_apply=no_apply,
            rag_chunks=rag_chunks,
            loop_logger=loop_logger,
            iterations=iterations,
            llm_execute=llm_execute,
        )
        for i in range(1, config.max_iterations + 1):
            terminal_status, last_check, stall_count, work_done = iteration_runner.run(
                iteration=i, stall_count=stall_count
            )
            if terminal_status is not None:
                completed = i if work_done else i - 1
                return make_result(terminal_status, completed, last_check, iterations)

        # Max iterations reached
        return make_result(
            LoopStatus.MAX_ITERATIONS, config.max_iterations, last_check, iterations
        )
