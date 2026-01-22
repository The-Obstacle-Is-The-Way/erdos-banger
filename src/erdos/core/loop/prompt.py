"""Loop prompt building utilities.

Per spec-012-design.md D2 (Token Budget) and D5 (Prompt Template).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jinja2 import Environment, PackageLoader, select_autoescape


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.loop.config import LoopConfig
    from erdos.core.models import LeanCheckResult, LeanError, ProblemRecord


# Template environment for loop prompts
_env = Environment(
    loader=PackageLoader("erdos", "templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _truncate_bytes(text: str, max_bytes: int) -> str:
    """Truncate text to fit within max_bytes (UTF-8)."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    # Truncate and add ellipsis
    truncated = encoded[: max_bytes - 3]
    # Decode safely (may cut off mid-character)
    return truncated.decode("utf-8", errors="ignore") + "..."


def budget_context(
    *,
    lean_file: str,
    errors_text: str,
    problem_text: str,
    rag_text: str,
    config: LoopConfig,
) -> dict[str, str]:
    """Truncate context components to fit within byte budget.

    Per spec-012-design.md D2: Byte-Based Budget with Hard Caps.

    Priority: lean_file > errors > problem > rag

    Args:
        lean_file: Content of the Lean file
        errors_text: Formatted error messages
        problem_text: Problem statement text
        rag_text: Retrieved context from RAG
        config: Loop configuration with budget limits

    Returns:
        Dictionary with truncated content
    """
    return {
        "lean_file": _truncate_bytes(lean_file, config.max_file_bytes_prompt),
        "errors_text": _truncate_bytes(errors_text, 4096),
        "problem_text": _truncate_bytes(problem_text, 2048),
        "rag_text": _truncate_bytes(rag_text, 8192),
    }


def _format_errors(errors: list[LeanError]) -> str:
    """Format errors for the prompt."""
    lines = []
    for i, error in enumerate(errors, 1):
        lines.append(f"### Error {i} at line {error.line}")
        lines.append(f"```\n{error.message}\n```")
    return "\n".join(lines)


def build_loop_prompt(
    *,
    file_path: Path,
    file_content: str,
    problem: ProblemRecord,
    check_result: LeanCheckResult,
    rag_chunks: list[Any],
    config: LoopConfig,
) -> str:
    """Build the prompt for the LLM.

    Uses the loop_prompt.j2 template for deterministic output.

    Args:
        file_path: Path to the Lean file
        file_content: Content of the Lean file
        problem: Problem record
        check_result: Result of Lean compilation check
        rag_chunks: Retrieved context chunks
        config: Loop configuration

    Returns:
        Formatted prompt string
    """
    # Budget the context
    budgeted = budget_context(
        lean_file=file_content,
        errors_text=_format_errors(check_result.errors),
        problem_text=problem.statement or "",
        rag_text="",  # RAG chunks handled separately
        config=config,
    )

    template = _env.get_template("loop_prompt.j2")
    return template.render(
        file_path=str(file_path),
        file_content=budgeted["lean_file"],
        compilation_success=check_result.success,
        error_count=len(check_result.errors),
        errors=check_result.errors,
        problem=problem,
        rag_chunks=rag_chunks,
    )
