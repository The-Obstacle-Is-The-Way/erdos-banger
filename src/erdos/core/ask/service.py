"""Ask service: orchestrates RAG Q&A for Erdős problems."""

import os
from typing import Any

from erdos.core.ask.llm import execute_llm_if_enabled
from erdos.core.ask.prompt import build_prompt
from erdos.core.ask.retrieval import retrieve_sources
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.ports import ProblemRepository, SearchIndexProtocol
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search.db import SearchIndexError
from erdos.core.search.index_builder import build_index
from erdos.core.search.types import SearchResult


def _ensure_index_ready(
    *,
    loader: ProblemRepository,
    index: SearchIndexProtocol,
    build_index_flag: bool,
) -> SearchIndexProtocol | CLIOutput:
    """
    Ensure search index is ready (build if requested, then open).

    Args:
        loader: Problem loader for building index
        index: Search index to use (built/rebuilt if requested)
        build_index_flag: Whether to rebuild the index

    Returns:
        SearchIndexProtocol if successful, or CLIOutput error
    """
    # Build/rebuild index if requested
    if build_index_flag:
        try:
            build_index(loader=loader, index=index, rebuild=True)
        except (SearchIndexError, ProblemLoaderError) as e:
            return CLIOutput.err(
                command="erdos ask",
                error_type="ERROR",
                message=f"Failed to build index: {e}",
                code=ExitCode.ERROR,
            )
    return index


def _load_problem(
    problem_id: int, *, repo: ProblemRepository
) -> ProblemRecord | CLIOutput:
    """
    Load problem, handling errors.

    Returns:
        ProblemRecord if successful, or CLIOutput error
    """
    try:
        problem = repo.get_by_id(problem_id)
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    if problem is None:
        return CLIOutput.err(
            command="erdos ask",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    return problem


def _build_response_data(
    *,
    problem_id: int,
    question: str,
    prompt: str,
    sources: list[SearchResult],
    query: str,
    limit: int,
    used_fts: bool,
    llm_result: dict[str, str | int | bool | None],
) -> dict[str, Any]:
    """Build the response data dictionary."""
    return {
        "problem_id": problem_id,
        "question": question,
        "prompt": prompt,
        "answer": llm_result["answer"],
        "sources": [
            {
                "chunk_id": source.chunk_id,
                "rank": idx + 1,
                "source_type": source.source_type.value,
                "problem_id": source.problem_id,
                "reference_doi": source.reference_doi,
                "text": source.text,
            }
            for idx, source in enumerate(sources)
        ],
        "retrieval": {
            "query": query,
            "limit": limit,
            "count": len(sources),
            "used_fts": used_fts,
        },
        "llm": {
            "enabled": llm_result["llm_enabled"],
            "command": llm_result["llm_command"],
            "exit_code": llm_result["llm_exit_code"],
        },
    }


def ask_question(
    problem_id: int,
    question: str,
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
    limit: int = 5,
    build_index_flag: bool = False,
    no_llm: bool = False,
    llm_command: str | None = None,
) -> CLIOutput:
    """
    Ask a question about an Erdős problem using RAG.

    Args:
        problem_id: The problem ID
        question: The user's question
        repo: Problem repository (injected)
        index: Search index (injected)
        limit: Maximum retrieved chunks
        build_index_flag: Whether to rebuild the index before retrieval
        no_llm: If True, skip LLM execution (prompt-only mode)
        llm_command: Override LLM command (default: from ERDOS_LLM_COMMAND env)

    Returns:
        CLIOutput with ask results
    """
    # Load problem
    problem_or_error = _load_problem(problem_id, repo=repo)
    if isinstance(problem_or_error, CLIOutput):
        return problem_or_error
    problem = problem_or_error

    # Ensure index is ready
    index_or_error = _ensure_index_ready(
        loader=repo,
        index=index,
        build_index_flag=build_index_flag,
    )
    if isinstance(index_or_error, CLIOutput):
        return index_or_error

    # Retrieve sources
    sources, used_fts, query = retrieve_sources(
        index=index_or_error, problem=problem, question=question, limit=limit
    )

    # Build prompt
    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Determine LLM command
    enable_llm = not no_llm
    effective_llm_cmd = (
        llm_command if llm_command else os.environ.get("ERDOS_LLM_COMMAND", "")
    )

    # Execute LLM if enabled
    llm_result = execute_llm_if_enabled(
        prompt=prompt, enable_llm=enable_llm, llm_command=effective_llm_cmd
    )
    if isinstance(llm_result, CLIOutput):
        return llm_result

    # Build response
    data = _build_response_data(
        problem_id=problem_id,
        question=question,
        prompt=prompt,
        sources=sources,
        query=query or "",
        limit=limit,
        used_fts=used_fts,
        llm_result=llm_result,
    )
    return CLIOutput.ok(command="erdos ask", data=data)
