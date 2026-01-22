"""Shared helpers and output formatters for lean subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from erdos.core.models import LeanCheckResult


# Default upstream metadata path
UPSTREAM_METADATA_PATH = Path("data/erdosproblems/data/problems.yaml")

# Console instances for output
console = Console()
err_console = Console(stderr=True)


def print_human_check_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Lean check result."""
    result = LeanCheckResult.model_validate(result_data, strict=False)

    if result.success:
        console.print(f"[green]✓[/green] {result.file} compiled successfully")
    else:
        console.print(f"[red]✗[/red] {result.file} has {result.error_count} error(s)")
        for error in result.errors:
            console.print(f"  {error}")


def print_human_formalize_result(result_data: dict[str, Any]) -> None:
    """Pretty-print formalize result."""
    output_file = result_data.get("file", "unknown")
    console.print(f"[green]✓[/green] Created {output_file}")
    console.print(f"  Run: erdos lean check {output_file}")


def print_human_prove_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Aristotle prove result."""
    output_file = result_data.get("output_file", "unknown")
    console.print(f"[green]✓[/green] Proof generated at {output_file}")
    console.print(f"  Run: erdos lean check {output_file}")


def print_human_status_result(result_data: dict[str, Any]) -> None:
    """Pretty-print lean status result."""
    if "summary" in result_data:
        # All problems summary
        summary = result_data["summary"]
        total = summary.get("total", 0)
        upstream_formalized = summary.get("upstream_formalized", 0)
        local_exists = summary.get("local_exists", 0)
        console.print(f"Formalization Status ({total} problems)")
        console.print()
        console.print(f"  Upstream formalized: {upstream_formalized}")
        console.print(f"  Local files exist:   {local_exists}")
    else:
        # Single problem
        problem_id = result_data.get("problem_id", "?")
        console.print(f"Problem {problem_id}")
        console.print()

        # Upstream info
        upstream = result_data.get("upstream", {})
        if upstream.get("available"):
            state = "formalized" if upstream.get("formalized") else "not formalized"
            console.print(f"Upstream: {state}")
            if upstream.get("url"):
                console.print(f"  URL: {upstream['url']}")
        else:
            console.print("Upstream: [dim]no metadata available[/dim]")

        # Local info
        local = result_data.get("local", {})
        if local.get("exists"):
            sorry_str = "yes" if local.get("has_sorry") else "no"
            console.print(f"Local: {local.get('path')}")
            console.print(f"  Has sorry: {sorry_str}")
        else:
            console.print("Local: [dim]no file[/dim]")

        # Comparison
        comparison = result_data.get("comparison")
        if comparison:
            console.print(f"Comparison: {comparison}")


def print_human_import_result(result_data: dict[str, Any]) -> None:
    """Pretty-print lean import result."""
    path = result_data.get("path")
    dry_run = result_data.get("dry_run", False)
    written = result_data.get("written", False)

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] Would import to {path}")
    elif written:
        console.print(f"[green]✓[/green] Imported to {path}")
        validated = result_data.get("lean_validated", False)
        if validated:
            console.print("  Lean validation: passed")
        else:
            console.print("  [yellow]Lean validation: skipped[/yellow]")
    else:
        console.print(f"[yellow]![/yellow] File already up to date: {path}")


def print_human(result_data: Any) -> None:
    """Route result data to appropriate human-readable printer."""
    if isinstance(result_data, dict):
        # LeanCheckResult has "file" and "success" keys
        if {"file", "success"}.issubset(result_data.keys()):
            print_human_check_result(result_data)
        # Formalize result has "problem_id" and "file" keys (but not "upstream"/"local")
        elif (
            {"problem_id", "file"}.issubset(result_data.keys())
            and "upstream" not in result_data
            and "local" not in result_data
            and "dry_run" not in result_data
        ):
            print_human_formalize_result(result_data)
        # Aristotle prove result has "input_file", "output_file", "aristotle" keys
        elif {"input_file", "output_file", "aristotle"}.issubset(result_data.keys()):
            print_human_prove_result(result_data)
        # Init result has "project_path" and "initialized" keys
        elif {"project_path", "initialized"}.issubset(result_data.keys()):
            console.print(
                f"[green]✓[/green] Initialized Lean project at "
                f"{result_data['project_path']}"
            )
        # Status result has "upstream" or "local" or "summary" keys
        elif (
            "upstream" in result_data
            or "local" in result_data
            or "summary" in result_data
        ):
            print_human_status_result(result_data)
        # Import result has "dry_run" and "written" keys
        elif "dry_run" in result_data and "written" in result_data:
            print_human_import_result(result_data)
        else:
            console.print(result_data)
    else:
        console.print(result_data)


def print_human_batch_formalize(result_data: dict[str, Any]) -> None:
    """Pretty-print batch formalize results."""
    batch_id = result_data.get("batch_id", "?")
    total = result_data.get("total", 0)
    completed = result_data.get("completed", 0)
    failed = result_data.get("failed", 0)
    failed_ids = result_data.get("failed_ids", [])
    dry_run = result_data.get("dry_run", False)

    if dry_run:
        console.print(f"\n[yellow]Dry run[/yellow]: Would formalize {total} problems")
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
