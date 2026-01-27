"""Unit tests for the Aristotle integration module."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from erdos.core.lean import (
    AristotleConfig,
    AristotleError,
    AristotleResult,
    build_aristotle_command,
    run_aristotle_prove_from_file,
    validate_aristotle_config,
)


if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


# =============================================================================
# Configuration Tests
# =============================================================================


class TestAristotleConfig:
    """Tests for AristotleConfig dataclass."""

    def test_config_defaults(self) -> None:
        """Test default configuration values."""
        config = AristotleConfig()
        assert config.command == "aristotle"
        assert config.timeout == 600
        assert config.informal is False
        assert config.formal_input_context is None

    def test_config_custom_values(self, tmp_path: Path) -> None:
        """Test custom configuration values."""
        context_file = tmp_path / "context.lean"
        config = AristotleConfig(
            command="/usr/local/bin/aristotle",
            timeout=300,
            informal=True,
            formal_input_context=context_file,
        )
        assert config.command == "/usr/local/bin/aristotle"
        assert config.timeout == 300
        assert config.informal is True
        assert config.formal_input_context == context_file


class TestValidateAristotleConfig:
    """Tests for validate_aristotle_config function."""

    def test_missing_api_key_raises_error(self, monkeypatch: MonkeyPatch) -> None:
        """Missing ARISTOTLE_API_KEY raises AristotleError."""
        monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
        with pytest.raises(AristotleError) as exc_info:
            validate_aristotle_config()
        assert "ARISTOTLE_API_KEY" in str(exc_info.value)
        assert exc_info.value.error_type == "ConfigError"

    def test_empty_api_key_raises_error(self, monkeypatch: MonkeyPatch) -> None:
        """Empty ARISTOTLE_API_KEY raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "")
        with pytest.raises(AristotleError) as exc_info:
            validate_aristotle_config()
        assert "ARISTOTLE_API_KEY" in str(exc_info.value)
        assert exc_info.value.error_type == "ConfigError"

    def test_empty_api_key_parameter_raises_error(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Empty api_key parameter raises AristotleError blaming the parameter."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "env-key")
        with pytest.raises(AristotleError) as exc_info:
            validate_aristotle_config(api_key=" ")
        assert "api_key" in str(exc_info.value)
        assert "environment variable" not in str(exc_info.value)
        assert exc_info.value.error_type == "ConfigError"

    def test_missing_command_raises_error(self, monkeypatch: MonkeyPatch) -> None:
        """Missing aristotle command on PATH raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        monkeypatch.delenv("ERDOS_ARISTOTLE_COMMAND", raising=False)
        with patch("shutil.which", return_value=None):
            with pytest.raises(AristotleError) as exc_info:
                validate_aristotle_config()
            assert "aristotle" in str(exc_info.value).lower()
            assert exc_info.value.error_type == "ConfigError"

    def test_custom_command_not_found_raises_error(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Custom ERDOS_ARISTOTLE_COMMAND not found raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        monkeypatch.setenv("ERDOS_ARISTOTLE_COMMAND", "/nonexistent/aristotle")
        with patch("shutil.which", return_value=None):
            with pytest.raises(AristotleError) as exc_info:
                validate_aristotle_config()
            assert "/nonexistent/aristotle" in str(exc_info.value)
            assert exc_info.value.error_type == "ConfigError"

    def test_valid_config_returns_config(self, monkeypatch: MonkeyPatch) -> None:
        """Valid configuration returns AristotleConfig."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        monkeypatch.delenv("ERDOS_ARISTOTLE_COMMAND", raising=False)
        with patch("shutil.which", return_value="/usr/bin/aristotle"):
            config = validate_aristotle_config()
        assert config.command == "/usr/bin/aristotle"

    def test_custom_command_resolved_via_which(self, monkeypatch: MonkeyPatch) -> None:
        """Custom command name is resolved via shutil.which."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        monkeypatch.setenv("ERDOS_ARISTOTLE_COMMAND", "custom-aristotle")
        with patch("shutil.which", return_value="/opt/bin/custom-aristotle"):
            config = validate_aristotle_config()
        assert config.command == "/opt/bin/custom-aristotle"

    def test_absolute_path_command_used_directly(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Absolute path command is used directly if executable."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        # Create a mock executable file
        mock_cmd = tmp_path / "aristotle"
        mock_cmd.write_text("#!/bin/bash\necho test", encoding="utf-8")
        mock_cmd.chmod(0o755)
        monkeypatch.setenv("ERDOS_ARISTOTLE_COMMAND", str(mock_cmd))

        config = validate_aristotle_config()
        assert config.command == str(mock_cmd)


# =============================================================================
# Command Building Tests
# =============================================================================


class TestBuildAristotleCommand:
    """Tests for build_aristotle_command function."""

    def test_basic_command(self, tmp_path: Path) -> None:
        """Test basic command without optional flags."""
        input_file = tmp_path / "input.lean"
        output_file = tmp_path / "output.lean"
        config = AristotleConfig(command="/usr/bin/aristotle")

        cmd = build_aristotle_command(config, input_file, output_file)

        assert cmd == [
            "/usr/bin/aristotle",
            "prove-from-file",
            str(input_file),
            "--output-file",
            str(output_file),
        ]

    def test_command_with_informal_flag(self, tmp_path: Path) -> None:
        """Test command with --informal flag."""
        input_file = tmp_path / "input.lean"
        output_file = tmp_path / "output.lean"
        config = AristotleConfig(command="/usr/bin/aristotle", informal=True)

        cmd = build_aristotle_command(config, input_file, output_file)

        assert "--informal" in cmd

    def test_command_with_formal_input_context_flag(self, tmp_path: Path) -> None:
        """Test command with --formal-input-context flag and path argument."""
        input_file = tmp_path / "input.lean"
        output_file = tmp_path / "output.lean"
        context_file = tmp_path / "context.lean"
        config = AristotleConfig(
            command="/usr/bin/aristotle", formal_input_context=context_file
        )

        cmd = build_aristotle_command(config, input_file, output_file)

        assert "--formal-input-context" in cmd
        # Path should follow the flag
        context_idx = cmd.index("--formal-input-context")
        assert cmd[context_idx + 1] == str(context_file)

    def test_command_with_all_flags(self, tmp_path: Path) -> None:
        """Test command with all optional flags."""
        input_file = tmp_path / "input.lean"
        output_file = tmp_path / "output.lean"
        context_file = tmp_path / "context.lean"
        config = AristotleConfig(
            command="/usr/bin/aristotle",
            informal=True,
            formal_input_context=context_file,
        )

        cmd = build_aristotle_command(config, input_file, output_file)

        assert "--informal" in cmd
        assert "--formal-input-context" in cmd
        context_idx = cmd.index("--formal-input-context")
        assert cmd[context_idx + 1] == str(context_file)


# =============================================================================
# Input Validation Tests
# =============================================================================


class TestRunAristotleProveFromFileValidation:
    """Tests for input validation in run_aristotle_prove_from_file."""

    def test_input_file_not_found_raises_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Non-existent input file raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "nonexistent.lean"
        output_file = tmp_path / "output.lean"

        with patch("shutil.which", return_value="/usr/bin/aristotle"):
            with pytest.raises(AristotleError) as exc_info:
                run_aristotle_prove_from_file(input_file, output_file)
            assert exc_info.value.error_type == "NotFoundError"
            assert "not found" in str(exc_info.value).lower()

    def test_output_equals_input_raises_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Output file same as input file raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")

        with patch("shutil.which", return_value="/usr/bin/aristotle"):
            with pytest.raises(AristotleError) as exc_info:
                run_aristotle_prove_from_file(input_file, input_file)
            assert exc_info.value.error_type == "UsageError"
            assert "same" in str(exc_info.value).lower()

    def test_output_resolves_to_input_raises_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Output file resolving to same path as input raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        # Use a path with . components that resolves to the same file
        output_file = tmp_path / "." / "input.lean"

        with patch("shutil.which", return_value="/usr/bin/aristotle"):
            with pytest.raises(AristotleError) as exc_info:
                run_aristotle_prove_from_file(input_file, output_file)
            assert exc_info.value.error_type == "UsageError"


# =============================================================================
# Subprocess Execution Tests
# =============================================================================


class TestRunAristotleProveFromFileExecution:
    """Tests for subprocess execution in run_aristotle_prove_from_file."""

    def test_successful_execution(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Successful Aristotle execution returns AristotleResult."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            result = run_aristotle_prove_from_file(input_file, output_file)

        assert result.success is True
        assert result.exit_code == 0
        assert result.input_file == input_file
        assert result.output_file == output_file
        mock_run.assert_called_once()

    def test_nonzero_exit_code_returns_failure(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Nonzero exit code returns failure result with stderr."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: proof failed"

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = run_aristotle_prove_from_file(input_file, output_file)

        assert result.success is False
        assert result.exit_code == 1
        assert "proof failed" in result.stderr

    def test_timeout_raises_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Subprocess timeout raises AristotleError."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="aristotle", timeout=10),
            ),
            pytest.raises(AristotleError) as exc_info,
        ):
            run_aristotle_prove_from_file(input_file, output_file, timeout=10)
        assert exc_info.value.error_type == "TimeoutError"
        assert "10" in str(exc_info.value)

    def test_custom_timeout_passed_to_subprocess(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Custom timeout is passed to subprocess.run."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            run_aristotle_prove_from_file(input_file, output_file, timeout=300)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 300

    def test_api_key_parameter_is_passed_to_subprocess_env(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """api_key parameter is passed to subprocess env."""
        monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            run_aristotle_prove_from_file(input_file, output_file, api_key="test-key")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"]["ARISTOTLE_API_KEY"] == "test-key"

    def test_informal_flag_passed_to_command(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Informal flag is included in subprocess command."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            run_aristotle_prove_from_file(input_file, output_file, informal=True)

        call_args = mock_run.call_args[0][0]  # First positional arg is the command
        assert "--informal" in call_args

    def test_formal_input_context_flag_passed_to_command(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Formal input context flag and path are included in subprocess command."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "test-key")
        input_file = tmp_path / "input.lean"
        input_file.write_text("-- test", encoding="utf-8")
        output_file = tmp_path / "output.lean"
        context_file = tmp_path / "context.lean"
        context_file.write_text("-- context", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("shutil.which", return_value="/usr/bin/aristotle"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            run_aristotle_prove_from_file(
                input_file, output_file, formal_input_context=context_file
            )

        call_args = mock_run.call_args[0][0]
        assert "--formal-input-context" in call_args
        context_idx = call_args.index("--formal-input-context")
        assert call_args[context_idx + 1] == str(context_file)


# =============================================================================
# AristotleResult Tests
# =============================================================================


class TestAristotleResult:
    """Tests for AristotleResult dataclass."""

    def test_result_to_dict(self, tmp_path: Path) -> None:
        """Test conversion to dictionary for JSON serialization."""
        result = AristotleResult(
            success=True,
            input_file=tmp_path / "input.lean",
            output_file=tmp_path / "output.lean",
            command="aristotle",
            exit_code=0,
            stdout="Success",
            stderr="",
            timeout=600,
            informal=False,
            formal_input_context=None,
        )

        data = result.to_dict()

        assert data["input_file"] == str(tmp_path / "input.lean")
        assert data["output_file"] == str(tmp_path / "output.lean")
        assert data["aristotle"]["command"] == "aristotle"
        assert data["aristotle"]["exit_code"] == 0
        assert data["aristotle"]["timeout_s"] == 600
        assert data["aristotle"]["informal"] is False
        assert data["aristotle"]["formal_input_context"] is None

    def test_result_to_dict_with_flags(self, tmp_path: Path) -> None:
        """Test result dict includes flag values."""
        context_file = tmp_path / "context.lean"
        result = AristotleResult(
            success=False,
            input_file=tmp_path / "input.lean",
            output_file=tmp_path / "output.lean",
            command="aristotle",
            exit_code=1,
            stdout="",
            stderr="Error",
            timeout=300,
            informal=True,
            formal_input_context=context_file,
        )

        data = result.to_dict()

        assert data["aristotle"]["informal"] is True
        assert data["aristotle"]["formal_input_context"] == str(context_file)
        assert data["aristotle"]["timeout_s"] == 300


# =============================================================================
# Error Class Tests
# =============================================================================


class TestAristotleError:
    """Tests for AristotleError exception class."""

    def test_error_with_type(self) -> None:
        """Test error with error_type attribute."""
        error = AristotleError("Test error", error_type="ConfigError")
        assert str(error) == "Test error"
        assert error.error_type == "ConfigError"

    def test_error_default_type(self) -> None:
        """Test error with default error_type."""
        error = AristotleError("Test error")
        assert error.error_type == "Error"
