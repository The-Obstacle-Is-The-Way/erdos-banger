"""erdos search - search problem statements.

This module is a thin CLI adapter that parses Typer flags and delegates
to the core search service (erdos.core.search.service).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
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
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


app = typer.Typer(
    help="Search problem statements.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


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
    semantic: bool, hybrid: bool, bm25_only: bool, alpha: float | None
) -> CLIOutput | None:
    """Validate mutually exclusive mode flags.

    Returns CLIOutput error if validation fails, None if valid.
    """
    mode_flags = [semantic, hybrid, bm25_only]
    if sum(mode_flags) > 1:
        return CLIOutput.err(
            command="erdos search",
            error_type="UsageError",
            message="Flags --semantic, --hybrid, and --bm25-only are mutually exclusive",
            code=ExitCode.USAGE_ERROR,
        )
    if alpha is not None and not hybrid:
        return CLIOutput.err(
            command="erdos search",
            error_type="UsageError",
            message="--alpha requires --hybrid mode",
            code=ExitCode.USAGE_ERROR,
        )
    return None


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
    error = build_search_index(repo=repo, index=index)
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
        str,
        typer.Argument(help="Search query (supports FTS5 syntax when index exists)"),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum results to return"),
    ] = 10,
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

    Example: erdos search "prime"
    Example: erdos search "prime gaps" --semantic
    Example: erdos search "consecutive primes" --hybrid --alpha 0.6
    """
    json_mode = bool((ctx.obj or {}).get("json"))
    progress_console = err_console if json_mode else console

    result: CLIOutput | None = None

    with measure_time_ms() as duration:
        effective_alpha = 0.5 if alpha is None else alpha
        # Validate mode flags
        result = _validate_mode_flags(semantic, hybrid, bm25_only, alpha)

        if result is None:
            app_ctx, app_error = get_app_context(ctx, command="erdos search")
            if app_error is not None or app_ctx is None:
                result = app_error
            else:
                # Best-effort index: if it can't be opened, fall back to basic search
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
        exit_with_result(ctx, result, print_human=_print_human)
