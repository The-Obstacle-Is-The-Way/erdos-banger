"""Loop runner - main iteration orchestration.

Per spec-012-loop-command.md execution model.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from erdos.core.ask.llm import execute_llm
from erdos.core.loop.logging import LoopLogger, file_hash, generate_run_id
from erdos.core.loop.patch_validator import PatchStatus, validate_patch
from erdos.core.loop.prompt import build_loop_prompt
from erdos.core.loop.result import IterationRecord, LoopResult, LoopStatus
from erdos.core.loop.verifier import (
    LoopExitCondition,
    LoopVerification,
    count_admits,
    count_sorries,
)


if TYPE_CHECKING:
    from erdos.core.lean_runner import LeanRunner
    from erdos.core.loop.config import LoopConfig
    from erdos.core.models import LeanCheckResult, ProblemRecord


logger = logging.getLogger(__name__)


def apply_patch(file_path: Path, search_text: str, replace_text: str) -> str:
    """Apply a patch to a file.

    Args:
        file_path: Path to the file
        search_text: Text to find and replace
        replace_text: Replacement text

    Returns:
        New file content after patch
    """
    content = file_path.read_text(encoding="utf-8")
    new_content = content.replace(search_text, replace_text, 1)
    file_path.write_text(new_content, encoding="utf-8")
    return new_content


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


def _handle_llm_error(
    iteration: int,
    exit_code: int,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
) -> tuple[int, IterationRecord]:
    """Handle LLM execution error, return updated stall_count and record."""
    logger.warning("LLM exited with code %d", exit_code)
    record = IterationRecord(
        iteration=iteration,
        patch_applied=False,
        sorry_before=sorries_before,
        sorry_after=sorries_before,
        admit_before=admits_before,
        admit_after=admits_before,
        check_success=last_check.success,
        error_count=len(last_check.errors),
        reason="llm_error",
    )
    return stall_count + 1, record


def _handle_patch_rejected(
    iteration: int,
    rejection_reason: str,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
) -> tuple[int, IterationRecord]:
    """Handle rejected patch, return updated stall_count and record."""
    logger.warning("Patch rejected: %s", rejection_reason)
    record = IterationRecord(
        iteration=iteration,
        patch_applied=False,
        sorry_before=sorries_before,
        sorry_after=sorries_before,
        admit_before=admits_before,
        admit_after=admits_before,
        check_success=last_check.success,
        error_count=len(last_check.errors),
        reason=rejection_reason,
    )
    return stall_count + 1, record


def _apply_and_verify_patch(
    file_path: Path,
    search_text: str,
    replace_text: str,
    sorries_before: int,
    admits_before: int,
    size_before: int,
    config: LoopConfig,
    loop_logger: LoopLogger,
    iteration: int,
) -> tuple[str, LoopVerification]:
    """Apply patch and run verification.

    Returns:
        (new_content, verification) tuple.
    """
    hash_before = file_hash(file_path)
    new_content = apply_patch(file_path, search_text, replace_text)
    hash_after = file_hash(file_path)

    loop_logger.log_event(
        "patch_applied",
        iteration,
        {"hash_before": hash_before, "hash_after": hash_after},
    )

    sorries_after = count_sorries(new_content)
    admits_after = count_admits(new_content)
    size_after = len(new_content.encode("utf-8"))

    verification = LoopVerification(
        compiles=True,  # Will be checked next iteration
        sorry_count_before=sorries_before,
        sorry_count_after=sorries_after,
        admit_count_before=admits_before,
        admit_count_after=admits_after,
        file_size_before=size_before,
        file_size_after=size_after,
        min_file_size_ratio=config.min_file_size_ratio,
    )

    return new_content, verification


def _run_single_iteration(  # noqa: PLR0911
    iteration: int,
    file_path: Path,
    problem: ProblemRecord,
    config: LoopConfig,
    lean_runner: LeanRunner,
    llm_command: str,
    no_apply: bool,
    rag_chunks: list[Any],
    loop_logger: LoopLogger,
    iterations: list[IterationRecord],
    stall_count: int,
) -> tuple[LoopStatus | None, LeanCheckResult, int, bool]:
    """Run a single loop iteration.

    # exempt: DEBT-042

    Returns:
        (terminal_status, last_check, updated_stall_count, work_done) tuple.
        terminal_status is None if the loop should continue.
        work_done is True if any meaningful work was done in this iteration.
    """
    logger.info("Loop iteration %d/%d", iteration, config.max_iterations)

    # Read current state
    file_content = file_path.read_text(encoding="utf-8")
    sorries_before = count_sorries(file_content)
    admits_before = count_admits(file_content)
    size_before = len(file_content.encode("utf-8"))

    # Run Lean check
    last_check = lean_runner.check(file_path, timeout=config.lean_timeout_seconds)
    loop_logger.log_event(
        "lean_check",
        iteration,
        {
            "success": last_check.success,
            "error_count": len(last_check.errors),
            "file_hash": file_hash(file_path),
        },
    )

    # Check if already complete (no work done yet)
    if last_check.success and sorries_before == 0 and admits_before == 0:
        return LoopStatus.SUCCESS, last_check, stall_count, False  # work_done=False

    # Build prompt and call LLM
    prompt = build_loop_prompt(
        file_path=file_path,
        file_content=file_content,
        problem=problem,
        check_result=last_check,
        rag_chunks=rag_chunks,
        config=config,
    )
    loop_logger.log_event("llm_prompt", iteration, {"prompt": prompt})

    try:
        response, exit_code = execute_llm(llm_command, prompt)
    except Exception as e:
        logger.error("LLM execution failed: %s", e)
        return (
            LoopStatus.ERROR,
            last_check,
            stall_count,
            True,
        )  # work_done=True (LLM attempted)

    loop_logger.log_event(
        "llm_response", iteration, {"response": response, "exit_code": exit_code}
    )

    if exit_code != 0:
        new_stall, record = _handle_llm_error(
            iteration,
            exit_code,
            sorries_before,
            admits_before,
            last_check,
            stall_count,
        )
        iterations.append(record)
        if new_stall >= config.stall_threshold:
            return LoopStatus.NO_PROGRESS, last_check, new_stall, True
        return None, last_check, new_stall, True

    # Validate patch
    patch_result = validate_patch(response, file_path, config)

    if patch_result.status == PatchStatus.NO_FIX:
        loop_logger.log_event(
            "patch_rejected", iteration, {"reason": "no_fix_possible"}
        )
        return LoopStatus.NO_FIX_POSSIBLE, last_check, stall_count, True

    if patch_result.status == PatchStatus.REJECTED:
        loop_logger.log_event(
            "patch_rejected", iteration, {"reason": patch_result.rejection_reason}
        )
        new_stall, record = _handle_patch_rejected(
            iteration,
            patch_result.rejection_reason or "unknown",
            sorries_before,
            admits_before,
            last_check,
            stall_count,
        )
        iterations.append(record)
        if new_stall >= config.stall_threshold:
            return LoopStatus.NO_PROGRESS, last_check, new_stall, True
        return None, last_check, new_stall, True

    # Apply patch (unless --no-apply)
    search_text = patch_result.search_text
    replace_text = patch_result.replace_text
    if search_text is None or replace_text is None:
        # Should never happen due to PatchStatus.OK contract
        return None, last_check, stall_count, True

    if no_apply:
        loop_logger.log_event("patch_skipped", iteration, {"reason": "no_apply"})
        iterations.append(
            IterationRecord(
                iteration=iteration,
                patch_applied=False,
                sorry_before=sorries_before,
                sorry_after=sorries_before,
                admit_before=admits_before,
                admit_after=admits_before,
                check_success=last_check.success,
                error_count=len(last_check.errors),
                reason="no_apply",
            )
        )
        # In no-apply mode, exit after first valid proposal
        return LoopStatus.NO_PROGRESS, last_check, stall_count, True

    # Apply the patch
    new_content, verification = _apply_and_verify_patch(
        file_path,
        search_text,
        replace_text,
        sorries_before,
        admits_before,
        size_before,
        config,
        loop_logger,
        iteration,
    )

    if verification.exit_condition == LoopExitCondition.REGRESSION:
        return LoopStatus.REGRESSION, last_check, stall_count, True

    # Record the iteration
    sorries_after = count_sorries(new_content)
    admits_after = count_admits(new_content)
    iterations.append(
        IterationRecord(
            iteration=iteration,
            patch_applied=True,
            sorry_before=sorries_before,
            sorry_after=sorries_after,
            admit_before=admits_before,
            admit_after=admits_after,
            check_success=True,
            error_count=0,
        )
    )

    # Update stall count based on progress
    new_stall = 0 if verification.is_progress else stall_count + 1

    # Check for completion
    if sorries_after == 0 and admits_after == 0:
        final_check = lean_runner.check(file_path, timeout=config.lean_timeout_seconds)
        if final_check.success:
            return (
                LoopStatus.SUCCESS,
                final_check,
                new_stall,
                True,
            )  # work_done=True (patch applied)

    return None, last_check, new_stall, True


def run_loop(
    *,
    problem: ProblemRecord,
    file_path: Path,
    config: LoopConfig,
    lean_runner: LeanRunner,
    llm_command: str | None,
    no_apply: bool = False,
    rag_chunks: list[Any] | None = None,
) -> LoopResult:
    """Run the iterative proof loop per spec-012-loop-command.md execution model."""
    if rag_chunks is None:
        rag_chunks = []

    # Set up logging
    log_path = Path("logs/loop") / f"{generate_run_id()}.jsonl"
    loop_logger = LoopLogger(log_path)
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

    try:
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
        for i in range(1, config.max_iterations + 1):
            terminal_status, last_check, stall_count, work_done = _run_single_iteration(
                iteration=i,
                file_path=file_path,
                problem=problem,
                config=config,
                lean_runner=lean_runner,
                llm_command=llm_command,
                no_apply=no_apply,
                rag_chunks=rag_chunks,
                loop_logger=loop_logger,
                iterations=iterations,
                stall_count=stall_count,
            )
            if terminal_status is not None:
                completed = i if work_done else i - 1
                return make_result(terminal_status, completed, last_check, iterations)

        # Max iterations reached
        return make_result(
            LoopStatus.MAX_ITERATIONS, config.max_iterations, last_check, iterations
        )

    finally:
        loop_logger.close()
