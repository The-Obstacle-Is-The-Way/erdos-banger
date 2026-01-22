"""erdos lean status - Show formalization status for problems."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.lean.common import UPSTREAM_METADATA_PATH, print_human
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.formal_conjectures import (
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
    LocalFormalizationInfo,
    build_upstream_url,
    get_local_file_path,
    load_upstream_metadata,
)
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository

logger = logging.getLogger(__name__)


def _get_comparison(upstream_formalized: bool, local_exists: bool) -> str:
    """Get comparison string between upstream and local status."""
    if upstream_formalized and local_exists:
        return "both_exist"
    if upstream_formalized:
        return "upstream_only"
    if local_exists:
        return "local_only"
    return "neither"


def _get_upstream_data(
    problem_id: int,
    upstream_info: dict[int, Any],
    check_upstream: bool,
) -> dict[str, Any]:
    """Build upstream data dict for status response."""
    if not check_upstream or problem_id not in upstream_info:
        return {"available": False}
    info = upstream_info[problem_id]
    return {
        "available": True,
        "formalized": info.formalized,
        "state": info.state,
        "last_update": info.last_update,
        "source": FORMAL_CONJECTURES_REPO,
        "url": build_upstream_url(problem_id) if info.formalized else None,
    }


def _get_local_data(
    project_path: Path, problem_id: int, check_local: bool
) -> dict[str, Any]:
    """Build local data dict for status response."""
    if not check_local:
        return {"exists": False}
    local_path = get_local_file_path(project_path, problem_id)
    local_info = LocalFormalizationInfo.from_file(local_path)
    if not local_info.exists:
        return {"exists": False}
    return {
        "exists": True,
        "path": str(local_path),
        "has_sorry": local_info.has_sorry,
        "sha256": local_info.sha256,
    }


def _get_single_problem_status(
    problem_id: int,
    project_path: Path,
    repo: ProblemRepository,
    upstream_info: dict[int, Any],
    check_upstream: bool,
    check_local: bool,
) -> CLIOutput:
    """Get status for a single problem."""
    problem = repo.get_by_id(problem_id)
    if problem is None:
        return CLIOutput.err(
            command="erdos lean status",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    upstream_data = _get_upstream_data(problem_id, upstream_info, check_upstream)
    local_data = _get_local_data(project_path, problem_id, check_local)
    comparison = _get_comparison(
        upstream_data.get("formalized", False), local_data.get("exists", False)
    )

    return CLIOutput.ok(
        command="erdos lean status",
        data={
            "problem_id": problem_id,
            "upstream": upstream_data,
            "local": local_data,
            "comparison": comparison,
        },
    )


def _get_all_problems_status(
    project_path: Path,
    repo: ProblemRepository,
    upstream_info: dict[int, Any],
    *,
    check_upstream: bool,
    check_local: bool,
) -> CLIOutput:
    """Get summary status for all problems."""
    problems = repo.load_all()
    total = len(problems)

    upstream_formalized = 0
    if check_upstream:
        upstream_formalized = sum(
            1
            for p in problems
            if (upstream := upstream_info.get(p.id)) and upstream.formalized
        )

    local_exists = 0
    if check_local:
        local_exists = sum(
            1 for p in problems if get_local_file_path(project_path, p.id).exists()
        )

    return CLIOutput.ok(
        command="erdos lean status",
        data={
            "summary": {
                "total": total,
                "upstream_formalized": upstream_formalized,
                "local_exists": local_exists,
                "checked": {"upstream": check_upstream, "local": check_local},
            }
        },
    )


def get_formalization_status(
    problem_id: int | None,
    project_path: Path,
    *,
    repo: ProblemRepository,
    check_upstream: bool = True,
    check_local: bool = True,
) -> CLIOutput:
    """Get formalization status for a problem or all problems."""
    try:
        upstream_info: dict[int, Any] = {}
        if check_upstream:
            if not UPSTREAM_METADATA_PATH.exists():
                return CLIOutput.err(
                    command="erdos lean status",
                    error_type="ConfigError",
                    message=f"Upstream metadata not found: {UPSTREAM_METADATA_PATH}. "
                    "Run 'git submodule update --init --recursive' to fetch.",
                    code=ExitCode.CONFIG_ERROR,
                )
            upstream_info = load_upstream_metadata(UPSTREAM_METADATA_PATH)

        if problem_id is not None:
            return _get_single_problem_status(
                problem_id,
                project_path,
                repo,
                upstream_info,
                check_upstream,
                check_local,
            )
        return _get_all_problems_status(
            project_path,
            repo,
            upstream_info,
            check_upstream=check_upstream,
            check_local=check_local,
        )
    except FormalConjecturesError as e:
        return CLIOutput.err(
            command="erdos lean status",
            error_type=e.error_type,
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean status command")
        return CLIOutput.err(
            command="erdos lean status",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def register(app: typer.Typer) -> None:
    """Register status command on the app."""

    @app.command()
    def status(
        ctx: typer.Context,
        problem_id: Annotated[
            int | None,
            typer.Argument(
                help="Problem ID (optional; shows summary if omitted).",
                min=1,
            ),
        ] = None,
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                help="Path to Lean project (default: formal/lean/)",
            ),
        ] = None,
        upstream: Annotated[
            bool,
            typer.Option(
                "--upstream", help="Check upstream metadata for formalization status"
            ),
        ] = False,
        local: Annotated[
            bool,
            typer.Option("--local", help="Check local formal/lean/Erdos/ directory"),
        ] = False,
    ) -> None:
        """
        Show formalization status for problems.

        Without PROBLEM_ID, shows summary counts.
        With PROBLEM_ID, shows detailed status for that problem.

        Example: erdos lean status 6
        """
        with measure_time_ms() as duration:
            app_ctx, app_error = get_app_context(ctx, command="erdos lean status")
            if app_error is not None:
                exit_with_result(ctx, app_error)
                return
            if app_ctx is None:
                return

            path = project_path or Path("formal/lean")

            # Default: check both if neither specified
            check_upstream = upstream or not (upstream or local)
            check_local = local or not (upstream or local)

            result = get_formalization_status(
                problem_id,
                path,
                repo=app_ctx.problems,
                check_upstream=check_upstream,
                check_local=check_local,
            )

        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=print_human)
