"""erdos lean formalize - Generate Lean skeletons for problems."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer


if TYPE_CHECKING:
    from erdos.core.context import AppContext
    from erdos.core.ports import ProblemRepository

from erdos.commands.app_context import get_app_context
from erdos.commands.lean.batch_formalize import (
    batch_formalize,
    batch_result_to_cli_output,
    formalize_problem,
)
from erdos.commands.lean.common import (
    err_console,
    print_human,
    print_human_batch_formalize,
)
from erdos.commands.lean.import_cmd import import_upstream_formalization
from erdos.commands.presenter import exit_with_result
from erdos.core.batch import (
    BatchFilters,
    BatchProgress,
    filter_problem_ids,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


_COMMAND = "erdos lean formalize"


@dataclass
class _FormalizeArgs:
    """Validated arguments for formalize command."""

    problem_id: int | None
    project_path: Path
    force: bool
    import_upstream: bool
    no_network: bool
    all_problems: bool
    status: str | None
    tag: list[str] | None
    limit: int | None
    skip_existing: bool
    dry_run: bool
    max_concurrent: int
    json_mode: bool

    @property
    def batch_mode(self) -> bool:
        """Determine if batch mode should be activated."""
        if self.all_problems:
            return True
        if self.problem_id is None:
            return bool(self.status is not None or self.tag)
        return False


def _validate_args(args: _FormalizeArgs) -> CLIOutput | None:
    """Validate formalize arguments. Returns error CLIOutput if invalid, None if OK."""
    if not args.batch_mode and args.problem_id is None:
        return CLIOutput.err(
            command=_COMMAND,
            error_type="UsageError",
            message="Provide a PROBLEM_ID or use batch options (--all, --status, --tag)",
            code=ExitCode.USAGE_ERROR,
        )
    if args.max_concurrent < 1:
        return CLIOutput.err(
            command=_COMMAND,
            error_type="UsageError",
            message="--max-concurrent must be >= 1",
            code=ExitCode.USAGE_ERROR,
        )
    if args.no_network and not args.import_upstream:
        return CLIOutput.err(
            command=_COMMAND,
            error_type="UsageError",
            message="--no-network requires --import-upstream",
            code=ExitCode.USAGE_ERROR,
        )
    return None


def _run_batch_formalize(
    problem_ids: list[int],
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
    skip_existing: bool,
    max_concurrent: int,
    dry_run: bool,
    json_mode: bool,
) -> CLIOutput:
    """Execute batch formalize logic."""
    if dry_run:
        data = {
            "batch_id": "",
            "mode": "batch",
            "total": len(problem_ids),
            "completed": 0,
            "failed": 0,
            "failed_ids": [],
            "dry_run": True,
            "problem_ids": problem_ids,
        }
        return CLIOutput.ok(command=_COMMAND, data=data)

    def on_progress(progress: BatchProgress) -> None:
        status_icon = "[green]✓[/green]" if progress.success else "[red]✗[/red]"
        err_console.print(
            f"[{progress.index + 1}/{progress.total}] Problem {progress.problem_id}... "
            f"{status_icon} ({progress.message})"
        )

    result = batch_formalize(
        problem_ids,
        project_path,
        repo=repo,
        force=force,
        skip_existing=skip_existing,
        max_concurrent=max_concurrent,
        on_progress=None if json_mode else on_progress,
    )
    return batch_result_to_cli_output(result, problem_ids, dry_run)


def _execute_formalize(args: _FormalizeArgs, app_ctx: AppContext) -> CLIOutput:
    """Execute formalize based on mode (batch/single/import)."""
    if args.batch_mode:
        filters = BatchFilters(status=args.status, tags=args.tag, limit=args.limit)
        problems = app_ctx.problems.load_all()
        problem_ids = filter_problem_ids(problems, filters)
        if not problem_ids:
            return CLIOutput.err(
                command=_COMMAND,
                error_type="NotFoundError",
                message="No problems match the given filters",
                code=ExitCode.NOT_FOUND,
            )
        return _run_batch_formalize(
            problem_ids,
            args.project_path,
            repo=app_ctx.problems,
            force=args.force,
            skip_existing=args.skip_existing,
            max_concurrent=args.max_concurrent,
            dry_run=args.dry_run,
            json_mode=args.json_mode,
        )

    if args.problem_id is not None and args.import_upstream:
        return import_upstream_formalization(
            args.problem_id,
            args.project_path,
            force=args.force,
            no_network=args.no_network,
            skip_lean_validation=True,
        )

    if args.problem_id is not None:
        return formalize_problem(
            args.problem_id,
            args.project_path,
            repo=app_ctx.problems,
            force=args.force,
        )

    # Unreachable due to earlier validation
    return CLIOutput.err(
        command=_COMMAND,
        error_type="UsageError",
        message="Provide a PROBLEM_ID or use batch options",
        code=ExitCode.USAGE_ERROR,
    )


def register(app: typer.Typer) -> None:
    """Register formalize command on the app."""

    @app.command()
    def formalize(
        ctx: typer.Context,
        problem_id: Annotated[
            int | None,
            typer.Argument(
                help="Problem ID to formalize (omit for batch mode).", min=1
            ),
        ] = None,
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path", "-p", help="Path to Lean project (default: formal/lean/)"
            ),
        ] = None,
        force: Annotated[
            bool, typer.Option("--force", "-f", help="Overwrite existing file")
        ] = False,
        import_upstream: Annotated[
            bool,
            typer.Option(
                "--import-upstream",
                help="Import upstream formalization instead of generating skeleton",
            ),
        ] = False,
        no_network: Annotated[
            bool,
            typer.Option(
                "--no-network",
                help="Use cached upstream file only (requires --import-upstream)",
            ),
        ] = False,
        all_problems: Annotated[
            bool, typer.Option("--all", help="Process all problems (batch mode)")
        ] = False,
        status: Annotated[
            str | None,
            typer.Option(
                "--status",
                help="Filter by status: open, proved, disproved, partially_solved, unknown",
            ),
        ] = None,
        tag: Annotated[
            list[str] | None,
            typer.Option("--tag", help="Filter by tag (can be repeated)"),
        ] = None,
        limit: Annotated[
            int | None, typer.Option("--limit", help="Max problems to process")
        ] = None,
        skip_existing: Annotated[
            bool,
            typer.Option(
                "--skip-existing", help="Skip problems with existing Lean files"
            ),
        ] = False,
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Show what would be processed")
        ] = False,
        max_concurrent: Annotated[
            int,
            typer.Option(
                "--max-concurrent", help="Max parallel Lean compilations (default: 4)"
            ),
        ] = 4,
    ) -> None:
        """
        Generate Lean skeletons for problems.

        Single mode: Pass a PROBLEM_ID to formalize one problem.

        Batch mode: Omit PROBLEM_ID and use --all or filter options (--status, --tag)
        to process multiple problems. Supports parallel execution with --max-concurrent.

        Use --import-upstream to import existing formalizations instead.
        """
        args = _FormalizeArgs(
            problem_id=problem_id,
            project_path=project_path or Path("formal/lean"),
            force=force,
            import_upstream=import_upstream,
            no_network=no_network,
            all_problems=all_problems,
            status=status,
            tag=tag,
            limit=limit,
            skip_existing=skip_existing,
            dry_run=dry_run,
            max_concurrent=max_concurrent,
            json_mode=bool((ctx.obj or {}).get("json")),
        )

        if validation_error := _validate_args(args):
            exit_with_result(ctx, validation_error, print_human=print_human)
            return

        with measure_time_ms() as duration:
            app_ctx, app_error = get_app_context(ctx, command=_COMMAND)
            if app_error is not None:
                exit_with_result(ctx, app_error)
                return
            if app_ctx is None:
                return  # Unreachable
            result = _execute_formalize(args, app_ctx)

        result.duration_ms = duration[0]
        print_fn = print_human_batch_formalize if args.batch_mode else print_human
        exit_with_result(ctx, result, print_human=print_fn)
