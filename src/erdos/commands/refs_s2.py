"""Semantic Scholar subcommands for `erdos refs s2` (SPEC-030)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

import requests
import typer

from erdos.commands.presenter import console, exit_with_result
from erdos.core.clients.semantic_scholar import (
    CitationContext,
    S2Config,
    S2Paper,
    S2Reference,
    SemanticScholarClient,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


app = typer.Typer(help="Semantic Scholar citation commands.")


def _get_client() -> SemanticScholarClient:
    """Create S2 client from environment config."""
    config = S2Config.from_env()
    return SemanticScholarClient(config)


def _format_citation_for_json(citation: CitationContext) -> dict[str, Any]:
    """Format citation for JSON output."""
    return {
        "citing_paper": {
            "s2_id": citation.citing_paper_id,
            "title": citation.citing_paper_title,
            "year": citation.citing_paper_year,
        },
        "intents": citation.intents,
        "contexts": citation.contexts,
    }


def _format_reference_for_json(ref: S2Reference) -> dict[str, Any]:
    """Format reference for JSON output."""
    return {
        "s2_id": ref.cited_paper_id,
        "title": ref.cited_paper_title,
        "year": ref.cited_paper_year,
        "intents": ref.intents,
        "contexts": ref.contexts,
    }


def _format_paper_for_json(paper: S2Paper) -> dict[str, Any]:
    """Format paper for JSON output."""
    return {
        "s2_id": paper.s2_id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
    }


def _print_citations_human(data: dict[str, Any]) -> None:
    """Pretty-print citations for human consumption."""
    paper = data.get("paper", {})
    console.print(f"[bold]Paper:[/bold] {paper.get('title', 'Unknown')!r}")

    authors = paper.get("authors", [])
    if authors:
        console.print(f"[bold]Authors:[/bold] {', '.join(authors)}")

    year = paper.get("year")
    if year:
        console.print(f"[bold]Year:[/bold] {year}")

    console.print()

    citations = data.get("citations", [])
    total = data.get("total_citations", len(citations))
    returned = data.get("returned", len(citations))

    console.print(f"[bold]Citing Papers ({returned} of {total}):[/bold]")
    console.print()

    for i, citation in enumerate(citations, 1):
        citing = citation.get("citing_paper", {})
        title = citing.get("title", "Unknown")
        year_str = f" ({citing.get('year')})" if citing.get("year") else ""
        intents = ", ".join(citation.get("intents", [])) or "unclassified"

        console.print(f"  [bold]{i}.[/bold] {title!r}{year_str}")
        console.print(f"     [dim]Intent:[/dim] {intents}")

        contexts = citation.get("contexts", [])
        if contexts:
            # Show first context, truncated
            ctx = contexts[0]
            if len(ctx) > 120:
                ctx = ctx[:117] + "..."
            console.print(f"     [dim]Context:[/dim] {ctx}")
        console.print()


def _print_cited_by_human(data: dict[str, Any]) -> None:
    """Pretty-print cited-by papers for human consumption."""
    paper = data.get("paper", {})
    console.print(f"[bold]Paper:[/bold] {paper.get('title', 'Unknown')!r}")

    authors = paper.get("authors", [])
    if authors:
        console.print(f"[bold]Authors:[/bold] {', '.join(authors)}")

    console.print()

    citing_papers = data.get("citing_papers", [])
    total = data.get("total_citations", len(citing_papers))
    returned = data.get("returned", len(citing_papers))

    console.print(f"[bold]Cited by ({returned} of {total}):[/bold]")
    console.print()

    for i, cp in enumerate(citing_papers, 1):
        title = cp.get("title", "Unknown")
        year_str = f" ({cp.get('year')})" if cp.get("year") else ""
        console.print(f"  [bold]{i}.[/bold] {title!r}{year_str}")


def _print_references_human(data: dict[str, Any]) -> None:
    """Pretty-print references for human consumption."""
    paper = data.get("paper", {})
    console.print(f"[bold]Paper:[/bold] {paper.get('title', 'Unknown')!r}")

    authors = paper.get("authors", [])
    if authors:
        console.print(f"[bold]Authors:[/bold] {', '.join(authors)}")

    console.print()

    references = data.get("references", [])
    console.print(f"[bold]References ({len(references)}):[/bold]")
    console.print()

    for i, ref in enumerate(references, 1):
        title = ref.get("title", "Unknown")
        year_str = f" ({ref.get('year')})" if ref.get("year") else ""
        intents = ", ".join(ref.get("intents", [])) or "unclassified"

        console.print(f"  [bold]{i}.[/bold] {title!r}{year_str}")
        console.print(f"     [dim]Intent:[/dim] {intents}")

        contexts = ref.get("contexts", [])
        if contexts:
            ctx = contexts[0]
            if len(ctx) > 120:
                ctx = ctx[:117] + "..."
            console.print(f"     [dim]Context:[/dim] {ctx}")
        console.print()


@app.command("citations")
def citations(
    ctx: typer.Context,
    identifier: Annotated[
        str,
        typer.Argument(
            help="DOI, arXiv ID, or S2 paper ID.",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum citations to return.", min=1, max=1000),
    ] = 10,
) -> None:
    """Get citation contexts for a paper.

    Returns papers that cite the given paper, with intent classification
    and context snippets showing WHY each paper cites this one.

    Examples:
        erdos refs s2 citations "10.4007/annals.2008.167.481"
        erdos refs s2 citations "math/0404188" --limit 20
    """
    command = "erdos refs s2 citations"

    with measure_time_ms() as duration:
        client = _get_client()

        try:
            # First get the paper to get its S2 ID
            paper = client.get_paper(identifier)
            if paper is None:
                result = CLIOutput.err(
                    command=command,
                    error_type="NotFoundError",
                    message=f"Paper not found: {identifier}",
                    code=ExitCode.NOT_FOUND,
                )
                result.duration_ms = duration[0]
                exit_with_result(ctx, result)
                return

            # Then get citations using the S2 ID
            citations_list = client.get_citations(paper.s2_id, limit=limit)

            output_data: dict[str, Any] = {
                "identifier": identifier,
                "paper": _format_paper_for_json(paper),
                "citations": [_format_citation_for_json(c) for c in citations_list],
                "total_citations": paper.citation_count,
                "returned": len(citations_list),
            }

            result = CLIOutput.ok(command=command, data=output_data)

        except requests.HTTPError as e:
            result = CLIOutput.err(
                command=command,
                error_type="S2Error",
                message=f"Semantic Scholar API error: {e}",
                code=ExitCode.ERROR,
            )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_citations_human)


@app.command("cited-by")
def cited_by(
    ctx: typer.Context,
    identifier: Annotated[
        str,
        typer.Argument(
            help="DOI, arXiv ID, or S2 paper ID.",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit", help="Maximum citing papers to return.", min=1, max=1000
        ),
    ] = 10,
) -> None:
    """List papers that cite the given paper (no context snippets).

    Faster than 'citations' when you just need the list of citing papers.

    Examples:
        erdos refs s2 cited-by "10.4007/annals.2008.167.481"
        erdos refs s2 cited-by "2301.00001" --limit 50
    """
    command = "erdos refs s2 cited-by"

    with measure_time_ms() as duration:
        client = _get_client()

        try:
            paper = client.get_paper(identifier)
            if paper is None:
                result = CLIOutput.err(
                    command=command,
                    error_type="NotFoundError",
                    message=f"Paper not found: {identifier}",
                    code=ExitCode.NOT_FOUND,
                )
                result.duration_ms = duration[0]
                exit_with_result(ctx, result)
                return

            # Get citations (includes citing paper info)
            citations_list = client.get_citations(paper.s2_id, limit=limit)

            # Extract just the citing paper info (no contexts)
            citing_papers = [
                {
                    "s2_id": c.citing_paper_id,
                    "title": c.citing_paper_title,
                    "year": c.citing_paper_year,
                }
                for c in citations_list
            ]

            output_data: dict[str, Any] = {
                "identifier": identifier,
                "paper": _format_paper_for_json(paper),
                "citing_papers": citing_papers,
                "total_citations": paper.citation_count,
                "returned": len(citing_papers),
            }

            result = CLIOutput.ok(command=command, data=output_data)

        except requests.HTTPError as e:
            result = CLIOutput.err(
                command=command,
                error_type="S2Error",
                message=f"Semantic Scholar API error: {e}",
                code=ExitCode.ERROR,
            )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_cited_by_human)


@app.command("references")
def references(
    ctx: typer.Context,
    identifier: Annotated[
        str,
        typer.Argument(
            help="DOI, arXiv ID, or S2 paper ID.",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum references to return.", min=1, max=1000),
    ] = 10,
) -> None:
    """List papers referenced by the given paper (outgoing citations).

    Shows what papers this work cites, with intent and context when available.

    Examples:
        erdos refs s2 references "10.4007/annals.2008.167.481"
        erdos refs s2 references "math/0404188" --limit 25
    """
    command = "erdos refs s2 references"

    with measure_time_ms() as duration:
        client = _get_client()

        try:
            paper = client.get_paper(identifier)
            if paper is None:
                result = CLIOutput.err(
                    command=command,
                    error_type="NotFoundError",
                    message=f"Paper not found: {identifier}",
                    code=ExitCode.NOT_FOUND,
                )
                result.duration_ms = duration[0]
                exit_with_result(ctx, result)
                return

            # Get references
            refs_list = client.get_references(paper.s2_id, limit=limit)

            output_data: dict[str, Any] = {
                "identifier": identifier,
                "paper": _format_paper_for_json(paper),
                "references": [_format_reference_for_json(r) for r in refs_list],
                "returned": len(refs_list),
            }

            result = CLIOutput.ok(command=command, data=output_data)

        except requests.HTTPError as e:
            result = CLIOutput.err(
                command=command,
                error_type="S2Error",
                message=f"Semantic Scholar API error: {e}",
                code=ExitCode.ERROR,
            )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_references_human)
