"""MCP Server for erdos-banger.

Exposes erdos-banger functionality via Model Context Protocol (MCP)
for AI assistant integration.

Launch:
    erdos-mcp
    # or
    python -m erdos.mcp.server
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from erdos.commands.list_cmd import ListOptions, _execute_list_query
from erdos.commands.refs import get_refs
from erdos.commands.show import get_problem as show_get_problem
from erdos.core.ask import ask_question as core_ask_question
from erdos.core.exit_codes import ExitCode
from erdos.core.formalizer import FormalizerError, generate_skeleton
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoader
from erdos.core.run_logger import RunLogger
from erdos.core.search import search_basic, search_fts
from erdos.core.search.facade import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import (
        ProblemRepository,
        SearchIndexProtocol,
        SearchIndexReadPort,
    )


# Initialize the FastMCP server
mcp = FastMCP("erdos-banger")


# Default project path for Lean operations
DEFAULT_LEAN_PROJECT_PATH = Path("formal/lean")


def _get_repo() -> ProblemRepository:
    """Get the problem repository from environment or default."""
    return ProblemLoader.from_default()


def _get_index() -> SearchIndexProtocol | None:
    """Get the search index if available."""
    index_path_env = os.environ.get("ERDOS_INDEX_PATH")
    if index_path_env:
        return SearchIndex(Path(index_path_env))
    # Try default location (aligned with SearchIndex.from_default())
    default_path = Path("index/erdos.sqlite")
    if default_path.exists():
        return SearchIndex(default_path)
    return None


def _cli_output_to_dict(output: CLIOutput) -> dict[str, Any]:
    """Convert CLIOutput to dict for JSON serialization."""
    return output.model_dump(mode="json")


def _is_path_traversal(file_path: str, base_path: Path) -> bool:
    """Check if a file path attempts directory traversal."""
    # Resolve both paths to catch ../ patterns
    try:
        resolved = (base_path / file_path).resolve()
        base_resolved = base_path.resolve()
        return not str(resolved).startswith(str(base_resolved))
    except (ValueError, OSError):
        return True


# ============================================================================
# Core MCP Tool Functions (for unit testing)
# These functions take explicit dependencies for testability
# ============================================================================


def mcp_get_problem(problem_id: int, *, repo: ProblemRepository) -> dict[str, Any]:
    """Get details for a specific Erdős problem.

    Args:
        problem_id: Erdős problem ID
        repo: Problem repository

    Returns:
        CLIOutput-compatible dict
    """
    result = show_get_problem(problem_id, repo)
    return _cli_output_to_dict(result)


def mcp_list_problems(
    *,
    status: str | None = None,
    prize_min: int | None = None,
    prize_max: int | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
    repo: ProblemRepository,
) -> dict[str, Any]:
    """List problems with optional filters.

    Args:
        status: Filter by status (open, proved, disproved, partially_solved, unknown)
        prize_min: Minimum prize amount
        prize_max: Maximum prize amount
        tags: Filter by tags
        limit: Maximum results to return
        repo: Problem repository

    Returns:
        CLIOutput-compatible dict
    """
    options = ListOptions(
        status=status,
        prize_min=prize_min,
        prize_max=prize_max,
        tags=tags,
        limit=limit,
    )
    result = _execute_list_query(options, repo)
    return _cli_output_to_dict(result)


def mcp_get_references(problem_id: int, *, repo: ProblemRepository) -> dict[str, Any]:
    """Get references for a problem.

    Args:
        problem_id: Erdős problem ID
        repo: Problem repository

    Returns:
        CLIOutput-compatible dict
    """
    result = get_refs(problem_id, repo)
    return _cli_output_to_dict(result)


def mcp_search_index(
    query: str,
    *,
    limit: int = 10,
    problem_id: int | None = None,
    mode: str = "bm25",
    index: SearchIndexReadPort,
    repo: ProblemRepository,
) -> dict[str, Any]:
    """Search the problem/literature index.

    Args:
        query: Search query
        limit: Maximum results to return
        problem_id: Filter to specific problem
        mode: Search mode (bm25, semantic, hybrid) - only bm25 supported via MCP
        index: Search index read port (only read operations needed)
        repo: Problem repository

    Returns:
        CLIOutput-compatible dict
    """
    # Validate query
    if not query.strip():
        error = CLIOutput.err(
            command="search_index",
            error_type="UsageError",
            message="Query must not be empty",
            code=ExitCode.USAGE_ERROR,
        )
        return _cli_output_to_dict(error)

    # Use FTS search
    result = search_fts(
        query,
        index=index,
        repo=repo,
        limit=limit,
        problem_id=problem_id,
    )

    # Fallback to basic search if index is empty (FTS returns None)
    if result is None:
        result = search_basic(query, repo, limit, problem_id)
        if result.success and result.data:
            result.data["mode"] = "basic"
            result.data["fallback_reason"] = "index_empty"
        return _cli_output_to_dict(result)

    # Update mode in response
    if result.success and result.data:
        result.data["mode"] = mode

    return _cli_output_to_dict(result)


def mcp_lean_check(
    file: str,
    *,
    project_path: Path = DEFAULT_LEAN_PROJECT_PATH,
) -> dict[str, Any]:
    """Compile a Lean file and return errors.

    Args:
        file: Lean file path relative to formal/lean/
        project_path: Path to Lean project

    Returns:
        CLIOutput-compatible dict
    """
    # Security: reject path traversal
    if _is_path_traversal(file, project_path):
        error = CLIOutput.err(
            command="lean_check",
            error_type="UsageError",
            message="Path traversal not allowed",
            code=ExitCode.USAGE_ERROR,
        )
        return _cli_output_to_dict(error)

    file_path = project_path / file

    if not file_path.exists():
        error = CLIOutput.err(
            command="lean_check",
            error_type="NotFound",
            message=f"File not found: {file}",
            code=ExitCode.NOT_FOUND,
        )
        return _cli_output_to_dict(error)

    try:
        runner = LeanRunner(project_path)
        result = runner.check(file_path)
        return _cli_output_to_dict(
            CLIOutput.ok(command="lean_check", data=result.model_dump(mode="json"))
        )
    except LeanRunnerError as e:
        error = CLIOutput.err(
            command="lean_check",
            error_type="LeanRunnerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
        return _cli_output_to_dict(error)


def mcp_lean_formalize(
    problem_id: int,
    *,
    force: bool = False,
    project_path: Path = DEFAULT_LEAN_PROJECT_PATH,
    repo: ProblemRepository,
) -> dict[str, Any]:
    """Generate a Lean skeleton for a problem.

    Args:
        problem_id: Erdős problem ID
        force: Overwrite existing file
        project_path: Path to Lean project
        repo: Problem repository

    Returns:
        CLIOutput-compatible dict
    """
    problem = repo.get_by_id(problem_id)
    if problem is None:
        error = CLIOutput.err(
            command="lean_formalize",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )
        return _cli_output_to_dict(error)

    try:
        output_file = generate_skeleton(problem, project_path, overwrite=force)
        result = CLIOutput.ok(
            command="lean_formalize",
            data={"problem_id": problem_id, "file": str(output_file)},
        )
        return _cli_output_to_dict(result)
    except FormalizerError as e:
        error = CLIOutput.err(
            command="lean_formalize",
            error_type="FormalizerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
        return _cli_output_to_dict(error)


def mcp_ask_question(
    problem_id: int,
    question: str,
    *,
    no_llm: bool = True,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
) -> dict[str, Any]:
    """Ask a question about a problem (RAG).

    Args:
        problem_id: Erdős problem ID
        question: Question to ask
        no_llm: If True, return prompt/sources only (default: True for MCP)
        repo: Problem repository
        index: Search index

    Returns:
        CLIOutput-compatible dict
    """
    result = core_ask_question(
        problem_id=problem_id,
        question=question,
        repo=repo,
        index=index,
        limit=5,
        build_index_flag=False,
        no_llm=no_llm,
        llm_command=None,
    )
    return _cli_output_to_dict(result)


def mcp_get_logs(
    *,
    problem_id: int | None = None,
    command: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Query run logs.

    Args:
        problem_id: Filter by problem ID
        command: Filter by command name
        limit: Maximum entries to return

    Returns:
        CLIOutput-compatible dict with log entries
    """
    logger = RunLogger()
    entries = logger.query(
        problem_id=problem_id,
        command=command,
        limit=limit,
    )

    entries_data = [entry.model_dump(mode="json") for entry in entries]
    result = CLIOutput.ok(
        command="get_logs",
        data={"entries": entries_data, "count": len(entries_data)},
    )
    return _cli_output_to_dict(result)


# ============================================================================
# MCP Tool Registrations (these are the actual MCP entry points)
# ============================================================================


@mcp.tool()
def get_problem(problem_id: int) -> str:
    """Get details for a specific Erdős problem.

    Args:
        problem_id: Erdős problem ID

    Returns:
        JSON string with problem details or error
    """
    repo = _get_repo()
    result = mcp_get_problem(problem_id, repo=repo)
    return json.dumps(result)


@mcp.tool()
def list_problems(
    status: str | None = None,
    prize_min: int | None = None,
    prize_max: int | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
) -> str:
    """List problems with optional filters.

    Args:
        status: Filter by status (open, proved, disproved, partially_solved, unknown)
        prize_min: Minimum prize amount
        prize_max: Maximum prize amount
        tags: Filter by tags
        limit: Maximum results to return

    Returns:
        JSON string with problem list or error
    """
    repo = _get_repo()
    result = mcp_list_problems(
        status=status,
        prize_min=prize_min,
        prize_max=prize_max,
        tags=tags,
        limit=limit,
        repo=repo,
    )
    return json.dumps(result)


@mcp.tool()
def get_references(problem_id: int) -> str:
    """Get references for a problem.

    Args:
        problem_id: Erdős problem ID

    Returns:
        JSON string with references or error
    """
    repo = _get_repo()
    result = mcp_get_references(problem_id, repo=repo)
    return json.dumps(result)


@mcp.tool()
def search_index(
    query: str,
    limit: int = 10,
    problem_id: int | None = None,
    mode: str = "bm25",
) -> str:
    """Search the problem/literature index.

    Args:
        query: Search query
        limit: Maximum results to return
        problem_id: Filter to specific problem
        mode: Search mode (bm25, semantic, hybrid) - currently only bm25 is supported

    Returns:
        JSON string with search results or error
    """
    repo = _get_repo()
    index = _get_index()

    if index is None:
        # Fall back to basic search
        basic_result = search_basic(query, repo, limit=limit, problem_id=problem_id)
        if basic_result.success and basic_result.data:
            basic_result.data["mode"] = "basic"
        return json.dumps(_cli_output_to_dict(basic_result))

    result = mcp_search_index(
        query,
        limit=limit,
        problem_id=problem_id,
        mode=mode,
        index=index,
        repo=repo,
    )
    return json.dumps(result)


@mcp.tool()
def lean_check(file: str) -> str:
    """Compile a Lean file and return errors.

    Args:
        file: Lean file path relative to formal/lean/

    Returns:
        JSON string with compilation result or error
    """
    result = mcp_lean_check(file)
    return json.dumps(result)


@mcp.tool()
def lean_formalize(problem_id: int, force: bool = False) -> str:
    """Generate a Lean skeleton for a problem.

    Args:
        problem_id: Erdős problem ID
        force: Overwrite existing file

    Returns:
        JSON string with file path or error
    """
    repo = _get_repo()
    result = mcp_lean_formalize(problem_id, force=force, repo=repo)
    return json.dumps(result)


@mcp.tool()
def ask_question(
    problem_id: int,
    question: str,
    no_llm: bool = True,
) -> str:
    """Ask a question about a problem (RAG).

    Default: returns prompt and sources only (no_llm=True).
    MCP server does not call an LLM by default.

    Args:
        problem_id: Erdős problem ID
        question: Question to ask
        no_llm: If True (default), return prompt/sources only

    Returns:
        JSON string with answer/sources or error
    """
    repo = _get_repo()
    index = _get_index()

    if index is None:
        error = CLIOutput.err(
            command="ask_question",
            error_type="ConfigError",
            message="Search index not available. Build index first with 'erdos search --build-index'",
            code=ExitCode.CONFIG_ERROR,
        )
        return json.dumps(_cli_output_to_dict(error))

    result = mcp_ask_question(
        problem_id,
        question,
        no_llm=no_llm,
        repo=repo,
        index=index,
    )
    return json.dumps(result)


@mcp.tool()
def get_logs(
    problem_id: int | None = None,
    command: str | None = None,
    limit: int = 20,
) -> str:
    """Query run logs.

    Args:
        problem_id: Filter by problem ID
        command: Filter by command name
        limit: Maximum entries to return

    Returns:
        JSON string with log entries or error
    """
    result = mcp_get_logs(
        problem_id=problem_id,
        command=command,
        limit=limit,
    )
    return json.dumps(result)


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
