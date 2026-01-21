"""erdos lean import - Import upstream formalizations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from erdos.commands.lean.common import print_human
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.formal_conjectures import (
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
    LocalFormalizationInfo,
    ProvenanceEntry,
    fetch_upstream_lean_file,
    get_cache_path,
    get_local_file_path,
    load_provenance,
    save_provenance,
)
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


def _validate_imported_file(
    project_path: Path, local_path: Path, skip_validation: bool
) -> bool | CLIOutput:
    """Validate imported file with Lean. Returns bool or CLIOutput on error."""
    if skip_validation:
        return False
    try:
        runner = LeanRunner(project_path)
        check_result = runner.check(local_path)
        if not check_result.success:
            return CLIOutput.err(
                command="erdos lean import",
                error_type="LeanError",
                message=f"Imported file has Lean errors: {check_result.errors}",
                code=ExitCode.LEAN_ERROR,
            )
        return True
    except LeanRunnerError as e:
        logger.warning("Lean validation failed: %s", e)
        return False


def _update_provenance(
    local_path: Path,
    problem_id: int,
    fetch_result: Any,
) -> None:
    """Update provenance file after import."""
    prov_path = local_path.parent / ".provenance.yaml"
    prov = load_provenance(prov_path)
    entry = ProvenanceEntry(
        problem_id=problem_id,
        source=FORMAL_CONJECTURES_REPO,
        url=fetch_result.url,
        imported_at=datetime.now(tz=UTC),
        sha256=fetch_result.sha256,
        remote_etag=fetch_result.etag,
    )
    prov.upsert(entry)
    save_provenance(prov_path, prov)


def _build_import_data(
    problem_id: int,
    local_path: Path,
    cache_path: Path,
    fetch_url: str,
    fetch_sha256: str,
    *,
    dry_run: bool,
    written: bool,
    lean_validated: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build common import result data dict."""
    data: dict[str, Any] = {
        "problem_id": problem_id,
        "dry_run": dry_run,
        "written": written,
        "path": str(local_path),
        "cache_path": str(cache_path),
        "source": FORMAL_CONJECTURES_REPO,
        "url": fetch_url,
        "sha256": fetch_sha256,
        "lean_validated": lean_validated,
    }
    if reason:
        data["reason"] = reason
    return data


def _check_local_conflict(
    local_path: Path, fetch_sha256: str, force: bool
) -> str | None:
    """Check for local file conflict. Returns error message if conflict, None if OK."""
    if not local_path.exists() or force:
        return None
    local_info = LocalFormalizationInfo.from_file(local_path)
    if local_info.sha256 == fetch_sha256:
        return "same_content"
    return (
        f"Local file exists with different content: {local_path}. "
        "Use --force to overwrite."
    )


def _do_import(
    problem_id: int,
    project_path: Path,
    fetch_result: Any,
    local_path: Path,
    cache_path: Path,
    *,
    force: bool,
    dry_run: bool,
    skip_lean_validation: bool,
) -> CLIOutput:
    """Execute the import operation. Extracted to reduce return statement count."""
    # Check for conflicts
    conflict = _check_local_conflict(local_path, fetch_result.sha256, force)
    if conflict == "same_content":
        return CLIOutput.ok(
            command="erdos lean import",
            data=_build_import_data(
                problem_id,
                local_path,
                cache_path,
                fetch_result.url,
                fetch_result.sha256,
                dry_run=dry_run,
                written=False,
                lean_validated=False,
                reason="already_imported",
            ),
        )
    if conflict:
        return CLIOutput.err(
            command="erdos lean import",
            error_type="Conflict",
            message=conflict,
            code=ExitCode.ERROR,
        )

    if dry_run:
        return CLIOutput.ok(
            command="erdos lean import",
            data=_build_import_data(
                problem_id,
                local_path,
                cache_path,
                fetch_result.url,
                fetch_result.sha256,
                dry_run=True,
                written=False,
                lean_validated=False,
            ),
        )

    # Write file and validate
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(fetch_result.content, encoding="utf-8")
    lean_validated = _validate_imported_file(
        project_path, local_path, skip_lean_validation
    )
    if isinstance(lean_validated, CLIOutput):
        return lean_validated  # Validation error

    # Update provenance
    _update_provenance(local_path, problem_id, fetch_result)

    return CLIOutput.ok(
        command="erdos lean import",
        data=_build_import_data(
            problem_id,
            local_path,
            cache_path,
            fetch_result.url,
            fetch_result.sha256,
            dry_run=False,
            written=True,
            lean_validated=lean_validated,
        ),
    )


def import_upstream_formalization(
    problem_id: int,
    project_path: Path,
    *,
    source_url: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    no_network: bool = False,
    skip_lean_validation: bool = False,
) -> CLIOutput:
    """Import upstream formalization for a problem."""
    try:
        fetch_result = fetch_upstream_lean_file(
            project_path, problem_id, source_url=source_url, no_network=no_network
        )
        local_path = get_local_file_path(project_path, problem_id)
        cache_path = get_cache_path(project_path, problem_id)
        return _do_import(
            problem_id,
            project_path,
            fetch_result,
            local_path,
            cache_path,
            force=force,
            dry_run=dry_run,
            skip_lean_validation=skip_lean_validation,
        )
    except FormalConjecturesError as e:
        error_type_to_exit_code = {
            "NetworkError": ExitCode.NETWORK_ERROR,
            "NotFound": ExitCode.NOT_FOUND,
            "ConfigError": ExitCode.CONFIG_ERROR,
        }
        exit_code = error_type_to_exit_code.get(e.error_type, ExitCode.ERROR)
        return CLIOutput.err(
            command="erdos lean import",
            error_type=e.error_type,
            message=str(e),
            code=exit_code,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean import command")
        return CLIOutput.err(
            command="erdos lean import",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def register(app: typer.Typer) -> None:
    """Register import command on the app."""

    @app.command(name="import")
    def import_cmd(
        ctx: typer.Context,
        problem_id: Annotated[
            int,
            typer.Argument(
                help="Problem ID to import formalization for.",
                min=1,
            ),
        ],
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                help="Path to Lean project (default: formal/lean/)",
            ),
        ] = None,
        source: Annotated[
            str | None,
            typer.Option("--source", help="Override source URL"),
        ] = None,
        force: Annotated[
            bool,
            typer.Option("--force", "-f", help="Overwrite existing local file"),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run", help="Show what would be imported without writing"
            ),
        ] = False,
        no_network: Annotated[
            bool,
            typer.Option("--no-network", help="Use cached upstream file only"),
        ] = False,
        skip_lean_validation: Annotated[
            bool,
            typer.Option(
                "--skip-lean-validation",
                help="Do not run Lean check on imported file",
            ),
        ] = False,
    ) -> None:
        """
        Import upstream formalization for a problem.

        Fetches from google-deepmind/formal-conjectures by default.

        Example: erdos lean import 6
        """
        with measure_time_ms() as duration:
            path = project_path or Path("formal/lean")
            result = import_upstream_formalization(
                problem_id,
                path,
                source_url=source,
                force=force,
                dry_run=dry_run,
                no_network=no_network,
                skip_lean_validation=skip_lean_validation,
            )

        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=print_human)
