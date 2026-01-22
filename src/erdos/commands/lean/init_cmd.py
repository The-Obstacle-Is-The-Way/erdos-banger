"""erdos lean init - Initialize Lean 4 project."""

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


def init_lean_project(project_path: Path, *, fetch_mathlib: bool = True) -> CLIOutput:
    """Initialize Lean project structure."""
    try:
        runner = LeanRunner(project_path)
        runner.init(fetch_mathlib=fetch_mathlib)
        return CLIOutput.ok(
            command="erdos lean init",
            data={"project_path": str(project_path), "initialized": True},
        )
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="LeanRunnerError",
            message=str(e) or "Lean initialization failed",
            code=ExitCode.LEAN_ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean init command")
        return CLIOutput.err(
            command="erdos lean init",
            error_type="Error",
            message=str(e) or "Unexpected error",
            code=ExitCode.ERROR,
        )


def register(app: typer.Typer) -> None:
    """Register init command on the app."""

    @app.command()
    def init(
        ctx: typer.Context,
        project_path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                "-p",
                help="Path to Lean project (default: formal/lean/)",
            ),
        ] = None,
        no_mathlib: Annotated[
            bool,
            typer.Option(
                "--no-mathlib",
                help="Initialize a minimal project without mathlib (faster, offline).",
            ),
        ] = False,
    ) -> None:
        """
        Initialize Lean 4 project with mathlib.

        Creates lakefile.lean, lean-toolchain, and directory structure.
        """

        with measure_time_ms() as duration:
            path = project_path or Path("formal/lean")
            path.mkdir(parents=True, exist_ok=True)
            result = init_lean_project(path, fetch_mathlib=not no_mathlib)

        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=print_human)
