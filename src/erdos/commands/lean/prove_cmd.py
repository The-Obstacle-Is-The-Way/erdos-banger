"""erdos lean prove - Run Aristotle prove-from-file on Lean files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from erdos.commands.lean.common import print_human
from erdos.commands.presenter import exit_with_result
from erdos.core.aristotle import AristotleError, run_aristotle_prove_from_file
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


def prove_with_aristotle(
    input_file: Path,
    output_file: Path,
    *,
    timeout: int = 600,
    informal: bool = False,
    formal_input_context: bool = False,
) -> CLIOutput:
    """Run Aristotle prove-from-file command.

    Args:
        input_file: Path to the input Lean file
        output_file: Path for the output Lean file
        timeout: Maximum seconds to wait for completion
        informal: Pass --informal flag to Aristotle
        formal_input_context: Pass --formal-input-context flag to Aristotle

    Returns:
        CLIOutput with execution details
    """
    try:
        result = run_aristotle_prove_from_file(
            input_file,
            output_file,
            timeout=timeout,
            informal=informal,
            formal_input_context=formal_input_context,
        )
        if result.success:
            return CLIOutput.ok(
                command="erdos lean prove",
                data=result.to_dict(),
            )
        else:
            # Nonzero exit code - return error with stderr
            return CLIOutput.err(
                command="erdos lean prove",
                error_type="AristotleError",
                message=result.stderr
                or f"Aristotle exited with code {result.exit_code}",
                code=ExitCode.ERROR,
            )
    except AristotleError as e:
        # Map error types to exit codes
        error_type_to_exit_code = {
            "ConfigError": ExitCode.CONFIG_ERROR,
            "NotFound": ExitCode.NOT_FOUND,
            "UsageError": ExitCode.USAGE_ERROR,
            "Timeout": ExitCode.ERROR,
        }
        exit_code = error_type_to_exit_code.get(e.error_type, ExitCode.ERROR)
        return CLIOutput.err(
            command="erdos lean prove",
            error_type=e.error_type,
            message=str(e),
            code=exit_code,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean prove command")
        return CLIOutput.err(
            command="erdos lean prove",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def register(app: typer.Typer) -> None:
    """Register prove command on the app."""

    @app.command()
    def prove(
        ctx: typer.Context,
        input_file: Annotated[
            Path,
            typer.Argument(
                help="Lean file to prove.",
                exists=True,
                readable=True,
            ),
        ],
        output: Annotated[
            Path,
            typer.Option(
                "--output",
                "-o",
                help="Output file path (required; must differ from input).",
            ),
        ],
        timeout: Annotated[
            int,
            typer.Option(
                "--timeout",
                "-t",
                help="Maximum seconds to wait for completion.",
            ),
        ] = 600,
        informal: Annotated[
            bool,
            typer.Option("--informal", help="Pass --informal flag to Aristotle."),
        ] = False,
        formal_input_context: Annotated[
            bool,
            typer.Option(
                "--formal-input-context",
                help="Pass --formal-input-context flag to Aristotle.",
            ),
        ] = False,
    ) -> None:
        """
        Run Aristotle prove-from-file on a Lean file.

        Requires ARISTOTLE_API_KEY environment variable to be set.
        Writes output to a separate file (never overwrites the input).

        Example: erdos lean prove Problem006.lean --output Problem006.solved.lean
        """
        # Validate output is not the same as input
        if input_file.resolve() == output.resolve():
            result = CLIOutput.err(
                command="erdos lean prove",
                error_type="UsageError",
                message="Output file cannot be the same as input file.",
                code=ExitCode.USAGE_ERROR,
            )
            exit_with_result(ctx, result, print_human=print_human)
            return

        with measure_time_ms() as duration:
            result = prove_with_aristotle(
                input_file,
                output,
                timeout=timeout,
                informal=informal,
                formal_input_context=formal_input_context,
            )

        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=print_human)
