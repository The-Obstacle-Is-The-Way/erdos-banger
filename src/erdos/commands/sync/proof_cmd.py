"""erdos sync proof - extract proof links from forum threads (SPEC-035)."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.panel import Panel
from rich.table import Table

from erdos.commands.presenter import console, exit_with_result
from erdos.core.sync.proof_service import sync_proof_links
from erdos.core.timing import measure_time_ms


# =============================================================================
# Security warning for --verify
# =============================================================================

VERIFY_WARNING = """
⚠️  SECURITY WARNING ⚠️

The --verify flag will:
  • Clone an external repository
  • Execute `lake build` (runs untrusted build tooling)

This runs third-party code on your machine. Proceed with caution.

Guardrails applied:
  ✓ Runs in temporary directory
  ✓ API keys stripped from environment
  ✓ No git hooks executed
  ✓ Logs truncated to prevent overflow
"""


def _print_verify_warning() -> None:
    """Print security warning before verification."""
    console.print(
        Panel(VERIFY_WARNING.strip(), title="Verification Warning", style="yellow")
    )


# =============================================================================
# Human output
# =============================================================================


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print sync result for humans."""
    problem_id = data.get("problem_id", "?")
    links = data.get("links", [])
    links_count = data.get("links_count", 0)
    cached = data.get("cached", False)
    provenance_path = data.get("provenance_path", "")
    verification_status = data.get("verification_status", "unverified")
    verification_error = data.get("verification_error")
    verified_repo = data.get("verified_repo")
    verified_files = data.get("verified_files", [])
    toolchain = data.get("toolchain")

    source_text = "(from cache)" if cached else "(from network)"

    if links_count == 0:
        content = f"No proof repository links found {source_text}"
        panel = Panel(
            content,
            title=f"Problem #{problem_id} - Proof Links",
            expand=False,
        )
        console.print(panel)
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("URL", style="cyan")
    table.add_column("Author", style="green")
    table.add_column("Lean Version", style="yellow")

    for link in links:
        table.add_row(
            link.get("url", "?"),
            link.get("author") or "-",
            link.get("lean_version_hint") or "-",
        )

    status_style = {
        "verified": "green",
        "inconclusive": "yellow",
        "failed": "red",
        "source_unavailable": "red",
        "unverified": "dim",
    }.get(verification_status, "dim")

    lines = [
        f"[bold]Problem #{problem_id}[/bold] {source_text}",
        f"Found {links_count} proof link(s)",
        f"Verification: [{status_style}]{verification_status}[/{status_style}]",
    ]

    if verification_error:
        lines.append(f"  Error: {verification_error}")
    if verified_repo:
        lines.append(f"  Repo: {verified_repo}")
    if toolchain:
        lines.append(f"  Toolchain: {toolchain}")
    if verified_files:
        lines.append(f"  Verified files: {', '.join(verified_files)}")

    lines.append(f"Saved to: {provenance_path}")

    if verification_status == "verified":
        title = "✓ Proof Verified"
        style: str = "green"
    elif verification_status == "inconclusive":
        title = "~ Proof Inconclusive"
        style = "yellow"
    elif verification_status in ("failed", "source_unavailable"):
        title = "✗ Verification Failed"
        style = "red"
    else:
        title = "✓ Proof Links Extracted"
        style = "default"

    panel = Panel(
        "\n".join(lines),
        title=title,
        expand=False,
        border_style=style,
    )
    console.print(panel)
    console.print(table)


# =============================================================================
# CLI Command
# =============================================================================


def proof(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(help="Problem ID to extract proof links for", min=1),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be extracted without writing"),
    ] = False,
    verify: Annotated[
        bool,
        typer.Option(
            "--verify",
            help="Clone and verify proofs (runs untrusted build tooling)",
        ),
    ] = False,
) -> None:
    """Extract proof repository links from the forum thread (optionally verify)."""
    json_mode = bool((ctx.obj or {}).get("json"))
    if verify and not json_mode:
        _print_verify_warning()

    with measure_time_ms() as duration:
        result = sync_proof_links(
            problem_id,
            dry_run=dry_run,
            verify=verify and not dry_run,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
