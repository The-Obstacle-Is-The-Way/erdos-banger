"""Prompt construction for RAG Q&A."""

from erdos.core.models import ProblemRecord
from erdos.core.search.types import SearchResult


def build_prompt(
    problem: ProblemRecord,
    sources: list[SearchResult],
    question: str,
) -> str:
    """
    Build a deterministic RAG prompt.

    Args:
        problem: The problem record
        sources: Retrieved text chunks (ordered by relevance)
        question: User's question

    Returns:
        Formatted prompt string
    """
    # Build prompt sections
    sections = []

    # Header
    sections.append("You are assisting with research on a specific Erdős problem.")
    sections.append("")

    # Problem metadata
    sections.append("Problem:")
    sections.append(f"- id: {problem.id}")
    sections.append(f"- title: {problem.title}")
    sections.append("")

    # Statement
    sections.append("Statement:")
    sections.append(problem.statement)
    sections.append("")

    # Notes section
    sections.append("Notes:")
    if problem.notes:
        sections.append(problem.notes)
    else:
        sections.append("(none)")
    sections.append("")

    # Sources
    sections.append("Sources (cite as [n]):")
    if sources:
        for idx, source in enumerate(sources, start=1):
            sections.append(f"[{idx}] ({source.source_type.value}) {source.chunk_id}")
            sections.append(source.text)
            sections.append("")
    else:
        sections.append("(no sources retrieved)")
        sections.append("")

    # Question
    sections.append("Question:")
    sections.append(question)
    sections.append("")

    # Instructions
    sections.append("Instructions:")
    sections.append("- Answer using only the sources above.")
    sections.append(
        "- When making a claim, cite the supporting source like [1] or [2]."
    )
    sections.append(
        "- If the sources are insufficient, say so explicitly and suggest what to ingest/search next."
    )

    return "\n".join(sections)
