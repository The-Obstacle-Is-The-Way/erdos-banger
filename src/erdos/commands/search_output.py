"""Human output formatters for `erdos search`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from erdos.commands.presenter import console


PrintHuman = Callable[[dict[str, Any]], None]


def print_msc_human(data: dict[str, Any]) -> None:
    """Pretty-print MSC search results from zbMATH."""
    entries = data.get("entries", [])
    msc_code = data.get("msc", "")
    year_min = data.get("year_min")
    year_max = data.get("year_max")

    console.print(f"[bold]MSC Search:[/bold] {msc_code}")
    if year_min or year_max:
        year_range = f"{year_min or ''}-{year_max or ''}"
        console.print(f"[bold]Year Range:[/bold] {year_range}")
    console.print(f"[bold]Results:[/bold] {len(entries)}")
    console.print()

    if not entries:
        console.print("No entries found.")
        return

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "Unknown")
        authors = "; ".join(entry.get("authors", [])[:3])
        if len(entry.get("authors", [])) > 3:
            authors += " et al."
        year = entry.get("year", "")
        year_str = f" ({year})" if year else ""
        msc_codes = ", ".join(m.get("code", "") for m in entry.get("msc", [])[:3])

        console.print(f"[bold]{i}.[/bold] {title!r}{year_str}")
        if authors:
            console.print(f"    [dim]Authors:[/dim] {authors}")
        if msc_codes:
            console.print(f"    [dim]MSC:[/dim] {msc_codes}")
        console.print()


def print_search_human(result_data: dict[str, Any]) -> None:
    """Pretty-print search results."""
    results = result_data.get("results", [])
    query = result_data.get("query", "")
    mode = result_data.get("mode", "bm25")

    if not results:
        console.print(f"No results for: {query}")
        return

    console.print(f"[bold]Search results for:[/bold] {query}")

    mode_labels = {
        "bm25": "[dim]Using BM25 ranking[/dim]",
        "semantic": "[dim]Using semantic (vector) search[/dim]",
        "hybrid": (
            f"[dim]Using hybrid search (alpha={result_data.get('alpha', 0.5)})[/dim]"
        ),
        "basic": (
            "[dim]Using basic substring search "
            "(run 'erdos search --build-index' for better results)[/dim]"
        ),
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

        scores_parts: list[str] = []
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
