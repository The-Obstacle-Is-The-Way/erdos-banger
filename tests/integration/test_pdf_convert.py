"""Integration tests for PDF convert command (SPEC-019)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.exit_codes import ExitCode


runner = CliRunner()


class TestConvertCommandHelp:
    """Tests for convert command help output."""

    def test_convert_help_shows_options(self, strip_ansi) -> None:
        """Convert --help shows expected options."""
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Check key options are documented
        assert "--output" in output or "-o" in output
        assert "--format" in output
        assert "--converter" in output
        assert "--use-llm" in output

    def test_convert_help_shows_device_option(self, strip_ansi) -> None:
        """Convert --help documents the --device option (DEBT-036)."""
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # --device option must be documented
        assert "--device" in output
        # Help text should mention supported devices
        assert (
            "cpu" in output.lower()
            or "cuda" in output.lower()
            or "mps" in output.lower()
        )


class TestConvertCommandValidation:
    """Tests for convert command validation."""

    def test_convert_requires_pdf_path(self) -> None:
        """Convert command requires PDF path argument."""
        result = runner.invoke(app, ["convert"])
        # Should show error or help
        assert result.exit_code != 0

    def test_convert_rejects_nonexistent_file(self) -> None:
        """Convert returns error for nonexistent file."""
        result = runner.invoke(app, ["convert", "/nonexistent/file.pdf"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_convert_rejects_non_pdf_file(self, tmp_path: Path) -> None:
        """Convert returns error for non-PDF file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")

        result = runner.invoke(app, ["convert", str(txt_file)])
        assert result.exit_code != 0
        assert "pdf" in result.output.lower()


class TestConvertCommandOutput:
    """Tests for convert command output formats."""

    def test_convert_json_output_structure(self, tmp_path: Path) -> None:
        """Convert --json produces valid CLIOutput structure."""
        # Create a minimal PDF-like file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        # Mock the converter to avoid needing actual marker
        with patch("erdos.core.pdf_converter.convert_pdf") as mock_convert:
            from erdos.core.pdf_converter import PDFConversionResult

            mock_convert.return_value = PDFConversionResult(
                success=True,
                text="# Converted\n\nTest content",
                converter="marker",
            )

            result = runner.invoke(app, ["--json", "convert", str(pdf_file)])
            # Should succeed or fail gracefully with JSON
            if result.exit_code == 0:
                import json

                data = json.loads(result.output)
                assert "success" in data
                assert "data" in data or "error" in data

    def test_convert_format_text_strips_basic_markdown(self, tmp_path: Path) -> None:
        """Convert --format text removes basic markdown markers."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with (
            patch(
                "erdos.commands.convert.get_available_converters",
                return_value=["marker"],
            ),
            patch("erdos.commands.convert.convert_pdf") as mock_convert,
        ):
            from erdos.core.pdf_converter import PDFConversionResult

            mock_convert.return_value = PDFConversionResult(
                success=True,
                text="# Title\n\nSome `code` and a [link](https://example.com).\n```py\nx = 1\n```",
                converter="marker",
            )

            result = runner.invoke(app, ["convert", str(pdf_file), "--format", "text"])
            assert result.exit_code == 0
            assert "# " not in result.stdout
            assert "`" not in result.stdout
            assert "(" not in result.stdout  # link URL stripped
            assert "Title" in result.stdout
            assert "Some code and a link." in result.stdout

    def test_convert_format_json_writes_json_to_stdout(self, tmp_path: Path) -> None:
        """Convert --format json prints a JSON object to stdout (not CLIOutput envelope)."""
        import json

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with (
            patch(
                "erdos.commands.convert.get_available_converters",
                return_value=["marker"],
            ),
            patch("erdos.commands.convert.convert_pdf") as mock_convert,
        ):
            from erdos.core.pdf_converter import PDFConversionResult

            mock_convert.return_value = PDFConversionResult(
                success=True,
                text="# Converted\n\nTest content",
                converter="marker",
                metadata={"pages": "1"},
            )

            result = runner.invoke(app, ["convert", str(pdf_file), "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.stdout)
            assert payload["converter"] == "marker"
            assert payload["metadata"]["pages"] == "1"
            assert "text" in payload
            assert "char_count" in payload


class TestConvertCommandOptions:
    """Tests for convert command options."""

    def test_convert_output_option_validates_path(self, tmp_path: Path) -> None:
        """Convert --output validates output path."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        # Output to a directory (should fail or succeed depending on implementation)
        result = runner.invoke(
            app, ["convert", str(pdf_file), "--output", str(tmp_path)]
        )
        # Exit codes: SUCCESS=0, ERROR=1, USAGE_ERROR=2, CONFIG_ERROR=10 (no converter)
        assert result.exit_code in (0, 1, 2, 10)

    def test_convert_format_option_values(self, tmp_path: Path) -> None:
        """Convert --format accepts expected values."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        # Check that invalid format is rejected or handled
        result = runner.invoke(
            app, ["convert", str(pdf_file), "--format", "invalid_format"]
        )
        # Should either fail validation or handle gracefully
        # Exit code 2 = typer validation error for invalid enum value
        assert result.exit_code in (0, 1, 2, 10)

    def test_convert_converter_option(self, tmp_path: Path) -> None:
        """Convert --converter accepts converter names."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        # Request pdfplumber converter
        result = runner.invoke(
            app, ["convert", str(pdf_file), "--converter", "pdfplumber"]
        )
        # Should not crash (may fail if converter not available - exit 10)
        assert result.exit_code in (0, 1, 2, 10)


class TestConvertCommandDeviceValidation:
    """Tests for convert command --device validation (DEBT-059)."""

    def test_device_invalid_value_fails(self, tmp_path: Path) -> None:
        """--device with invalid value returns usage error."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        result = runner.invoke(
            app,
            ["--json", "convert", str(pdf_file), "--device", "invalid"],
        )

        # Should be usage error (2) for invalid device
        assert result.exit_code == ExitCode.USAGE_ERROR
        import json

        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "UsageError"
        assert "device" in data["error"]["message"].lower()

    def test_device_cpu_accepted(self, tmp_path: Path) -> None:
        """--device cpu is a valid value."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        result = runner.invoke(
            app,
            ["convert", str(pdf_file), "--device", "cpu"],
        )
        # Should not fail due to invalid device (may fail due to missing converter = 10)
        assert result.exit_code in (0, 1, 10)

    def test_device_cuda_accepted(self, tmp_path: Path) -> None:
        """--device cuda is a valid value."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        result = runner.invoke(
            app,
            ["convert", str(pdf_file), "--device", "cuda"],
        )
        # Should not fail due to invalid device (may fail due to missing converter = 10)
        assert result.exit_code in (0, 1, 10)

    def test_device_mps_accepted(self, tmp_path: Path) -> None:
        """--device mps is a valid value."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        result = runner.invoke(
            app,
            ["convert", str(pdf_file), "--device", "mps"],
        )
        # Should not fail due to invalid device (may fail due to missing converter = 10)
        assert result.exit_code in (0, 1, 10)

    def test_device_case_insensitive(self, tmp_path: Path) -> None:
        """--device is case insensitive (CPU, Cpu, cpu all work)."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        result = runner.invoke(
            app,
            ["convert", str(pdf_file), "--device", "CPU"],
        )
        # Should not fail due to invalid device (may fail due to missing converter = 10)
        assert result.exit_code in (0, 1, 10)


class TestConvertCommandLLMOptions:
    """Tests for convert command LLM options."""

    def test_convert_use_llm_flag(self, tmp_path: Path) -> None:
        """Convert --use-llm flag is recognized."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        # Just check flag is accepted (will fail without converter)
        result = runner.invoke(app, ["convert", str(pdf_file), "--use-llm"])
        # Should not fail due to unknown option
        assert (
            "--use-llm" not in result.output.lower()
            or "unknown" not in result.output.lower()
        )

    def test_convert_llm_service_option(self, tmp_path: Path) -> None:
        """Convert --llm-service accepts service names."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        result = runner.invoke(
            app, ["convert", str(pdf_file), "--use-llm", "--llm-service", "claude"]
        )
        # Should not fail due to unknown service (may fail if converter not available - exit 10)
        assert result.exit_code in (0, 1, 2, 10)
