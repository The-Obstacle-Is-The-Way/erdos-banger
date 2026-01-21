"""erdos lean check - Check Lean files for compilation errors."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from erdos.commands.lean.common import print_human
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


def check_lean_file(file_path: Path, project_path: Path) -> CLIOutput:
    """Check a Lean file for errors."""
    try:
        runner = LeanRunner(project_path)
        result = runner.check(file_path)
        return CLIOutput.ok(
            command="erdos lean check",
            data=result.model_dump(mode="json"),
        )
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="LeanRunnerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except FileNotFoundError:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotFound",
            message=f"File not found: {file_path}",
            code=ExitCode.NOT_FOUND,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean check command")
        return CLIOutput.err(
            command="erdos lean check",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def register(app: typer.Typer) -> None:
    """Register check command on the app."""

    @app.command()
    def check(
        ctx: typer.Context,
        file: Annotated[
            Path,
            typer.Argument(
                help="Lean file to check.",
                exists=True,
                readable=True,
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
    ) -> None:
        """
        Check a Lean file for compilation errors.

        Example: erdos lean check Erdos/Problem006.lean
        """
        with measure_time_ms() as duration:
            path = project_path or Path("formal/lean")
            result = check_lean_file(file, path)

        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=print_human)

        if (
            result.success
            and isinstance(result.data, dict)
            and not result.data.get("success", True)
        ):
            raise typer.Exit(code=ExitCode.LEAN_ERROR)
