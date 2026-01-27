"""Integration tests for erdos lean prove command."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from tests.cli_runner import make_cli_runner


if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


runner = make_cli_runner()


class TestLeanProveCommandValidation:
    """Tests for input validation in lean prove command."""

    def test_missing_input_file_fails(self, tmp_path: Path) -> None:
        """Non-existent input file returns error."""
        nonexistent = tmp_path / "nonexistent.lean"
        output = tmp_path / "output.lean"

        result = runner.invoke(
            app, ["lean", "prove", str(nonexistent), "--output", str(output)]
        )

        # Typer handles this validation and exits with code 2
        assert result.exit_code != 0

    def test_missing_output_option_fails(self, tmp_path: Path) -> None:
        """Missing --output option returns error."""
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")

        result = runner.invoke(app, ["lean", "prove", str(input_file)])

        assert result.exit_code != 0

    def test_output_same_as_input_fails(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Output file same as input returns usage error."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")

        result = runner.invoke(
            app,
            ["--json", "lean", "prove", str(input_file), "--output", str(input_file)],
        )

        assert result.exit_code == ExitCode.USAGE_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "UsageError"
        assert "same" in data["error"]["message"].lower()


class TestLeanProveCommandConfig:
    """Tests for configuration validation in lean prove command."""

    def test_missing_api_key_returns_config_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Missing ARISTOTLE_API_KEY returns config error."""
        monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        result = runner.invoke(
            app,
            ["--json", "lean", "prove", str(input_file), "--output", str(output)],
        )

        assert result.exit_code == ExitCode.CONFIG_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "ConfigError"
        assert "ARISTOTLE_API_KEY" in data["error"]["message"]

    def test_missing_command_returns_config_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Missing aristotle command returns config error."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        monkeypatch.delenv("ERDOS_ARISTOTLE_COMMAND", raising=False)
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        with patch("shutil.which", return_value=None):
            result = runner.invoke(
                app,
                ["--json", "lean", "prove", str(input_file), "--output", str(output)],
            )

        assert result.exit_code == ExitCode.CONFIG_ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "ConfigError"

    def test_dotenv_api_key_is_loaded_and_passed_to_subprocess(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """ARISTOTLE_API_KEY is loaded from `.env` when enabled."""
        monkeypatch.setenv("ERDOS_LOAD_DOTENV", "1")
        monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)
        monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with runner.isolated_filesystem():
            from pathlib import Path

            Path(".env").write_text("ARISTOTLE_API_KEY=dotenv-key\n", encoding="utf-8")
            input_file = Path("input.lean")
            input_file.write_text("-- test", encoding="utf-8")
            output = Path("output.lean")

            with (
                patch("shutil.which", return_value="/usr/bin/aristotle"),
                patch("subprocess.run", return_value=mock_result) as mock_run,
            ):
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "prove",
                        str(input_file),
                        "--output",
                        str(output),
                    ],
                )

        assert result.exit_code == ExitCode.SUCCESS
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"]["ARISTOTLE_API_KEY"] == "dotenv-key"

    def test_dotenv_api_key_is_loaded_from_repo_root_when_run_from_subdir(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Running from a subdirectory should still discover repo-root `.env`."""
        monkeypatch.setenv("ERDOS_LOAD_DOTENV", "1")
        monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)
        monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with runner.isolated_filesystem():
            from pathlib import Path

            Path("src/erdos").mkdir(parents=True)
            Path("pyproject.toml").write_text(
                '[project]\nname = "erdos-banger"\n', encoding="utf-8"
            )
            Path(".env").write_text("ARISTOTLE_API_KEY=dotenv-key\n", encoding="utf-8")

            Path("formal/lean").mkdir(parents=True)
            input_file = Path("formal/lean/input.lean")
            input_file.write_text("-- test", encoding="utf-8")
            output_file = Path("formal/lean/output.lean")

            old_cwd = os.getcwd()
            os.chdir(Path("formal/lean"))
            try:
                with (
                    patch("shutil.which", return_value="/usr/bin/aristotle"),
                    patch("subprocess.run", return_value=mock_result) as mock_run,
                ):
                    result = runner.invoke(
                        app,
                        [
                            "--json",
                            "lean",
                            "prove",
                            str(Path("input.lean")),
                            "--output",
                            str(Path("output.lean")),
                        ],
                    )
            finally:
                os.chdir(old_cwd)

        assert result.exit_code == ExitCode.SUCCESS
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"]["ARISTOTLE_API_KEY"] == "dotenv-key"


class TestLeanProveCommandExecution:
    """Tests for subprocess execution in lean prove command."""

    def test_successful_prove_returns_ok(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Successful Aristotle execution returns success."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                ],
            )

        assert result.exit_code == ExitCode.SUCCESS
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["input_file"] == str(input_file)
        assert data["data"]["output_file"] == str(output)
        assert data["data"]["aristotle"]["exit_code"] == 0

    def test_aristotle_failure_returns_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Aristotle failure returns error with stderr."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: proof failed"

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                ],
            )

        assert result.exit_code == ExitCode.ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "AristotleError"
        assert "proof failed" in data["error"]["message"]

    def test_timeout_returns_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Timeout returns error with appropriate message."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="aristotle", timeout=10),
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                    "--timeout",
                    "10",
                ],
            )

        assert result.exit_code == ExitCode.ERROR
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "TimeoutError"
        assert "10" in data["error"]["message"]


class TestLeanProveCommandOptions:
    """Tests for CLI options in lean prove command."""

    def test_informal_flag_passed_to_aristotle(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """--informal flag is passed to Aristotle subprocess."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                    "--informal",
                ],
            )

        call_args = mock_run.call_args[0][0]
        assert "--informal" in call_args

    def test_formal_input_context_flag_passed_to_aristotle(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """--formal-input-context flag with path is passed to Aristotle subprocess."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"
        context_file = tmp_path / "context.lean"
        context_file.write_text("-- context file", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                    "--formal-input-context",
                    str(context_file),
                ],
            )

        call_args = mock_run.call_args[0][0]
        assert "--formal-input-context" in call_args
        # Verify the path is also in the command
        assert str(context_file) in call_args

    def test_custom_timeout_passed_to_subprocess(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """--timeout value is passed to subprocess."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                    "--timeout",
                    "300",
                ],
            )

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 300


class TestLeanProveCommandJsonOutput:
    """Tests for JSON output format in lean prove command."""

    def test_json_output_schema_on_success(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Successful prove returns correct JSON schema."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                ],
            )

        data = json.loads(result.stdout)

        # Verify schema matches SPEC-021
        assert data["command"] == "erdos lean prove"
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["input_file"] == str(input_file)
        assert data["data"]["output_file"] == str(output)
        assert "aristotle" in data["data"]
        assert data["data"]["aristotle"]["exit_code"] == 0
        assert data["data"]["aristotle"]["informal"] is False
        assert data["data"]["aristotle"]["formal_input_context"] is None
        assert "timeout_s" in data["data"]["aristotle"]

    def test_stdout_clean_in_json_mode(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """No extra output on stdout in JSON mode."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "lean",
                    "prove",
                    str(input_file),
                    "--output",
                    str(output),
                ],
            )

        # stdout should be valid JSON (pretty-printed is OK)
        data = json.loads(result.stdout)
        # Verify it's a proper CLIOutput structure
        assert "command" in data
        assert "success" in data
        assert data["success"] is True
