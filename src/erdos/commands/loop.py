"""erdos loop - Iterative Lean proof attempts."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.formalizer import generate_skeleton
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.loop import LoopStatus, run_loop
from erdos.core.loop_config import LoopConfig
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


logger = logging.getLogger(__name__)


app = typer.Typer(help="Iterative Lean proof loop.")
console = Console()


def _print_human_result(result_data: dict[str, Any]) -> None:
    """Pretty-print loop result."""
    status = result_data.get("status", "unknown")
    problem_id = result_data.get("problem_id")
    iterations = result_data.get("iterations_completed", 0)
    max_iter = result_data.get("iterations_max", 0)
    file_path = result_data.get("file", "")

    if status == "success":
        console.print(f"[green]✓[/green] Problem {problem_id} proof complete!")
        console.print(f"  File: {file_path}")
        console.print(f"  Iterations: {iterations}/{max_iter}")
    elif status == "no_fix_possible":
        console.print(f"[yellow]![/yellow] No fix possible for problem {problem_id}")
        console.print("  The LLM indicated it cannot fix the current state.")
    elif status == "max_iterations":
        console.print(
            f"[yellow]![/yellow] Reached maximum iterations ({max_iter}) "
            f"for problem {problem_id}"
        )
    elif status == "llm_required":
        console.print(
            f"[yellow]![/yellow] LLM required but not configured for problem {problem_id}"
        )
        console.print(
            "  Set ERDOS_LLM_COMMAND or use --llm-cmd to specify an LLM command."
        )
    elif status == "no_progress":
        console.print(
            f"[yellow]![/yellow] No progress after {iterations} iterations "
            f"for problem {problem_id}"
        )
    elif status == "regression":
        console.print(f"[red]✗[/red] Regression detected for problem {problem_id}")
        console.print("  File size shrank unexpectedly (possible deletion attack).")
    else:
        console.print(f"[red]✗[/red] Loop failed for problem {problem_id}: {status}")

    # Show iteration details
    iter_records = result_data.get("iterations", [])
    if iter_records:
        console.print("\nIterations:")
        for rec in iter_records:
            patch_str = (
                "[green]applied[/green]"
                if rec.get("patch_applied")
                else "[dim]skipped[/dim]"
            )
            sorry_before = rec.get("sorry_before", "?")
            sorry_after = rec.get("sorry_after", "?")
            console.print(
                f"  [{rec['iteration']}] {patch_str} "
                f"sorry: {sorry_before} → {sorry_after}"
            )


# ============================================================================
# Core Logic
# ============================================================================


def execute_loop(  # noqa: PLR0911
    problem_id: int,
    *,
    repo: ProblemRepository,
    project_path: Path,
    config: LoopConfig,
    llm_command: str | None,
    no_apply: bool,
) -> CLIOutput:
    """Execute the loop for a problem.

    # exempt: DEBT-042

    Args:
        problem_id: Problem ID
        repo: Problem repository
        project_path: Path to Lean project
        config: Loop configuration
        llm_command: LLM command (or None)
        no_apply: If True, don't write changes

    Returns:
        CLIOutput with result
    """
    # Get problem
    problem = repo.get_by_id(problem_id)
    if problem is None:
        return CLIOutput.err(
            command="erdos loop",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    # Ensure Lean project exists
    if not project_path.exists():
        try:
            runner = LeanRunner(project_path)
            runner.init(fetch_mathlib=True)
        except LeanRunnerError as e:
            return CLIOutput.err(
                command="erdos loop",
                error_type="InitError",
                message=f"Failed to initialize Lean project: {e}",
                code=ExitCode.ERROR,
            )

    # Ensure Lean file exists
    file_path = project_path / "Erdos" / f"Problem{problem_id:03d}.lean"
    if not file_path.exists():
        try:
            generate_skeleton(problem, project_path, overwrite=False)
        except Exception as e:
            return CLIOutput.err(
                command="erdos loop",
                error_type="FormalizerError",
                message=f"Failed to generate skeleton: {e}",
                code=ExitCode.ERROR,
            )

    # Create Lean runner
    try:
        lean_runner = LeanRunner(project_path)
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos loop",
            error_type="LeanRunnerError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    # Run the loop
    try:
        result = run_loop(
            problem=problem,
            file_path=file_path,
            config=config,
            lean_runner=lean_runner,
            llm_command=llm_command,
            no_apply=no_apply,
        )
    except Exception as e:
        logger.exception("Loop execution failed")
        return CLIOutput.err(
            command="erdos loop",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )

    # Map result to CLIOutput
    # Per spec-012: success=true ONLY when proof is complete (zero sorry/admit, compiles)
    # All other statuses return success=false with loop data in error object
    result_dict = result.to_dict()

    if result.status == LoopStatus.SUCCESS:
        return CLIOutput.ok(
            command="erdos loop",
            data=result_dict,
        )

    # Map status to error type and exit code
    status_map: dict[LoopStatus, tuple[str, str, ExitCode]] = {
        LoopStatus.MAX_ITERATIONS: (
            "MaxIterations",
            f"Reached maximum iterations ({result.iterations_max})",
            ExitCode.ERROR,
        ),
        LoopStatus.NO_PROGRESS: (
            "NoProgress",
            "No progress after multiple iterations",
            ExitCode.ERROR,
        ),
        LoopStatus.NO_FIX_POSSIBLE: (
            "NoFixPossible",
            "LLM indicated no fix is possible",
            ExitCode.ERROR,
        ),
        LoopStatus.REGRESSION: (
            "Regression",
            "File size shrank unexpectedly (possible deletion attack)",
            ExitCode.ERROR,
        ),
        LoopStatus.LLM_REQUIRED: (
            "LLMRequired",
            "LLM required but not configured (set ERDOS_LLM_COMMAND)",
            ExitCode.CONFIG_ERROR,
        ),
        LoopStatus.ERROR: (
            "Error",
            "Loop execution failed",
            ExitCode.ERROR,
        ),
    }

    error_type, message, exit_code = status_map.get(
        result.status, ("Error", f"Unknown status: {result.status}", ExitCode.ERROR)
    )

    # Include loop result data in error object per spec-012
    # (extra summary keys allowed by CLIOutput invariants)
    error_obj = {
        "type": error_type,
        "message": message,
        "code": int(exit_code),
        **result_dict,  # Include full loop result data
    }

    return CLIOutput(
        command="erdos loop",
        success=False,
        data=None,
        error=error_obj,
    )


# ============================================================================
# CLI Command
# ============================================================================


@app.command()
def run(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to work on.",
            min=1,
        ),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    max_iter: Annotated[
        int,
        typer.Option(
            "--max-iter",
            "-n",
            help="Maximum iterations (default: 10).",
            min=1,
        ),
    ] = 10,
    no_apply: Annotated[
        bool,
        typer.Option(
            "--no-apply",
            help="Propose changes only; never write to disk.",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="Lean check timeout in seconds (default: 120).",
            min=1,
        ),
    ] = 120,
    allow_sorry_increase: Annotated[
        int,
        typer.Option(
            "--allow-sorry-increase",
            help="Allow patch to increase sorry count by up to N (default: 0).",
            min=0,
        ),
    ] = 0,
    max_patch_lines: Annotated[
        int,
        typer.Option(
            "--max-patch-lines",
            help="Reject patches larger than this many lines (default: 50).",
            min=1,
        ),
    ] = 50,
    max_patch_bytes: Annotated[
        int,
        typer.Option(
            "--max-patch-bytes",
            help="Reject patches larger than this many bytes (default: 8192).",
            min=1,
        ),
    ] = 8192,
    rag_limit: Annotated[
        int,
        typer.Option(
            "--rag-limit",
            help="Maximum retrieved context chunks in prompt (default: 5).",
            min=0,
        ),
    ] = 5,
    llm_cmd: Annotated[
        str | None,
        typer.Option(
            "--llm-cmd",
            help="Override LLM command (default: from ERDOS_LLM_COMMAND env var).",
        ),
    ] = None,
) -> None:
    """
    Run iterative proof loop for a problem.

    This command runs an iterative "propose → apply → check" cycle to assist
    Lean formalization. Each iteration:

    1. Checks the current Lean file for errors
    2. Builds a prompt with the file, errors, and problem context
    3. Calls an external LLM to propose a fix
    4. Validates and applies the fix (if --no-apply is not set)
    5. Repeats until success or max iterations

    Safety guardrails:
    - Only modifies files under formal/lean/Erdos/
    - Rejects patches that add sorry or admit (by default)
    - Rejects patches larger than configured limits
    - Aborts if file shrinks by > 20%

    Example (propose only):

        erdos loop 6 --no-apply

    Example (auto-apply):

        ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos loop 6
    """
    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos loop")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return  # Unreachable

        path = project_path or Path("formal/lean")

        # Get LLM command from env if not specified
        llm_command = llm_cmd or os.environ.get("ERDOS_LLM_COMMAND")

        config = LoopConfig.from_cli(
            max_iterations=max_iter,
            lean_timeout_seconds=timeout,
            allow_sorry_increase=allow_sorry_increase,
            max_patch_lines=max_patch_lines,
            max_patch_bytes=max_patch_bytes,
            rag_limit=rag_limit,
        )

        result = execute_loop(
            problem_id,
            repo=app_ctx.problems,
            project_path=path,
            config=config,
            llm_command=llm_command,
            no_apply=no_apply,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human_result)
