"""erdos search - search problem statements."""

from __future__ import annotations

from typing import Annotated

import typer

from erdos.commands.presenter import exit_with_result
from erdos.commands.search_impl import execute_search_command
from erdos.core.constants import DEFAULT_SEARCH_LIMIT
from erdos.core.timing import measure_time_ms


app = typer.Typer(
    help="Search problem statements.",
    context_settings={"allow_interspersed_args": True},
)


QUERY_HELP = (
    "Search query (supports FTS5 syntax when index exists). "
    "Not required when using --msc."
)
MSC_HELP = "Search zbMATH by MSC code (e.g., '11B05'). Incompatible with other modes."


@app.callback(invoke_without_command=True)
def search(
    ctx: typer.Context,
    query: Annotated[str | None, typer.Argument(help=QUERY_HELP)] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-n", help="Maximum results to return", min=1, max=1000
        ),
    ] = DEFAULT_SEARCH_LIMIT,
    problem_filter: Annotated[
        int | None,
        typer.Option("--problem", "-p", help="Filter to a specific problem ID"),
    ] = None,
    build_index_flag: Annotated[
        bool, typer.Option("--build-index", help="Build/rebuild the search index")
    ] = False,
    semantic: Annotated[
        bool,
        typer.Option("--semantic", "-s", help="Use semantic (vector) search"),
    ] = False,
    hybrid: Annotated[bool, typer.Option("--hybrid", help="Hybrid search")] = False,
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
        typer.Option("--build-embeddings", help="Build/rebuild semantic embeddings"),
    ] = False,
    embedding_model: Annotated[
        str,
        typer.Option("--embedding-model", help="Embedding model name"),
    ] = "sentence-transformers/all-MiniLM-L6-v2",
    msc: Annotated[str | None, typer.Option("--msc", help=MSC_HELP)] = None,
    year_min: Annotated[
        int | None,
        typer.Option("--year-min", help="Minimum publication year (for --msc mode)"),
    ] = None,
    year_max: Annotated[
        int | None,
        typer.Option("--year-max", help="Maximum publication year (for --msc mode)"),
    ] = None,
) -> None:
    """Search problem statements (or zbMATH via `--msc`)."""
    with measure_time_ms() as duration:
        result, printer = execute_search_command(
            ctx,
            query=query,
            limit=limit,
            problem_filter=problem_filter,
            build_index_flag=build_index_flag,
            semantic=semantic,
            hybrid=hybrid,
            bm25_only=bm25_only,
            alpha=alpha,
            build_embeddings_flag=build_embeddings_flag,
            embedding_model=embedding_model,
            msc=msc,
            year_min=year_min,
            year_max=year_max,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=printer)
