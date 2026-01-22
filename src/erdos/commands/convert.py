"""erdos convert - standalone PDF conversion command (SPEC-019)."""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.pdf.converter import (
    LLMService,
    PDFConversionConfig,
    convert_pdf,
    get_available_converters,
)
from erdos.core.timing import measure_time_ms


class OutputFormat(str, Enum):
    """Output format for converted PDF."""

    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


app = typer.Typer(
    help="Convert PDF files to text/markdown.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print conversion results."""
    text = result_data.get("text") or ""
    if result_data.get("format") == OutputFormat.JSON.value:
        typer.echo(text)
    elif text:
        console.print(text)
    else:
        console.print("[yellow]No text extracted[/yellow]")

    # Show metadata
    converter = result_data.get("converter", "unknown")
    char_count = int(
        result_data.get("char_count") or len(result_data.get("text", "") or "")
    )
    err_console.print(f"\n[dim]Converter: {converter}, Characters: {char_count}[/dim]")


def _markdown_to_text(markdown: str) -> str:
    """Convert markdown to a best-effort plain text representation."""
    if not markdown:
        return ""

    # Remove fenced code markers but keep the code content.
    text = re.sub(r"^```[^\n]*\n", "", markdown, flags=re.MULTILINE)
    text = text.replace("```", "")

    # Replace markdown links with their visible text.
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove inline code backticks.
    text = text.replace("`", "")

    # Strip heading markers.
    lines = [re.sub(r"^#{1,6}\s+", "", line) for line in text.splitlines()]
    return "\n".join(lines)


def _validate_pdf_path(pdf_path: Path) -> CLIOutput | None:
    """Validate PDF path exists and has .pdf extension.

    Returns:
        CLIOutput error if validation fails, None if OK.
    """
    if not pdf_path.exists():
        return CLIOutput.err(
            command="erdos convert",
            error_type="NotFoundError",
            message=f"File not found: {pdf_path}",
            code=ExitCode.NOT_FOUND,
        )

    if pdf_path.suffix.lower() != ".pdf":
        return CLIOutput.err(
            command="erdos convert",
            error_type="UsageError",
            message=f"Not a PDF file: {pdf_path.suffix}",
            code=ExitCode.USAGE_ERROR,
        )

    return None


def _convert_and_output(
    pdf_path: Path,
    config: PDFConversionConfig,
    output_path: Path | None,
    output_format: OutputFormat,
) -> CLIOutput:
    """Run conversion and handle output.

    Args:
        pdf_path: Path to PDF file.
        config: Conversion configuration.
        output_path: Optional output file path.
        output_format: Output format to use.

    Returns:
        CLIOutput with conversion result.
    """
    result = convert_pdf(pdf_path, config)

    if not result.success:
        return CLIOutput.err(
            command="erdos convert",
            error_type="ConversionError",
            message=result.error or "Unknown conversion error",
            code=ExitCode.ERROR,
        )

    extracted_text = result.text or ""
    extracted_char_count = len(extracted_text)

    # Format output based on requested format
    if output_format == OutputFormat.TEXT:
        output_text = _markdown_to_text(extracted_text)
        output_char_count = len(output_text)
    elif output_format == OutputFormat.JSON:
        payload = {
            "pdf_path": str(pdf_path),
            "converter": result.converter,
            "text": extracted_text,
            "char_count": extracted_char_count,
            "metadata": result.metadata,
        }
        output_text = json.dumps(payload, ensure_ascii=False)
        output_char_count = extracted_char_count
    else:
        output_text = extracted_text
        output_char_count = extracted_char_count

    # Write to file if output path specified
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")

    return CLIOutput.ok(
        command="erdos convert",
        data={
            "pdf_path": str(pdf_path),
            "converter": result.converter,
            "text": output_text,
            "char_count": output_char_count,
            "output_path": str(output_path) if output_path else None,
            "format": output_format.value,
            "metadata": result.metadata,
        },
    )


@app.callback(invoke_without_command=True)
def convert(
    ctx: typer.Context,
    pdf_path: Annotated[
        Path,
        typer.Argument(
            help="Path to PDF file to convert",
            exists=False,  # We validate ourselves for better error messages
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (default: stdout)",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, text, or json",
            case_sensitive=False,
        ),
    ] = OutputFormat.MARKDOWN,
    converter: Annotated[
        str,
        typer.Option(
            "--converter",
            "-c",
            help="Converter to use: marker (default), pdfplumber",
        ),
    ] = "marker",
    use_llm: Annotated[
        bool,
        typer.Option(
            "--use-llm",
            help="Enable LLM-enhanced extraction (Marker only)",
        ),
    ] = False,
    llm_service: Annotated[
        str | None,
        typer.Option(
            "--llm-service",
            help="LLM service: gemini, claude, openai, ollama",
        ),
    ] = None,
    force_ocr: Annotated[
        bool,
        typer.Option(
            "--force-ocr",
            help="Force OCR even if text is extractable (Marker only)",
        ),
    ] = False,
    device: Annotated[
        str | None,
        typer.Option(
            "--device",
            "-d",
            help="Torch device for Marker: cpu, cuda, mps (sets TORCH_DEVICE env var)",
        ),
    ] = None,
) -> None:
    """Convert a PDF file to markdown/text.

    Uses Marker (GPL, optional) for high-quality conversion with math preservation.
    Falls back to pdfplumber (MIT) for basic text extraction.

    Install Marker with: uv sync --extra pdf

    Examples:

        erdos convert paper.pdf
        erdos convert paper.pdf --output paper.md
        erdos convert paper.pdf --use-llm --llm-service claude
        erdos convert paper.pdf --converter pdfplumber
    """
    json_mode = bool((ctx.obj or {}).get("json"))

    # Validate PDF path
    if validation_error := _validate_pdf_path(pdf_path):
        exit_with_result(ctx, validation_error)
        return

    # Parse LLM service if provided
    llm_service_enum: LLMService | None = None
    if llm_service:
        try:
            llm_service_enum = LLMService(llm_service.lower())
        except ValueError:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command="erdos convert",
                    error_type="UsageError",
                    message=f"Invalid LLM service: {llm_service}. Use: gemini, claude, openai, ollama",
                    code=ExitCode.USAGE_ERROR,
                ),
            )
            return

    # Validate --device option
    allowed_devices = {"cpu", "cuda", "mps"}
    if device is not None and device.lower() not in allowed_devices:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos convert",
                error_type="UsageError",
                message=f"Invalid device: {device}. Use: cpu, cuda, mps",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return
    # Normalize device to lowercase
    device_normalized = device.lower() if device else None

    # Check converter availability
    available = get_available_converters()
    if converter not in available:
        if not available:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command="erdos convert",
                    error_type="ConfigError",
                    message="No PDF converters available. Install Marker: uv sync --extra pdf",
                    code=ExitCode.CONFIG_ERROR,
                ),
            )
            return
        # Fall back to first available
        err_console.print(
            f"[yellow]Converter '{converter}' not available, using '{available[0]}'[/yellow]"
        )
        converter = available[0]

    # Build config
    config = PDFConversionConfig(
        converter=converter,
        use_llm=use_llm,
        llm_service=llm_service_enum,
        force_ocr=force_ocr,
        torch_device=device_normalized,
    )

    # Show progress
    if not json_mode:
        err_console.print(f"[dim]Converting {pdf_path.name}...[/dim]")

    # Run conversion
    with measure_time_ms() as duration:
        result = _convert_and_output(pdf_path, config, output, output_format)

    result.duration_ms = duration[0]

    # Exit with result
    exit_with_result(ctx, result, print_human=_print_human)
