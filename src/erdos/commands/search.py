"""erdos search - search problem statements."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.exit_codes import ExitCode
from erdos.core.index_builder import build_index as do_build_index
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search_index import SearchIndex, SearchIndexError
from erdos.core.timing import measure_time_ms


# NOTE: SearchIndex imported for isinstance checks in embedding functions


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from erdos.core.embeddings import EmbeddingModel
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol
    from erdos.core.problem_loader import ProblemLoader


class SearchMode(str, Enum):
    """Search mode selection."""

    BM25 = "bm25"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class SearchOptions:
    """Options for the search command."""

    query: str
    limit: int
    problem_id: int | None
    build_index: bool
    build_embeddings: bool = False
    mode: SearchMode = SearchMode.BM25
    alpha: float = 0.5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


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


def search_problems_fts(
    query: str,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository | None = None,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput | None:
    """Search using FTS5 index (preferred).

    Returns None if index is empty (caller should fall back to basic search).
    """
    try:
        # Guard against empty query (consistent with basic search)
        if not query.strip():
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        # Check if index has data - return None to signal caller should fallback
        if index.problem_count() == 0:
            return None

        results = index.search(query, limit=limit, problem_id=problem_id)

        enriched_results = []
        for r in results:
            problem = None
            if repo is not None and r.problem_id is not None:
                try:
                    problem = repo.get_by_id(r.problem_id)
                except Exception:
                    logger.debug(
                        "Failed to enrich result for problem %s",
                        r.problem_id,
                        exc_info=True,
                    )
                    problem = None
            enriched_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "snippet": r.snippet,
                    "score": r.score,
                    "source_type": r.source_type.value,
                    "problem_id": r.problem_id,
                    "title": problem.title if problem else None,
                    "reference_doi": r.reference_doi,
                }
            )

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(enriched_results),
                "results": enriched_results,
                "use_fts": True,
            },
        )

    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in FTS search")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def search_problems_basic(
    query: str,
    repo: ProblemRepository,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput:
    """Fallback: basic substring search (no ranking)."""
    try:
        q = query.lower().strip()
        if not q:
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        # If problem_id specified, search only that problem
        if problem_id is not None:
            problem = repo.get_by_id(problem_id)
            if problem is None:
                return CLIOutput.err(
                    command="erdos search",
                    error_type="NotFound",
                    message=f"Problem {problem_id} not found",
                    code=ExitCode.NOT_FOUND,
                )
            candidates = [problem]
        else:
            candidates = repo.load_all()

        matches: list[ProblemRecord] = []
        for problem in candidates:
            if q in problem.title.lower() or q in problem.statement.lower():
                matches.append(problem)

        matches = sorted(matches, key=lambda p: p.id)[:limit]

        results = [
            {
                "problem_id": p.id,
                "title": p.title,
                "snippet": p.statement[:PREVIEW_LENGTH] + "..."
                if len(p.statement) > PREVIEW_LENGTH
                else p.statement,
                "score": None,
                "source_type": "problem_statement",
            }
            for p in matches
        ]

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(results),
                "results": results,
                "use_fts": False,
            },
        )
    except Exception as e:
        logger.exception("Unexpected error in search command")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


# Keep for backward compatibility
def search_problems(query: str, loader: ProblemLoader) -> CLIOutput:
    """Legacy search function (for backward compatibility)."""
    return search_problems_basic(query, loader)


def _build_index_if_requested(
    build_index: bool,
    progress_console: Console,
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
) -> CLIOutput | None:
    """Build index if requested, returning error or None on success."""
    if not build_index:
        return None
    progress_console.print("Building search index...")
    try:
        stats = do_build_index(loader=repo, index=index, rebuild=True)
        progress_console.print(
            f"[green]✓[/green] Indexed {stats['problems_indexed']} problems"
        )
        return None
    except (ProblemLoaderError, SearchIndexError) as e:
        error_type = (
            "LoaderError" if isinstance(e, ProblemLoaderError) else "IndexError"
        )
        return CLIOutput.err(
            command="erdos search",
            error_type=error_type,
            message=str(e),
            code=ExitCode.ERROR,
        )


def _search_with_fallback(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol | None,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute FTS search with fallback to basic substring search."""
    if index is None:
        result = search_problems_basic(
            options.query, repo, options.limit, options.problem_id
        )
        # Update mode for display
        if result.success and result.data:
            result.data["mode"] = "basic"
        return result

    fts_result = search_problems_fts(
        options.query,
        index=index,
        repo=repo,
        limit=options.limit,
        problem_id=options.problem_id,
    )

    # None means index is empty - fall back to basic search
    if fts_result is None:
        result = search_problems_basic(
            options.query, repo, options.limit, options.problem_id
        )
        if result.success and result.data:
            result.data["mode"] = "basic"
            result.data["fallback_reason"] = "index_empty"
        return result

    # Update mode for display
    if fts_result.success and fts_result.data:
        fts_result.data["mode"] = "bm25"

    return fts_result


def _get_embedding_model(
    model_name: str,
) -> tuple[EmbeddingModel | None, CLIOutput | None]:
    """Load embedding model, returning error if unavailable."""
    # Local import to avoid import errors when embeddings deps not installed
    from erdos.core.embeddings import (  # noqa: PLC0415
        EMBEDDING_AVAILABLE,
        EmbeddingConfig,
        EmbeddingModel,
        EmbeddingNotAvailableError,
    )

    if not EMBEDDING_AVAILABLE:
        return None, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message=(
                "Embedding functionality requires the 'embeddings' extra. "
                "Install with: uv sync --extra embeddings"
            ),
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        # Determine expected dimension based on model
        dim = 384 if "MiniLM" in model_name else 768
        config = EmbeddingConfig(model_name=model_name, dimension=dim)
        model = EmbeddingModel(config)
        return model, None
    except EmbeddingNotAvailableError as e:
        return None, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message=str(e),
            code=ExitCode.CONFIG_ERROR,
        )
    except ValueError as e:
        return None, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message=str(e),
            code=ExitCode.CONFIG_ERROR,
        )


def _build_embeddings_if_requested(
    build_embeddings: bool,
    progress_console: Console,
    *,
    index: SearchIndexProtocol,
    model_name: str,
) -> CLIOutput | None:
    """Build embeddings if requested, returning error or None on success."""
    if not build_embeddings:
        return None

    embedder, err = _get_embedding_model(model_name)
    if err:
        return err
    if embedder is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    progress_console.print(f"Building embeddings with model: {model_name}...")
    try:
        if isinstance(index, SearchIndex):
            count = index.build_embeddings(embedder)
            progress_console.print(f"[green]✓[/green] Embedded {count} chunks")
        else:
            return CLIOutput.err(
                command="erdos search",
                error_type="ConfigError",
                message="Embedding build requires SearchIndex instance",
                code=ExitCode.CONFIG_ERROR,
            )
        return None
    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )


def _search_semantic(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute semantic search."""
    if not isinstance(index, SearchIndex):
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Semantic search requires SearchIndex instance",
            code=ExitCode.CONFIG_ERROR,
        )

    embedder, err = _get_embedding_model(options.embedding_model)
    if err:
        return err
    if embedder is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        results = index.search_semantic(
            options.query,
            embedder,
            limit=options.limit,
            problem_id=options.problem_id,
        )

        # Enrich results with problem titles
        enriched_results = []
        for r in results:
            problem = None
            if r.problem_id is not None:
                with contextlib.suppress(Exception):
                    problem = repo.get_by_id(r.problem_id)
            enriched_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "snippet": r.snippet,
                    "semantic_score": r.semantic_score,
                    "source_type": r.source_type.value,
                    "problem_id": r.problem_id,
                    "title": problem.title if problem else None,
                    "reference_doi": r.reference_doi,
                }
            )

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": options.query,
                "mode": "semantic",
                "count": len(enriched_results),
                "results": enriched_results,
                "embedding_model": options.embedding_model,
            },
        )
    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )


def _search_hybrid(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute hybrid BM25 + semantic search."""
    if not isinstance(index, SearchIndex):
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Hybrid search requires SearchIndex instance",
            code=ExitCode.CONFIG_ERROR,
        )

    embedder, err = _get_embedding_model(options.embedding_model)
    if err:
        return err
    if embedder is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        results = index.search_hybrid(
            options.query,
            embedder,
            limit=options.limit,
            alpha=options.alpha,
            problem_id=options.problem_id,
        )

        # Enrich results with problem titles
        enriched_results = []
        for r in results:
            problem = None
            if r.problem_id is not None:
                with contextlib.suppress(Exception):
                    problem = repo.get_by_id(r.problem_id)
            enriched_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "snippet": r.snippet,
                    "score": r.bm25_score,
                    "semantic_score": r.semantic_score,
                    "hybrid_score": r.hybrid_score,
                    "source_type": r.source_type.value,
                    "problem_id": r.problem_id,
                    "title": problem.title if problem else None,
                    "reference_doi": r.reference_doi,
                }
            )

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": options.query,
                "mode": "hybrid",
                "alpha": options.alpha,
                "count": len(enriched_results),
                "results": enriched_results,
                "embedding_model": options.embedding_model,
            },
        )
    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )


@app.callback(invoke_without_command=True)
def search(  # noqa: PLR0912, PLR0915
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
    build_index: Annotated[
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
        float,
        typer.Option(
            "--alpha",
            help="Hybrid weight (0.0=BM25 only, 1.0=semantic only, default: 0.5)",
            min=0.0,
            max=1.0,
        ),
    ] = 0.5,
    build_embeddings: Annotated[
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

    # Store result to assign duration after context manager exits
    result: CLIOutput | None = None

    with measure_time_ms() as duration:
        # Validate mutually exclusive mode flags
        mode_flags = [semantic, hybrid, bm25_only]
        if sum(mode_flags) > 1:
            result = CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Flags --semantic, --hybrid, and --bm25-only are mutually exclusive",
                code=ExitCode.USAGE_ERROR,
            )
        elif alpha != 0.5 and not hybrid:
            # --alpha only valid with --hybrid
            result = CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="--alpha requires --hybrid mode",
                code=ExitCode.USAGE_ERROR,
            )

        if result is None:
            app_ctx, app_error = get_app_context(ctx, command="erdos search")
            if app_error is not None or app_ctx is None:
                result = app_error
            else:
                # Best-effort index: if it can't be opened, fall back to basic search.
                index: SearchIndexProtocol | None
                try:
                    index = app_ctx.ensure_index()
                except SearchIndexError:
                    index = None

                # Build index if requested
                if build_index:
                    if index is None:
                        result = CLIOutput.err(
                            command="erdos search",
                            error_type="IndexError",
                            message="Search index is unavailable in this environment",
                            code=ExitCode.ERROR,
                        )
                    elif build_error := _build_index_if_requested(
                        build_index,
                        progress_console,
                        repo=app_ctx.problems,
                        index=index,
                    ):
                        result = build_error

                # Build embeddings if requested
                if result is None and build_embeddings:
                    if index is None:
                        result = CLIOutput.err(
                            command="erdos search",
                            error_type="IndexError",
                            message="Search index is unavailable",
                            code=ExitCode.ERROR,
                        )
                    elif embed_error := _build_embeddings_if_requested(
                        build_embeddings,
                        progress_console,
                        index=index,
                        model_name=embedding_model,
                    ):
                        result = embed_error

                # Determine search mode
                mode = SearchMode.BM25
                if semantic:
                    mode = SearchMode.SEMANTIC
                elif hybrid:
                    mode = SearchMode.HYBRID
                # bm25_only keeps the default

                # Perform the search
                if result is None:
                    options = SearchOptions(
                        query=query,
                        limit=limit,
                        problem_id=problem_filter,
                        build_index=build_index,
                        build_embeddings=build_embeddings,
                        mode=mode,
                        alpha=alpha,
                        embedding_model=embedding_model,
                    )

                    if mode == SearchMode.SEMANTIC:
                        if index is None:
                            result = CLIOutput.err(
                                command="erdos search",
                                error_type="IndexError",
                                message="Search index is unavailable",
                                code=ExitCode.ERROR,
                            )
                        else:
                            result = _search_semantic(
                                options, index=index, repo=app_ctx.problems
                            )
                    elif mode == SearchMode.HYBRID:
                        if index is None:
                            result = CLIOutput.err(
                                command="erdos search",
                                error_type="IndexError",
                                message="Search index is unavailable",
                                code=ExitCode.ERROR,
                            )
                        else:
                            result = _search_hybrid(
                                options, index=index, repo=app_ctx.problems
                            )
                    else:
                        # BM25 search (default)
                        result = _search_with_fallback(
                            options, index=index, repo=app_ctx.problems
                        )

    # Duration is now set correctly after context manager exits.
    # Result is guaranteed to be set by one of the branches above.
    if result is not None:
        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=_print_human)
