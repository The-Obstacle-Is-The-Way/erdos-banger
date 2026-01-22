"""Search service: orchestrates search operations for Erdős problems.

This module contains the core search logic, separated from CLI concerns.
The CLI adapter (commands/search.py) calls these functions and handles
Typer/Rich presentation.

# exempt: DEBT-062
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search.db import SearchIndexError
from erdos.core.search.facade import SearchIndex
from erdos.core.search.index_builder import build_index


if TYPE_CHECKING:
    from erdos.core.ports import (
        ProblemRepository,
        SearchIndexProtocol,
        SearchIndexReadPort,
    )
    from erdos.core.search.embeddings import EmbeddingModel


logger = logging.getLogger(__name__)


class SearchMode(str, Enum):
    """Search mode selection."""

    BM25 = "bm25"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class SearchOptions:
    """Options for search operations."""

    query: str
    limit: int
    problem_id: int | None
    build_index: bool
    build_embeddings: bool = False
    mode: SearchMode = SearchMode.BM25
    alpha: float = 0.5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


def _enrich_result(
    result: dict[str, object],
    repo: ProblemRepository | None,
    problem_id: int | None,
) -> dict[str, object]:
    """Add problem title to search result if available."""
    if repo is not None and problem_id is not None:
        try:
            problem = repo.get_by_id(problem_id)
            if problem:
                result["title"] = problem.title
        except Exception:
            logger.debug(
                "Failed to enrich result for problem %s",
                problem_id,
                exc_info=True,
            )
    return result


def search_fts(
    query: str,
    *,
    index: SearchIndexReadPort,
    repo: ProblemRepository | None = None,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput | None:
    """Search using FTS5 index (preferred).

    Returns None if index is empty (caller should fall back to basic search).

    Args:
        query: Search query
        index: Search index read port (only read operations needed)
        repo: Optional problem repository for enrichment
        limit: Maximum results
        problem_id: Optional filter to specific problem

    Returns:
        CLIOutput with results, error, or None if index is empty
    """
    try:
        # Guard against empty query
        if not query.strip():
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        # Return None to signal fallback needed if index is empty
        if index.problem_count() == 0:
            return None

        results = index.search(query, limit=limit, problem_id=problem_id)

        enriched_results = []
        for r in results:
            result_dict = {
                "chunk_id": r.chunk_id,
                "snippet": r.snippet,
                "score": r.score,
                "source_type": r.source_type.value,
                "problem_id": r.problem_id,
                "title": None,
                "reference_doi": r.reference_doi,
            }
            _enrich_result(result_dict, repo, r.problem_id)
            enriched_results.append(result_dict)

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


def search_basic(
    query: str,
    repo: ProblemRepository,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput:
    """Fallback: basic substring search (no ranking).

    Args:
        query: Search query
        repo: Problem repository
        limit: Maximum results
        problem_id: Optional filter to specific problem

    Returns:
        CLIOutput with results or error
    """
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
        logger.exception("Unexpected error in basic search")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def search_with_fallback(
    options: SearchOptions,
    *,
    index: SearchIndexReadPort | None,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute FTS search with fallback to basic substring search.

    Args:
        options: Search options
        index: Search index read port (may be None if unavailable)
        repo: Problem repository

    Returns:
        CLIOutput with search results
    """
    if index is None:
        result = search_basic(options.query, repo, options.limit, options.problem_id)
        if result.success and result.data:
            result.data["mode"] = "basic"
        return result

    fts_result = search_fts(
        options.query,
        index=index,
        repo=repo,
        limit=options.limit,
        problem_id=options.problem_id,
    )

    # None means index is empty - fall back to basic search
    if fts_result is None:
        result = search_basic(options.query, repo, options.limit, options.problem_id)
        if result.success and result.data:
            result.data["mode"] = "basic"
            result.data["fallback_reason"] = "index_empty"
        return result

    # Update mode for display
    if fts_result.success and fts_result.data:
        fts_result.data["mode"] = "bm25"

    return fts_result


def get_embedding_model(
    model_name: str,
) -> tuple[EmbeddingModel | None, CLIOutput | None]:
    """Load embedding model, returning error if unavailable.

    Args:
        model_name: Name of the embedding model to load

    Returns:
        Tuple of (model, error) - one will be None
    """
    # Local import to avoid import errors when embeddings deps not installed
    from erdos.core.search.embeddings import (  # noqa: PLC0415
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


def build_search_index(
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
) -> CLIOutput | None:
    """Build the search index.

    Args:
        repo: Problem repository
        index: Search index

    Returns:
        None on success, CLIOutput error on failure
    """
    try:
        build_index(loader=repo, index=index, rebuild=True)
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


def build_embeddings(
    *,
    index: SearchIndexProtocol,
    model_name: str,
) -> tuple[int, CLIOutput | None]:
    """Build embeddings for indexed chunks.

    Args:
        index: Search index (must be SearchIndex instance)
        model_name: Embedding model name

    Returns:
        Tuple of (count, error) - count is 0 if error occurred
    """
    embedder, err = get_embedding_model(model_name)
    if err:
        return 0, err
    if embedder is None:
        return 0, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        if isinstance(index, SearchIndex):
            count = index.build_embeddings(embedder)
            return count, None
        else:
            return 0, CLIOutput.err(
                command="erdos search",
                error_type="ConfigError",
                message="Embedding build requires SearchIndex instance",
                code=ExitCode.CONFIG_ERROR,
            )
    except SearchIndexError as e:
        return 0, CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )


def search_semantic(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute semantic search.

    Args:
        options: Search options
        index: Search index
        repo: Problem repository for enrichment

    Returns:
        CLIOutput with semantic search results
    """
    if not isinstance(index, SearchIndex):
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Semantic search requires SearchIndex instance",
            code=ExitCode.CONFIG_ERROR,
        )

    embedder, err = get_embedding_model(options.embedding_model)
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


def search_hybrid(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute hybrid BM25 + semantic search.

    Args:
        options: Search options (uses alpha for weighting)
        index: Search index
        repo: Problem repository for enrichment

    Returns:
        CLIOutput with hybrid search results
    """
    if not isinstance(index, SearchIndex):
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Hybrid search requires SearchIndex instance",
            code=ExitCode.CONFIG_ERROR,
        )

    embedder, err = get_embedding_model(options.embedding_model)
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


def execute_search(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol | None,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute search based on mode.

    This is the main entry point for search operations.

    Args:
        options: Search options including mode
        index: Search index (may be None)
        repo: Problem repository

    Returns:
        CLIOutput with search results
    """
    if options.mode == SearchMode.SEMANTIC:
        if index is None:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexError",
                message="Search index is unavailable",
                code=ExitCode.ERROR,
            )
        return search_semantic(options, index=index, repo=repo)

    if options.mode == SearchMode.HYBRID:
        if index is None:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexError",
                message="Search index is unavailable",
                code=ExitCode.ERROR,
            )
        return search_hybrid(options, index=index, repo=repo)

    # BM25 search (default) with fallback
    return search_with_fallback(options, index=index, repo=repo)
