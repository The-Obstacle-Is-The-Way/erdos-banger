"""Batch formalize orchestration for erdos lean formalize --all."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from erdos.core.batch import (
    BatchProgress,
    BatchResult,
    generate_batch_id,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.formal_conjectures import get_local_file_path
from erdos.core.formalizer import FormalizerError, generate_skeleton
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository

logger = logging.getLogger(__name__)


def formalize_problem(
    problem_id: int,
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
) -> CLIOutput:
    """Generate a Lean skeleton for a problem."""
    try:
        problem = repo.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos lean formalize",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )

        output_file = generate_skeleton(problem, project_path, overwrite=force)
        return CLIOutput.ok(
            command="erdos lean formalize",
            data={"problem_id": problem_id, "file": str(output_file)},
        )
    except FormalizerError as e:
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="FormalizerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean formalize command")
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def _formalize_single_problem(
    problem_id: int,
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
    skip_existing: bool,
) -> tuple[int, bool, str]:
    """Formalize a single problem (for batch mode).

    Returns:
        Tuple of (problem_id, success, message)
    """
    # Check if file exists
    local_path = get_local_file_path(project_path, problem_id)
    if skip_existing and local_path.exists():
        return (problem_id, True, "skipped (exists)")

    result = formalize_problem(problem_id, project_path, repo=repo, force=force)
    if result.success:
        return (problem_id, True, "OK")
    else:
        msg = (
            result.error.get("message", "unknown")
            if isinstance(result.error, dict)
            else "failed"
        )
        return (problem_id, False, msg)


def batch_formalize(
    problem_ids: list[int],
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool = False,
    skip_existing: bool = False,
    max_concurrent: int = 4,
    on_progress: Any | None = None,
) -> BatchResult:
    """Batch formalize multiple problems with optional parallelism.

    Args:
        problem_ids: List of problem IDs to formalize
        project_path: Path to Lean project
        repo: Problem repository
        force: Overwrite existing files
        skip_existing: Skip problems that already have Lean files
        max_concurrent: Max parallel Lean compilations (default: 4)
        on_progress: Callback for progress updates

    Returns:
        BatchResult with outcome details
    """
    batch_id = generate_batch_id()
    completed: list[int] = []
    failed: list[int] = []
    total = len(problem_ids)

    with measure_time_ms() as duration:
        if max_concurrent == 1:
            # Sequential execution
            for i, problem_id in enumerate(problem_ids):
                pid, success, message = _formalize_single_problem(
                    problem_id,
                    project_path,
                    repo=repo,
                    force=force,
                    skip_existing=skip_existing,
                )
                if success:
                    completed.append(pid)
                else:
                    failed.append(pid)

                if on_progress:
                    on_progress(
                        BatchProgress(
                            problem_id=pid,
                            index=i,
                            total=total,
                            success=success,
                            message=message,
                        )
                    )
        else:
            # Parallel execution using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(
                        _formalize_single_problem,
                        pid,
                        project_path,
                        repo=repo,
                        force=force,
                        skip_existing=skip_existing,
                    ): pid
                    for pid in problem_ids
                }

                for i, future in enumerate(as_completed(futures)):
                    pid, success, message = future.result()
                    if success:
                        completed.append(pid)
                    else:
                        failed.append(pid)

                    if on_progress:
                        on_progress(
                            BatchProgress(
                                problem_id=pid,
                                index=i,
                                total=total,
                                success=success,
                                message=message,
                            )
                        )

    return BatchResult(
        batch_id=batch_id,
        total=total,
        completed_count=len(completed),
        failed_count=len(failed),
        failed_ids=failed,
        duration_ms=duration[0],
    )


def batch_result_to_cli_output(
    result: BatchResult, problem_ids: list[int], dry_run: bool
) -> CLIOutput:
    """Convert BatchResult to CLIOutput for formalize command."""
    if result.exit_code != ExitCode.SUCCESS:
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="BatchError",
            message=result.error_message,
            code=result.exit_code,
        )

    data = {
        "batch_id": result.batch_id,
        "mode": "batch",
        "total": result.total,
        "completed": result.completed_count,
        "failed": result.failed_count,
        "failed_ids": result.failed_ids,
        "dry_run": dry_run,
    }

    if dry_run:
        data["problem_ids"] = problem_ids

    if result.failed_count > 0:
        message = (
            f"{result.failed_count} of {result.total} problems failed; "
            f"failed_ids={result.failed_ids}"
        )
        return CLIOutput(
            command="erdos lean formalize",
            success=False,
            data=None,
            error={
                "type": "PartialFailure",
                "message": message,
                "code": ExitCode.ERROR,
                "batch_id": result.batch_id,
                "mode": "batch",
                "total": result.total,
                "failed_count": result.failed_count,
                "succeeded_count": result.total - result.failed_count,
                "failed_ids": result.failed_ids,
                "completed": result.completed_count,
                "dry_run": dry_run,
            },
        )

    return CLIOutput.ok(command="erdos lean formalize", data=data)
