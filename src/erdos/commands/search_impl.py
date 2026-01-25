"""Implementation helpers for `erdos search`.

This module keeps the Typer callback in `erdos.commands.search` small and focused:
- parse flags
- delegate orchestration here
- render results via presenter
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import console, err_console
from erdos.commands.search_output import PrintHuman, print_msc_human, print_search_human
from erdos.core.clients.zbmath import ZbMathClient, ZbMathConfig, zbmath_entry_to_json
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.search import (
    SearchMode,
    SearchOptions,
    build_embeddings,
    build_search_index,
    execute_search,
)
from erdos.core.search.db import SearchIndexError


if TYPE_CHECKING:
    from pathlib import Path

    import typer
    from rich.console import Console

    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


def _validate_mode_flags(
    *,
    semantic: bool,
    hybrid: bool,
    bm25_only: bool,
    alpha: float | None,
    msc: str | None,
    year_min: int | None,
    year_max: int | None,
    build_index_flag: bool,
    build_embeddings_flag: bool,
) -> CLIOutput | None:
    """Validate mutually exclusive mode flags."""
    error_message: str | None = None

    if msc is not None:
        incompatible_flags = [
            (semantic, "--semantic"),
            (hybrid, "--hybrid"),
            (bm25_only, "--bm25-only"),
            (alpha is not None, "--alpha"),
            (build_index_flag, "--build-index"),
            (build_embeddings_flag, "--build-embeddings"),
        ]
        for flag_set, flag_name in incompatible_flags:
            if flag_set:
                error_message = (
                    f"--msc is incompatible with {flag_name} "
                    "(MSC search queries zbMATH API)"
                )
                break

        if (
            error_message is None
            and year_min is not None
            and year_max is not None
            and year_min > year_max
        ):
            error_message = "--year-min must be <= --year-max"

    elif sum([semantic, hybrid, bm25_only]) > 1:
        error_message = (
            "Flags --semantic, --hybrid, and --bm25-only are mutually exclusive"
        )
    elif alpha is not None and not hybrid:
        error_message = "--alpha requires --hybrid mode"

    if error_message:
        return CLIOutput.err(
            command="erdos search",
            error_type="UsageError",
            message=error_message,
            code=ExitCode.USAGE_ERROR,
        )
    return None


def _execute_msc_search(
    msc: str,
    *,
    limit: int,
    year_min: int | None,
    year_max: int | None,
) -> CLIOutput:
    """Execute MSC search via zbMATH API (SPEC-031)."""
    try:
        config = ZbMathConfig.from_env()
        client = ZbMathClient(config)

        entries = client.search_by_msc(
            msc,
            limit=limit,
            year_min=year_min,
            year_max=year_max,
        )

        data: dict[str, Any] = {
            "mode": "msc",
            "msc": msc,
            "limit": limit,
            "year_min": year_min,
            "year_max": year_max,
            "entries": [zbmath_entry_to_json(e) for e in entries],
            "returned": len(entries),
        }

        return CLIOutput.ok(command="erdos search", data=data)

    except requests.HTTPError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="ZbMathError",
            message=f"zbMATH API error: {e}",
            code=ExitCode.ERROR,
        )
    except requests.RequestException as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="ZbMathError",
            message=f"zbMATH request error: {e}",
            code=ExitCode.ERROR,
        )


def _get_search_mode(*, semantic: bool, hybrid: bool) -> SearchMode:
    if semantic:
        return SearchMode.SEMANTIC
    if hybrid:
        return SearchMode.HYBRID
    return SearchMode.BM25


def _handle_index_build(
    *,
    build_index_flag: bool,
    index: SearchIndexProtocol | None,
    progress_console: Console,
    repo: ProblemRepository,
    repo_root: Path | None,
) -> CLIOutput | None:
    if not build_index_flag:
        return None

    if index is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message="Search index is unavailable in this environment",
            code=ExitCode.ERROR,
        )

    progress_console.print("Building search index...")
    error = build_search_index(repo=repo, index=index, repo_root=repo_root)
    if error:
        return error

    stats = index.get_stats()
    progress_console.print(
        f"[green]✓[/green] Indexed {stats.get('problems', 0)} problems"
    )
    return None


def _handle_embeddings_build(
    *,
    build_embeddings_flag: bool,
    index: SearchIndexProtocol | None,
    progress_console: Console,
    model_name: str,
) -> CLIOutput | None:
    if not build_embeddings_flag:
        return None

    if index is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message="Search index is unavailable",
            code=ExitCode.ERROR,
        )

    progress_console.print(f"Building embeddings with model: {model_name}...")
    count, error = build_embeddings(index=index, model_name=model_name)
    if error:
        return error

    progress_console.print(f"[green]✓[/green] Embedded {count} chunks")
    return None


def execute_search_command(
    ctx: typer.Context,
    *,
    query: str | None,
    limit: int,
    problem_filter: int | None,
    build_index_flag: bool,
    semantic: bool,
    hybrid: bool,
    bm25_only: bool,
    alpha: float | None,
    build_embeddings_flag: bool,
    embedding_model: str,
    msc: str | None,
    year_min: int | None,
    year_max: int | None,
) -> tuple[CLIOutput, PrintHuman]:
    """Execute `erdos search`, returning a CLIOutput and human printer."""
    json_mode = bool(ctx.obj.get("json", False)) if isinstance(ctx.obj, dict) else False
    progress_console = err_console if json_mode else console

    printer: PrintHuman = print_search_human

    # MSC mode is mutually exclusive with other search modes and index ops.
    mode_validation_error = _validate_mode_flags(
        semantic=semantic,
        hybrid=hybrid,
        bm25_only=bm25_only,
        alpha=alpha,
        msc=msc,
        year_min=year_min,
        year_max=year_max,
        build_index_flag=build_index_flag,
        build_embeddings_flag=build_embeddings_flag,
    )
    if mode_validation_error is not None:
        return mode_validation_error, printer

    if msc is not None:
        return (
            _execute_msc_search(msc, limit=limit, year_min=year_min, year_max=year_max),
            print_msc_human,
        )

    query_str = (query or "").strip()
    if query_str == "":
        return (
            CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="A search query is required (or use --msc for MSC search)",
                code=ExitCode.USAGE_ERROR,
            ),
            printer,
        )

    app_ctx, app_error = get_app_context(ctx, command="erdos search")
    if app_error is not None or app_ctx is None:
        return (
            app_error
            if app_error is not None
            else CLIOutput.err(
                command="erdos search",
                error_type="InternalError",
                message="App context unavailable (unexpected)",
                code=ExitCode.ERROR,
            ),
            printer,
        )

    try:
        index: SearchIndexProtocol | None = app_ctx.ensure_index()
    except SearchIndexError:
        index = None

    error = _handle_index_build(
        build_index_flag=build_index_flag,
        index=index,
        progress_console=progress_console,
        repo=app_ctx.problems,
        repo_root=app_ctx.config.repo_root,
    )
    if error is None:
        error = _handle_embeddings_build(
            build_embeddings_flag=build_embeddings_flag,
            index=index,
            progress_console=progress_console,
            model_name=embedding_model,
        )
    if error is not None:
        return error, printer

    effective_alpha = 0.5 if alpha is None else alpha
    mode = _get_search_mode(semantic=semantic, hybrid=hybrid)

    options = SearchOptions(
        query=query_str,
        limit=limit,
        problem_id=problem_filter,
        build_index=False,
        build_embeddings=False,
        mode=mode,
        alpha=effective_alpha,
        embedding_model=embedding_model,
    )

    return execute_search(options, index=index, repo=app_ctx.problems), printer
