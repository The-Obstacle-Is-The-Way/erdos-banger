"""Unit tests for ask prompt formatting."""

from erdos.core.ask import build_prompt
from erdos.core.models import ChunkSource, ProblemRecord, ProblemStatus
from erdos.core.search.types import SearchResult


def test_prompt_includes_problem_statement():
    """Prompt must include the problem statement."""
    problem = ProblemRecord(
        id=6,
        title="Small primes in arithmetic progressions",
        statement="Let p_1 < p_2 < ... be the sequence of primes. Are there infinitely many n such that p_{n+1} - p_n > p_n - p_{n-1}?",
        status=ProblemStatus.OPEN,
    )
    sources: list[SearchResult] = []
    question = "What is known?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    assert problem.statement in prompt
    assert f"id: {problem.id}" in prompt
    assert f"title: {problem.title}" in prompt


def test_prompt_includes_question():
    """Prompt must include the user question."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    sources: list[SearchResult] = []
    question = "What partial results are known?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    assert question in prompt


def test_prompt_includes_numbered_sources():
    """Sources must be numbered [1], [2], etc."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    sources = [
        SearchResult(
            chunk_id="problem_6_statement",
            text="First source text about primes",
            snippet="...",
            score=10.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        ),
        SearchResult(
            chunk_id="problem_6_notes",
            text="Second source text with more details",
            snippet="...",
            score=8.0,
            source_type=ChunkSource.PROBLEM_NOTES,
            problem_id=6,
            reference_doi=None,
        ),
    ]
    question = "What is known?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Check numbered sources
    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "First source text about primes" in prompt
    assert "Second source text with more details" in prompt
    # Verify they appear in order
    idx_1 = prompt.index("[1]")
    idx_2 = prompt.index("[2]")
    assert idx_1 < idx_2


def test_prompt_includes_source_metadata():
    """Sources must include source_type and chunk_id."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    sources = [
        SearchResult(
            chunk_id="problem_6_statement",
            text="Source text",
            snippet="...",
            score=10.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        ),
    ]
    question = "Test?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    assert "problem_statement" in prompt
    assert "problem_6_statement" in prompt


def test_prompt_includes_notes_when_present():
    """Prompt must include notes section when problem has notes."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
        notes="Important historical context here.",
    )
    sources: list[SearchResult] = []
    question = "Test?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    assert "Notes:" in prompt
    assert "Important historical context here." in prompt


def test_prompt_empty_notes_when_absent():
    """Prompt notes section should be empty when problem has no notes."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
        notes=None,
    )
    sources: list[SearchResult] = []
    question = "Test?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Notes section should exist but be empty or say "(none)"
    assert "Notes:" in prompt


def test_prompt_is_deterministic():
    """Same inputs must produce exact same prompt (for regression testing)."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    sources = [
        SearchResult(
            chunk_id="test_chunk",
            text="Test text",
            snippet="...",
            score=5.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        ),
    ]
    question = "Test?"

    prompt1 = build_prompt(problem=problem, sources=sources, question=question)
    prompt2 = build_prompt(problem=problem, sources=sources, question=question)

    assert prompt1 == prompt2


def test_prompt_empty_sources():
    """Prompt must handle zero sources gracefully."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    sources: list[SearchResult] = []
    question = "Test?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Should still include problem and question, just no sources
    assert problem.statement in prompt
    assert question in prompt
    assert "Sources" in prompt  # Section should exist even if empty


def test_prompt_instructions_for_citation():
    """Prompt must include instructions to cite sources as [n]."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    sources: list[SearchResult] = []
    question = "Test?"

    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Should include citation instructions
    assert "cite" in prompt.lower() or "[n]" in prompt or "[1]" in prompt.lower()
    assert "Instructions:" in prompt or "instructions:" in prompt.lower()
