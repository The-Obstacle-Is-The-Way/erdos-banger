"""erdos search - search problem statements.

# exempt: DEBT-096 (509 LOC; CLI + multiple search modes including MSC/zbMATH)

This module is a thin CLI adapter that parses Typer flags and delegates
to the core search service (erdos.core.search.service).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import requests
import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import console, err_console, exit_with_result
from erdos.core.clients.zbmath import ZbMathClient, ZbMathConfig, zbmath_entry_to_json
from erdos.core.constants import DEFAULT_SEARCH_LIMIT
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
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


app = typer.Typer(
    help="Search problem statements.",
    context_settings={"allow_interspersed_args": True},
)


def _print_msc_human(data: dict[str, Any]) -> None:
    """Pretty-print MSC search results from zbMATH."""
    entries = data.get("entries", [])
    msc_code = data.get("msc", "")
    year_min = data.get("year_min")
    year_max = data.get("year_max")

    # Print header
    console.print(f"[bold]MSC Search:[/bold] {msc_code}")
    if year_min or year_max:
        year_range = f"{year_min or ''}-{year_max or ''}"
        console.print(f"[bold]Year Range:[/bold] {year_range}")
    console.print(f"[bold]Results:[/bold] {len(entries)}")
    console.print()

    if not entries:
        console.print("No entries found.")
        return

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "Unknown")
        authors = "; ".join(entry.get("authors", [])[:3])
        if len(entry.get("authors", [])) > 3:
            authors += " et al."
        year = entry.get("year", "")
        year_str = f" ({year})" if year else ""
        msc_codes = ", ".join(m.get("code", "") for m in entry.get("msc", [])[:3])

        console.print(f"[bold]{i}.[/bold] {title!r}{year_str}")
        if authors:
            console.print(f"    [dim]Authors:[/dim] {authors}")
        if msc_codes:
            console.print(f"    [dim]MSC:[/dim] {msc_codes}")
        console.print()


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print search results."""
    results = result_data.get("results", [])
    query = result_data.get("query", "")
    mode = result_data.get("mode", "bm25")

    if not results:
        console.print(f"No results for: {query}")
        return

    console.print(f"[bold]Search results for:[/bold] {query}")

    # Display mode info
    mode_labels = {
        "bm25": "[dim]Using BM25 ranking[/dim]",
        "semantic": "[dim]Using semantic (vector) search[/dim]",
        "hybrid": f"[dim]Using hybrid search (alpha={result_data.get('alpha', 0.5)})[/dim]",
        "basic": "[dim]Using basic substring search (run 'erdos search --build-index' for better results)[/dim]",
    }
    console.print(mode_labels.get(mode, "[dim]Search mode: unknown[/dim]"))
    console.print()

    for i, r in enumerate(results, 1):
        problem_id = r.get("problem_id")
        title = r.get("title") or ""
        snippet = r.get("snippet") or ""
        source_type = r.get("source_type", "")

        if problem_id:
            console.print(f"[cyan]{i}.[/cyan] Problem {problem_id}: {title}")
        else:
            console.print(f"[cyan]{i}.[/cyan] Reference")

        if snippet:
            console.print(f"   {snippet}")

        # Build score display based on mode
        scores_parts = []
        if r.get("score") is not None:
            scores_parts.append(f"BM25: {r['score']:.2f}")
        if r.get("semantic_score") is not None:
            scores_parts.append(f"Semantic: {r['semantic_score']:.2f}")
        if r.get("hybrid_score") is not None and mode == "hybrid":
            scores_parts.append(f"Hybrid: {r['hybrid_score']:.2f}")

        if scores_parts or source_type:
            score_str = " | ".join(scores_parts) if scores_parts else ""
            if source_type:
                score_str = (
                    f"{score_str} | Source: {source_type}"
                    if score_str
                    else f"Source: {source_type}"
                )
            console.print(f"   [dim]{score_str}[/dim]")
        console.print()


def _validate_mode_flags(
    semantic: bool,
    hybrid: bool,
    bm25_only: bool,
    alpha: float | None,
    msc: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    build_index_flag: bool = False,
    build_embeddings_flag: bool = False,
) -> CLIOutput | None:
    """Validate mutually exclusive mode flags.

    Returns CLIOutput error if validation fails, None if valid.
    """
    error_message: str | None = None

    # --msc is incompatible with other search modes and index ops
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
    limit: int,
    year_min: int | None,
    year_max: int | None,
) -> CLIOutput:
    """Execute MSC search via zbMATH API (SPEC-031).

    Args:
        msc: MSC code to search.
        limit: Maximum results.
        year_min: Optional minimum year filter.
        year_max: Optional maximum year filter.

    Returns:
        CLIOutput with search results or error.
    """
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


def _get_search_mode(semantic: bool, hybrid: bool) -> SearchMode:
    """Determine search mode from flags."""
    if semantic:
        return SearchMode.SEMANTIC
    if hybrid:
        return SearchMode.HYBRID
    return SearchMode.BM25


def _handle_index_build(
    build_index_flag: bool,
    index: SearchIndexProtocol | None,
    progress_console: Console,
    *,
    repo: ProblemRepository,
    repo_root: Path | None,
) -> CLIOutput | None:
    """Handle index building if requested.

    Returns CLIOutput error if build fails, None on success.
    """
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

    # Get stats for display
    stats = index.get_stats()
    progress_console.print(
        f"[green]✓[/green] Indexed {stats.get('problems', 0)} problems"
    )
    return None


def _handle_embeddings_build(
    build_embeddings_flag: bool,
    index: SearchIndexProtocol | None,
    progress_console: Console,
    model_name: str,
) -> CLIOutput | None:
    """Handle embeddings building if requested.

    Returns CLIOutput error if build fails, None on success.
    """
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


@app.callback(invoke_without_command=True)
def search(
    ctx: typer.Context,
    query: Annotated[
        str | None,
        typer.Argument(
            help="Search query (supports FTS5 syntax when index exists). "
            "Not required when using --msc."
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum results to return",
            min=1,
            max=1000,
        ),
    ] = DEFAULT_SEARCH_LIMIT,
    problem_filter: Annotated[
        int | None,
        typer.Option("--problem", "-p", help="Filter to specific problem ID"),
    ] = None,
    build_index_flag: Annotated[
        bool,
        typer.Option(
            "--build-index", help="Build/rebuild the search index before searching"
        ),
    ] = False,
    # SPEC-014: Semantic search flags
    semantic: Annotated[
        bool,
        typer.Option(
            "--semantic", "-s", help="Use semantic (vector) search instead of BM25"
        ),
    ] = False,
    hybrid: Annotated[
        bool,
        typer.Option("--hybrid", help="Combine BM25 and semantic scores"),
    ] = False,
    bm25_only: Annotated[
        bool,
        typer.Option("--bm25-only", help="Force BM25-only search (no vectors)"),
    ] = False,
    alpha: Annotated[
        float | None,
        typer.Option(
            "--alpha",
            help="Hybrid weight (0.0=BM25 only, 1.0=semantic only, default: 0.5)",
            min=0.0,
            max=1.0,
            show_default=False,
        ),
    ] = None,
    build_embeddings_flag: Annotated[
        bool,
        typer.Option(
            "--build-embeddings",
            help="Build/rebuild embeddings (requires embeddings optional deps)",
        ),
    ] = False,
    embedding_model: Annotated[
        str,
        typer.Option(
            "--embedding-model",
            help="Embedding model name",
        ),
    ] = "sentence-transformers/all-MiniLM-L6-v2",
    # SPEC-031: MSC search mode
    msc: Annotated[
        str | None,
        typer.Option(
            "--msc",
            help="Search zbMATH by MSC code (e.g., '11B05'). "
            "Incompatible with other search modes.",
        ),
    ] = None,
    year_min: Annotated[
        int | None,
        typer.Option("--year-min", help="Minimum publication year (for --msc mode)"),
    ] = None,
    year_max: Annotated[
        int | None,
        typer.Option("--year-max", help="Maximum publication year (for --msc mode)"),
    ] = None,
) -> None:
    """
    Search problem statements for a query.

    Supports FTS5 syntax when index exists:
      - "exact phrase" for phrase match
      - word* for prefix match
      - word1 OR word2 for alternatives
      - NOT word to exclude

    Search modes (mutually exclusive):
      --bm25-only  : BM25 keyword search (default)
      --semantic   : Semantic (vector) search
      --hybrid     : Combined BM25 + semantic (use --alpha to adjust weight)
      --msc CODE   : Search zbMATH by MSC code (SPEC-031)

    Example: erdos search "prime"
    Example: erdos search "prime gaps" --semantic
    Example: erdos search "consecutive primes" --hybrid --alpha 0.6
    Example: erdos search --msc "11B05" --year-min 2000
    """
    json_mode = bool((ctx.obj or {}).get("json"))
    progress_console = err_console if json_mode else console

    result: CLIOutput | None = None

    with measure_time_ms() as duration:
        effective_alpha = 0.5 if alpha is None else alpha
        # Validate mode flags
        result = _validate_mode_flags(
            semantic,
            hybrid,
            bm25_only,
            alpha,
            msc=msc,
            year_min=year_min,
            year_max=year_max,
            build_index_flag=build_index_flag,
            build_embeddings_flag=build_embeddings_flag,
        )

        # Handle --msc mode (SPEC-031)
        if result is None and msc is not None:
            result = _execute_msc_search(msc, limit, year_min, year_max)

        # Normal search mode
        elif result is None:
            # Query is required for normal search
            if query is None or query.strip() == "":
                result = CLIOutput.err(
                    command="erdos search",
                    error_type="UsageError",
                    message="A search query is required (or use --msc for MSC search)",
                    code=ExitCode.USAGE_ERROR,
                )
            else:
                app_ctx, app_error = get_app_context(ctx, command="erdos search")
                if app_error is not None or app_ctx is None:
                    result = app_error
                else:
                    # Best-effort index: if it can't be opened, fallback to basic
                    index: SearchIndexProtocol | None
                    try:
                        index = app_ctx.ensure_index()
                    except SearchIndexError:
                        index = None

                    # Build index if requested
                    result = _handle_index_build(
                        build_index_flag,
                        index,
                        progress_console,
                        repo=app_ctx.problems,
                        repo_root=app_ctx.config.repo_root,
                    )

                    # Build embeddings if requested
                    if result is None:
                        result = _handle_embeddings_build(
                            build_embeddings_flag,
                            index,
                            progress_console,
                            embedding_model,
                        )

                    # Perform the search
                    if result is None:
                        mode = _get_search_mode(semantic, hybrid)
                        options = SearchOptions(
                            query=query,
                            limit=limit,
                            problem_id=problem_filter,
                            build_index=False,
                            build_embeddings=False,
                            mode=mode,
                            alpha=effective_alpha,
                            embedding_model=embedding_model,
                        )
                        result = execute_search(
                            options,
                            index=index,
                            repo=app_ctx.problems,
                        )

    if result is not None:
        result.duration_ms = duration[0]
        # Use MSC-specific printer for MSC mode
        if msc is not None:
            exit_with_result(ctx, result, print_human=_print_msc_human)
        else:
            exit_with_result(ctx, result, print_human=_print_human)
