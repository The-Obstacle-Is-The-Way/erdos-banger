"""erdos ingest - fetch and cache reference metadata/content (SPEC-010-E, SPEC-015).

This module is a thin CLI adapter that:
1. Parses CLI flags into IngestOptions
2. Delegates to core/ingest/app.py for orchestration
3. Renders output via presenter.exit_with_result()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.constants import API_RATE_LIMIT_DELAY
from erdos.core.ingest import (
    IngestOptions,
    MetadataSource,
    execute_ingest,
)
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from collections.abc import Callable

    from erdos.core.batch import BatchProgress


app = typer.Typer(
    help="Ingest literature metadata and cache.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print ingestion results."""
    if "batch_id" in result_data:
        _print_human_batch(result_data)
        return

    problem_id = result_data.get("problem_id", "?")
    manifest_path = result_data.get("manifest_path", "?")
    total = result_data.get("references_total", 0)
    written = result_data.get("entries_written", 0)
    skipped = result_data.get("skipped", 0)

    console.print(
        f"\n[bold green]✓[/bold green] Ingestion complete for Problem {problem_id}"
    )
    console.print(f"  Manifest: {manifest_path}")
    console.print(f"  References processed: {total}")
    console.print(f"  Entries written: {written}")
    if skipped > 0:
        console.print(f"  Skipped: {skipped}")

    manifest = result_data.get("manifest", {})
    entries = manifest.get("entries", [])
    if entries:
        table = Table(title=f"Ingested References (Problem {problem_id})")
        table.add_column("Title")
        table.add_column("Source")
        table.add_column("DOI")
        table.add_column("arXiv")

        for entry in entries[:10]:
            ref = entry.get("reference", {})
            table.add_row(
                str(ref.get("title") or "")[:50],
                str(ref.get("source") or ""),
                str(ref.get("doi") or ""),
                str(ref.get("arxiv_id") or ""),
            )

        console.print(table)

        if len(entries) > 10:
            console.print(f"\n  ... and {len(entries) - 10} more entries")


def _print_human_batch(result_data: dict[str, Any]) -> None:
    """Pretty-print batch ingestion results."""
    batch_id = result_data.get("batch_id", "?")
    total = result_data.get("total", 0)
    completed = result_data.get("completed", 0)
    failed = result_data.get("failed", 0)
    failed_ids = result_data.get("failed_ids", [])
    dry_run = result_data.get("dry_run", False)

    if dry_run:
        console.print(f"\n[yellow]Dry run[/yellow]: Would process {total} problems")
        problem_ids = result_data.get("problem_ids", [])
        if problem_ids:
            console.print(f"  Problem IDs: {problem_ids[:20]}")
            if len(problem_ids) > 20:
                console.print(f"  ... and {len(problem_ids) - 20} more")
        return

    if failed == 0:
        console.print(
            f"\n[bold green]✓[/bold green] Batch {batch_id} completed: "
            f"{completed}/{total} succeeded"
        )
    else:
        console.print(
            f"\n[bold yellow]![/bold yellow] Batch {batch_id} completed: "
            f"{completed}/{total} succeeded, {failed} failed"
        )
        console.print(f"  Failed IDs: {failed_ids}")


def _create_progress_callback(
    json_mode: bool,
) -> tuple[bool, Callable[[BatchProgress], None] | None]:
    """Create progress callback for batch operations.

    Returns:
        Tuple of (is_batch_output_suppressed, callback_or_none).
    """
    if json_mode:
        return (True, None)

    def on_progress(progress: BatchProgress) -> None:
        """Handle progress updates."""
        status_icon = "[green]✓[/green]" if progress.success else "[red]✗[/red]"
        err_console.print(
            f"[{progress.index + 1}/{progress.total}] Problem {progress.problem_id}... "
            f"{status_icon} ({progress.message})"
        )

    return (False, on_progress)


def _show_progress_message(problem_id: int | None, json_output: bool) -> None:
    """Show progress message if not in JSON mode."""
    if not json_output:
        if problem_id is not None:
            err_console.print(
                f"[dim]Ingesting references for Problem {problem_id}...[/dim]"
            )
        else:
            err_console.print("[dim]Starting batch ingest...[/dim]")


@app.callback(invoke_without_command=True)
def ingest(
    ctx: typer.Context,
    problem_id: Annotated[
        int | None,
        typer.Argument(help="Problem ID (omit for batch mode)", min=1),
    ] = None,
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
    no_download: Annotated[bool, typer.Option("--no-download")] = False,
    no_network: Annotated[bool, typer.Option("--no-network")] = False,
    timeout: Annotated[float, typer.Option("--timeout")] = 30.0,
    delay: Annotated[float, typer.Option("--delay")] = API_RATE_LIMIT_DELAY,
    mailto: Annotated[str, typer.Option("--mailto")] = "",
    source: Annotated[
        MetadataSource,
        typer.Option(
            "--source",
            help="Metadata source: openalex (default), arxiv, or crossref",
            case_sensitive=False,
        ),
    ] = MetadataSource.OPENALEX,
    # Batch options
    all_problems: Annotated[
        bool,
        typer.Option("--all", help="Process all problems (batch mode)"),
    ] = False,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by status: open, proved, disproved, partially_solved, unknown",
        ),
    ] = None,
    prize_min: Annotated[
        int | None,
        typer.Option("--prize-min", help="Minimum prize amount"),
    ] = None,
    prize_max: Annotated[
        int | None,
        typer.Option("--prize-max", help="Maximum prize amount"),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by tag (can be repeated)"),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Max problems to process"),
    ] = None,
    skip: Annotated[
        int | None,
        typer.Option("--skip", help="Skip first N problems"),
    ] = None,
    resume: Annotated[
        bool,
        typer.Option("--resume", help="Resume from last incomplete batch"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be processed"),
    ] = False,
    max_concurrent: Annotated[
        int,
        typer.Option("--max-concurrent", help="Max parallel operations (ingest: 1)"),
    ] = 1,
    # PDF options (SPEC-019)
    pdf: Annotated[
        bool,
        typer.Option("--pdf", help="Enable PDF conversion for non-arXiv references"),
    ] = False,
    no_pdf: Annotated[
        bool,
        typer.Option("--no-pdf", help="Skip PDFs entirely (metadata only)"),
    ] = False,
    pdf_converter: Annotated[
        str,
        typer.Option(
            "--pdf-converter", help="PDF converter: marker (default), pdfplumber"
        ),
    ] = "marker",
    use_llm: Annotated[
        bool,
        typer.Option("--use-llm", help="Enable LLM-enhanced PDF extraction"),
    ] = False,
) -> None:
    """Ingest literature metadata and cache for problems.

    Single mode: Pass a PROBLEM_ID to ingest one problem.

    Batch mode: Omit PROBLEM_ID and use --all or filter options (--status, --prize-min,
    --prize-max, --tag) to process multiple problems. Batch state is tracked for
    resumption with --resume.

    Uses OpenAlex as the primary metadata source (271M+ works). Falls back to
    arXiv/Crossref when --source is specified.
    """
    json_mode = bool((ctx.obj or {}).get("json"))

    # Resolve PDF mode (--no-pdf takes precedence over --pdf)
    pdf_enabled = pdf and not no_pdf

    # Build options dataclass
    options = IngestOptions(
        problem_id=problem_id,
        force=force,
        no_download=no_download,
        no_network=no_network,
        timeout=timeout,
        delay=delay,
        mailto=mailto,
        source=source,
        all_problems=all_problems,
        status=status,
        prize_min=prize_min,
        prize_max=prize_max,
        tags=tag,
        limit=limit,
        skip=skip,
        resume=resume,
        dry_run=dry_run,
        max_concurrent=max_concurrent,
        pdf=pdf_enabled,
        pdf_converter=pdf_converter,
        use_llm=use_llm,
    )

    # Get app context
    app_ctx, app_error = get_app_context(ctx, command="erdos ingest")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

    # Show progress message
    _show_progress_message(
        problem_id if not options.all_problems else None,
        json_mode,
    )

    # Create progress callback for batch mode
    _, on_progress = _create_progress_callback(json_mode)

    # Execute orchestration via core service
    with measure_time_ms() as duration:
        result = execute_ingest(
            options,
            repo=app_ctx.problems,
            on_progress=on_progress,
        )

    result.duration_ms = duration[0]

    exit_with_result(ctx, result, print_human=_print_human)
