"""Command-specific result summarizers for run logging.

This module provides a registry of summarizer functions that extract command-specific
summaries from CLIOutput data. The registry pattern enables adding new commands
without modifying the core run_logger module (Open/Closed Principle).

Usage:
    from erdos.core.run_logger_summaries import get_summarizer

    summarizer = get_summarizer("erdos show")
    result = summarizer(cli_output.data)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


# Type alias for summarizer functions: data dict -> summary dict
ResultSummarizer = Callable[[dict[str, Any]], dict[str, Any]]


def _summarize_show(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos show' command result."""
    return {
        "status": data.get("status"),
        "has_prize": bool(data.get("prize", 0)),
    }


def _summarize_search(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos search' command result."""
    results = data.get("results", [])
    return {
        "hit_count": len(results),
        "top_problem_ids": [r.get("id") for r in results[:3] if isinstance(r, dict)],
    }


def _summarize_lean_check(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos lean check' command result."""
    errors = data.get("errors", [])
    return {
        "success": data.get("success", True),
        "error_count": len(errors) if isinstance(errors, list) else 0,
        "has_sorry": data.get("has_sorry", False),
    }


def _summarize_lean_formalize(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos lean formalize' command result."""
    return {"file_created": data.get("file_path")}


def _summarize_ingest(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos ingest' command result."""
    return {
        "references_processed": data.get("references_processed", 0),
        "manifest_path": data.get("manifest_path"),
    }


def _summarize_ask(data: dict[str, Any]) -> dict[str, Any]:
    """Summarize 'erdos ask' command result."""
    sources = data.get("sources", [])
    answer = data.get("answer", "")
    return {
        "sources_retrieved": len(sources) if isinstance(sources, list) else 0,
        "llm_enabled": data.get("llm_enabled", False),
        "answer_length": len(answer) if isinstance(answer, str) else 0,
    }


def _summarize_default(_data: dict[str, Any]) -> dict[str, Any]:
    """Default summarizer for commands without specific handling."""
    return {"success": True}


# Registry mapping command names to their summarizer functions
SUMMARIZERS: dict[str, ResultSummarizer] = {
    "erdos show": _summarize_show,
    "erdos search": _summarize_search,
    "erdos lean check": _summarize_lean_check,
    "erdos lean formalize": _summarize_lean_formalize,
    "erdos ingest": _summarize_ingest,
    "erdos ask": _summarize_ask,
}


def get_summarizer(command: str) -> ResultSummarizer:
    """Get the summarizer function for a command.

    Args:
        command: Command name (e.g., "erdos show", "erdos search")

    Returns:
        Summarizer function for the command, or default summarizer if not registered
    """
    return SUMMARIZERS.get(command, _summarize_default)


def register_summarizer(command: str, summarizer: ResultSummarizer) -> None:
    """Register a custom summarizer for a command.

    This allows external modules to register summarizers for new commands
    without modifying this module.

    Args:
        command: Command name to register
        summarizer: Summarizer function that takes data dict and returns summary dict
    """
    SUMMARIZERS[command] = summarizer
