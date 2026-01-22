"""Integration tests for erdos lean formalize command (DEBT-059 validation)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from erdos.core.lean_runner import LeanRunnerError


if TYPE_CHECKING:
    from pathlib import Path


runner = CliRunner()


class TestLeanFormalizeValidation:
    """Tests for input validation in lean formalize command."""

    def test_max_concurrent_zero_fails(self) -> None:
        """--max-concurrent=0 returns usage error."""
        result = runner.invoke(
            app,
            [
                "--json",
                "lean",
                "formalize",
                "--all",
                "--max-concurrent",
                "0",
            ],
        )

        assert result.exit_code == ExitCode.USAGE_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "UsageError"
        assert "max-concurrent" in data["error"]["message"].lower()

    def test_max_concurrent_negative_fails(self) -> None:
        """--max-concurrent=-1 returns usage error."""
        result = runner.invoke(
            app,
            [
                "--json",
                "lean",
                "formalize",
                "--all",
                "--max-concurrent",
                "-1",
            ],
        )

        assert result.exit_code == ExitCode.USAGE_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "UsageError"

    def test_no_network_without_import_upstream_fails(self) -> None:
        """--no-network without --import-upstream returns usage error."""
        result = runner.invoke(
            app,
            [
                "--json",
                "lean",
                "formalize",
                "1",
                "--no-network",
            ],
        )

        assert result.exit_code == ExitCode.USAGE_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "UsageError"
        assert "import-upstream" in data["error"]["message"].lower()


class TestLeanFormalizeHelp:
    """Tests for help documentation."""

    def test_formalize_help_shows_max_concurrent(self, strip_ansi) -> None:
        """Formalize --help shows --max-concurrent option."""
        result = runner.invoke(app, ["lean", "formalize", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--max-concurrent" in output

    def test_formalize_help_shows_no_network(self, strip_ansi) -> None:
        """Formalize --help shows --no-network option."""
        result = runner.invoke(app, ["lean", "formalize", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--no-network" in output


class TestLeanInitExitCodes:
    """Tests for lean init command exit codes (DEBT-059)."""

    def test_lean_runner_error_returns_lean_error_code(self, tmp_path: Path) -> None:
        """LeanRunnerError returns LEAN_ERROR exit code."""
        with patch("erdos.commands.lean.init_cmd.LeanRunner") as mock_runner_cls:
            mock_runner = mock_runner_cls.return_value
            mock_runner.init.side_effect = LeanRunnerError("Lake update failed")

            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "init",
                    "--path",
                    str(tmp_path),
                ],
            )

        assert result.exit_code == ExitCode.LEAN_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "LeanRunnerError"

    def test_unexpected_error_returns_error_code(self, tmp_path: Path) -> None:
        """Unexpected exception returns ERROR exit code."""
        with patch("erdos.commands.lean.init_cmd.LeanRunner") as mock_runner_cls:
            mock_runner = mock_runner_cls.return_value
            mock_runner.init.side_effect = RuntimeError("Unexpected failure")

            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "init",
                    "--path",
                    str(tmp_path),
                ],
            )

        assert result.exit_code == ExitCode.ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "Error"
