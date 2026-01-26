"""zbMATH subcommands for `erdos refs zbmath` (SPEC-031)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any


if TYPE_CHECKING:
    from collections.abc import Callable

import requests
import typer

from erdos.commands.presenter import console, exit_with_result
from erdos.core.clients.zbmath import (
    ZbMathClient,
    ZbMathConfig,
    ZbMathEntry,
    zbmath_entry_to_json,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


app = typer.Typer(help="zbMATH Open API commands.")


def _get_client() -> ZbMathClient:
    """Create zbMATH client from environment config."""
    config = ZbMathConfig.from_env()
    return ZbMathClient(config)


def _print_entry_human(data: dict[str, Any]) -> None:
    """Pretty-print a single entry for human consumption."""
    entry = data.get("entry", {})

    console.print(f"[bold]zbMATH Entry:[/bold] Zbl {entry.get('zbl_id', 'Unknown')}")
    console.print()

    console.print(f"[bold]Title:[/bold] {entry.get('title', 'Unknown')}")

    authors = entry.get("authors", [])
    if authors:
        console.print(f"[bold]Authors:[/bold] {'; '.join(authors)}")

    year = entry.get("year")
    if year:
        console.print(f"[bold]Year:[/bold] {year}")

    journal = entry.get("journal")
    if journal:
        console.print(f"[bold]Journal:[/bold] {journal}")

    doi = entry.get("doi")
    if doi:
        console.print(f"[bold]DOI:[/bold] {doi}")

    console.print()

    # MSC Classifications
    msc_list = entry.get("msc", [])
    if msc_list:
        console.print("[bold]MSC Classifications:[/bold]")
        for msc in msc_list:
            prefix = "  - " if not msc.get("primary") else "  - [bold]"
            suffix = "[/bold] (primary)" if msc.get("primary") else ""
            console.print(f"{prefix}{msc.get('code')}: {msc.get('text')}{suffix}")
        console.print()

    # Keywords
    keywords = entry.get("keywords", [])
    if keywords:
        console.print(f"[bold]Keywords:[/bold] {', '.join(keywords)}")
        console.print()

    # Review excerpt
    review = entry.get("review_excerpt")
    if review:
        console.print("[bold]Review (excerpt):[/bold]")
        console.print(f"  {review}")


def _print_entries_human(data: dict[str, Any]) -> None:
    """Pretty-print multiple entries for human consumption."""
    entries = data.get("entries", [])
    query = data.get("query", {})

    # Print query info
    if query.get("msc"):
        console.print(f"[bold]MSC Search:[/bold] {query['msc']}")
    if query.get("year_min") or query.get("year_max"):
        year_range = f"{query.get('year_min', '')}-{query.get('year_max', '')}"
        console.print(f"[bold]Year Range:[/bold] {year_range}")

    console.print(f"[bold]Results:[/bold] {len(entries)}")
    console.print()

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "Unknown")
        authors = "; ".join(entry.get("authors", [])[:3])  # First 3 authors
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


def _lookup_entry(
    client: ZbMathClient,
    identifier: str | None,
    zbl: str | None,
    title: str | None,
) -> ZbMathEntry | None:
    """Look up a single zbMATH entry by various identifiers."""
    if zbl is not None:
        return client.get_by_zbl_id(zbl)
    if title is not None:
        entries = client.search_by_title(title, limit=1)
        return entries[0] if entries else None
    if identifier is not None:
        return client.get_by_doi(identifier)
    return None


def _exit_help_if_no_query(
    ctx: typer.Context,
    *,
    command: str,
    json_mode: bool,
    identifier: str | None,
    zbl: str | None,
    title: str | None,
    msc: str | None,
) -> bool:
    """Exit early when no lookup/search option is provided.

    Returns True when the caller should return (JSON mode). Human mode raises
    `typer.Exit` after printing help.
    """
    if (
        msc is not None
        or zbl is not None
        or title is not None
        or identifier is not None
    ):
        return False

    if json_mode:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command=command,
                error_type="UsageError",
                message=ctx.get_help(),
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return True

    console.print(ctx.get_help())
    raise typer.Exit(code=ExitCode.SUCCESS)


def _run_query(
    client: ZbMathClient,
    *,
    command: str,
    identifier: str | None,
    zbl: str | None,
    title: str | None,
    msc: str | None,
    limit: int,
    year_min: int | None,
    year_max: int | None,
) -> tuple[CLIOutput, Callable[[dict[str, Any]], None]]:
    """Execute the selected zbMATH operation and return output + printer."""
    print_human: Callable[[dict[str, Any]], None] = _print_entry_human
    try:
        if msc is not None:
            entries = client.search_by_msc(
                msc,
                limit=limit,
                year_min=year_min,
                year_max=year_max,
            )
            output_data: dict[str, Any] = {
                "query": {
                    "msc": msc,
                    "limit": limit,
                    "year_min": year_min,
                    "year_max": year_max,
                },
                "entries": [zbmath_entry_to_json(e) for e in entries],
                "returned": len(entries),
            }
            return CLIOutput.ok(command=command, data=output_data), _print_entries_human

        entry = _lookup_entry(client, identifier, zbl, title)
        if entry is None:
            search_term = zbl or title or identifier
            return (
                CLIOutput.err(
                    command=command,
                    error_type="NotFoundError",
                    message=f"Entry not found: {search_term}",
                    code=ExitCode.NOT_FOUND,
                ),
                print_human,
            )

        return (
            CLIOutput.ok(
                command=command,
                data={
                    "identifier": zbl or title or identifier,
                    "entry": zbmath_entry_to_json(entry),
                },
            ),
            print_human,
        )
    except requests.HTTPError as e:
        return (
            CLIOutput.err(
                command=command,
                error_type="ZbMathError",
                message=f"zbMATH API error: {e}",
                code=ExitCode.ERROR,
            ),
            print_human,
        )
    except requests.RequestException as e:
        return (
            CLIOutput.err(
                command=command,
                error_type="ZbMathError",
                message=f"zbMATH request error: {e}",
                code=ExitCode.ERROR,
            ),
            print_human,
        )


@app.callback(invoke_without_command=True)
def zbmath(
    ctx: typer.Context,
    identifier: Annotated[
        str | None,
        typer.Argument(
            help="DOI to look up (e.g., '10.4007/annals.2008.167.481').",
        ),
    ] = None,
    zbl: Annotated[
        str | None,
        typer.Option("--zbl", help="zbMATH ID (e.g., '1191.11025')."),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", help="Title keywords to search."),
    ] = None,
    msc: Annotated[
        str | None,
        typer.Option("--msc", help="MSC code to search (e.g., '11B05')."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="Maximum results for search.",
            min=1,
            max=1000,
        ),
    ] = 20,
    year_min: Annotated[
        int | None,
        typer.Option("--year-min", help="Minimum publication year (requires --msc)."),
    ] = None,
    year_max: Annotated[
        int | None,
        typer.Option("--year-max", help="Maximum publication year (requires --msc)."),
    ] = None,
) -> None:
    """Look up zbMATH entries or search by MSC code.

    Provides access to math-specific metadata from zbMATH Open API,
    including MSC codes, expert reviews, and math-specific keywords.

    Examples:
        erdos refs zbmath "10.4007/annals.2008.167.481"   # By DOI
        erdos refs zbmath --zbl "1191.11025"               # By zbMATH ID
        erdos refs zbmath --title "primes progressions"   # By title
        erdos refs zbmath --msc "11B05"                   # By MSC code
        erdos refs zbmath --msc "11B05" --year-min 2000   # With year filter
    """
    command = "erdos refs zbmath"
    obj = ctx.obj
    json_mode = bool(obj.get("json", False)) if isinstance(obj, dict) else False

    if _exit_help_if_no_query(
        ctx,
        command=command,
        json_mode=json_mode,
        identifier=identifier,
        zbl=zbl,
        title=title,
        msc=msc,
    ):
        return

    if msc is None and (year_min is not None or year_max is not None):
        exit_with_result(
            ctx,
            CLIOutput.err(
                command=command,
                error_type="UsageError",
                message="--year-min/--year-max require --msc",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return

    if year_min is not None and year_max is not None and year_min > year_max:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command=command,
                error_type="UsageError",
                message="--year-min must be <= --year-max",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return

    with measure_time_ms() as duration:
        client = _get_client()
        result, print_human = _run_query(
            client,
            command=command,
            identifier=identifier,
            zbl=zbl,
            title=title,
            msc=msc,
            limit=limit,
            year_min=year_min,
            year_max=year_max,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=print_human)
