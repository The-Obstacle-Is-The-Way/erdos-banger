"""erdos sync proof - extract proof links from forum threads (SPEC-035).

# exempt: DEBT-092 (439 LOC; CLI + verification orchestration with human output)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.panel import Panel
from rich.table import Table

from erdos.commands.presenter import console, exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.sync.forum import (
    ForumFetchError,
    fetch_and_parse_forum,
    parse_forum_html,
    save_proof_links_cache,
)
from erdos.core.sync.models import ProofLinksCache, VerificationStatus
from erdos.core.sync.proofs import (
    create_provenance,
    save_provenance,
    save_verification_log,
    verify_proof,
)
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


# =============================================================================
# Data paths
# =============================================================================

DEFAULT_CACHE_PATH = Path("data/sync_cache/proofs")


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    DEFAULT_CACHE_PATH.mkdir(parents=True, exist_ok=True)


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
# Core logic
# =============================================================================


def _run_verification(
    problem_id: int,
    cache: ProofLinksCache,
    dry_run: bool,
    cache_path: Path,
) -> CLIOutput:
    """Run verification on extracted proof links.

    Tries each link deterministically until one reaches no_sorries verification.
    Per SPEC-035: keeps the first that reaches verification_strength=no_sorries.
    """
    if not cache.links:
        return CLIOutput.ok(
            command="erdos sync proof",
            data={
                "problem_id": problem_id,
                "links": [],
                "links_count": 0,
                "provenance_path": str(
                    cache_path / str(problem_id) / "provenance.json"
                ),
                "verification_status": "unverified",
                "verification_error": "No proof links found to verify",
            },
        )

    # Try each link in order (deterministic)
    best_result = None
    best_link = None

    for link in cache.links:
        logger.info("Verifying %s", link.url)
        result = verify_proof(link, problem_id)

        # Track best result
        if best_result is None:
            best_result = result
            best_link = link

        # If we got no_sorries, we're done
        if result.status == VerificationStatus.VERIFIED:
            best_result = result
            best_link = link
            break

        # Prefer better verification status
        priority = {
            VerificationStatus.VERIFIED: 4,
            VerificationStatus.INCONCLUSIVE: 3,
            VerificationStatus.FAILED: 2,
            VerificationStatus.SOURCE_UNAVAILABLE: 1,
            VerificationStatus.UNVERIFIED: 0,
        }
        if priority.get(result.status, 0) > priority.get(best_result.status, 0):
            best_result = result
            best_link = link

    # Should always have a result by now (loop ran at least once since links is non-empty)
    if best_result is None or best_link is None:
        # Defensive: should never happen since we checked cache.links is non-empty
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="InternalError",
            message="No verification result (unexpected)",
            code=ExitCode.ERROR,
        )

    # Create and save provenance (use extracted_at from the link extraction step)
    provenance = create_provenance(problem_id, best_link, best_result).model_copy(
        update={"extracted_at": cache.extracted_at}
    )

    if not dry_run:
        _ensure_cache_dir()
        provenance_path = save_provenance(provenance, cache_dir=cache_path)

        # Save verification log
        if best_result.log_content:
            log_path = save_verification_log(
                problem_id, best_result.log_content, cache_dir=cache_path
            )
            provenance = provenance.model_copy(
                update={"log_path": str(log_path.relative_to(cache_path.parent.parent))}
            )
            # Re-save with log_path
            save_provenance(provenance, cache_dir=cache_path)
    else:
        provenance_path = cache_path / str(problem_id) / "provenance.json"

    return CLIOutput.ok(
        command="erdos sync proof",
        data={
            "problem_id": problem_id,
            "links": [
                {
                    "url": link.url,
                    "author": link.author,
                    "lean_version_hint": link.lean_version_hint,
                }
                for link in cache.links
            ],
            "links_count": len(cache.links),
            "provenance_path": str(provenance_path),
            "verification_status": best_result.status.value,
            "verification_strength": best_result.strength.value,
            "verification_error": best_result.error,
            "verified_repo": best_link.url,
            "verified_commit": best_result.repo_commit,
            "verified_files": best_result.verified_files,
            "toolchain": best_result.toolchain,
        },
    )


def sync_proof_links(
    problem_id: int,
    *,
    dry_run: bool = False,
    verify: bool = False,
    html_content: str | None = None,
    cache_path: Path | None = None,
) -> CLIOutput:
    """
    Sync proof links from a forum thread.

    This is the core logic, separated from CLI concerns for testing.

    Args:
        problem_id: Problem ID to sync
        dry_run: If True, don't write to disk
        verify: If True, clone and verify proofs
        html_content: Pre-fetched HTML (for testing with fixtures)
        cache_path: Override cache path (for testing)

    Returns:
        CLIOutput with sync result
    """
    if cache_path is None:
        cache_path = DEFAULT_CACHE_PATH

    cached = html_content is not None

    try:
        # Either parse from provided HTML or fetch from network
        if html_content is not None:
            cache = parse_forum_html(html_content, problem_id)
        else:
            cache = fetch_and_parse_forum(problem_id)

        # Save the links cache (always, even when verifying)
        if not dry_run:
            _ensure_cache_dir()
            save_proof_links_cache(cache, cache_dir=cache_path)

        # If --verify is set, run verification
        if verify:
            return _run_verification(problem_id, cache, dry_run, cache_path)

        # Default: discover-only (extract links + record provenance)
        provenance_path = cache_path / str(problem_id) / "provenance.json"
        if cache.links:
            provenance = create_provenance(
                problem_id, cache.links[0], verification=None
            ).model_copy(update={"extracted_at": cache.extracted_at})
            if not dry_run:
                _ensure_cache_dir()
                save_provenance(provenance, cache_dir=cache_path)

        return CLIOutput.ok(
            command="erdos sync proof",
            data={
                "problem_id": problem_id,
                "links": [
                    {
                        "url": link.url,
                        "author": link.author,
                        "lean_version_hint": link.lean_version_hint,
                    }
                    for link in cache.links
                ],
                "links_count": len(cache.links),
                "provenance_path": str(provenance_path),
                "cached": cached,
                "verification_status": "unverified",
            },
        )

    except ForumFetchError as e:
        code = ExitCode.NETWORK_ERROR if e.status_code != 404 else ExitCode.NOT_FOUND
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="FetchError",
            message=str(e),
            code=code,
        )
    except Exception as e:  # final safety net; convert unexpected failures to CLIOutput
        logger.exception("Unexpected error in sync proof")
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="UnexpectedError",
            message=str(e),
            code=ExitCode.ERROR,
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

    # Create a table of links
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

    # Build status line with verification details
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

    # Choose panel style based on verification status
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
        typer.Argument(
            help="Problem ID to extract proof links for",
            min=1,
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be extracted without writing to disk",
        ),
    ] = False,
    verify: Annotated[
        bool,
        typer.Option(
            "--verify",
            help="Clone and verify proofs (runs untrusted build tooling)",
        ),
    ] = False,
) -> None:
    """
    Extract proof repository links from the forum thread.

    Fetches the forum thread for the given problem and extracts GitHub/GitLab
    repository links. Writes the results to data/sync_cache/proofs/<id>/links.json.

    By default, this command only extracts and records links. Use --verify to
    also clone repositories and run `lake build` to verify Lean proofs.

    ⚠️  WARNING: --verify runs untrusted code from external repositories.

    Example:
        erdos sync proof 347
        erdos sync proof 347 --verify
        erdos sync proof 347 --dry-run
    """
    # Print security warning for --verify (but not in JSON mode)
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
