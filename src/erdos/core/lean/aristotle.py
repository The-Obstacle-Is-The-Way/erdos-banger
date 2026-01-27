"""Harmonic Aristotle integration for Lean theorem proving.

This module provides a subprocess wrapper for the Aristotle CLI,
following the erdos-banger pattern of subprocess boundaries for
external tool integration.

Usage:
    result = run_aristotle_prove_from_file(
        input_file=Path("formal/lean/Erdos/Problem006.lean"),
        output_file=Path("formal/lean/Erdos/Problem006.aristotle.lean"),
    )
    if result.success:
        logger.info("Proof generated at %s", result.output_file)

Configuration:
    - ARISTOTLE_API_KEY: Required by the vendor CLI (must be set in environment)
    - ERDOS_ARISTOTLE_COMMAND: Optional path to aristotle executable (default: "aristotle")
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from erdos.core.config import AppConfig, build_subprocess_env
from erdos.core.constants import LAKE_UPDATE_TIMEOUT


logger = logging.getLogger(__name__)


class AristotleError(Exception):
    """Raised when Aristotle operations fail."""

    def __init__(self, message: str, error_type: str = "Error") -> None:
        """Initialize AristotleError.

        Args:
            message: Error description
            error_type: Type of error (ConfigError, NotFoundError, UsageError, TimeoutError, Error)
        """
        super().__init__(message)
        self.error_type = error_type


@dataclass
class AristotleConfig:
    """Configuration for Aristotle CLI invocation."""

    command: str = "aristotle"
    timeout: int = LAKE_UPDATE_TIMEOUT
    informal: bool = False
    formal_input_context: Path | None = None  # Path to Lean file with formal context


@dataclass
class AristotleResult:
    """Result of an Aristotle prove operation."""

    success: bool
    input_file: Path
    output_file: Path
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timeout: int
    informal: bool
    formal_input_context: Path | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary matching the JSON output schema from SPEC-021.
        """
        return {
            "input_file": str(self.input_file),
            "output_file": str(self.output_file),
            "aristotle": {
                "command": self.command,
                "informal": self.informal,
                "formal_input_context": str(self.formal_input_context)
                if self.formal_input_context
                else None,
                "timeout_s": self.timeout,
                "exit_code": self.exit_code,
            },
        }


def validate_aristotle_config(
    *,
    api_key: str | None = None,
    command: str | None = None,
) -> AristotleConfig:
    """Validate Aristotle configuration.

    Checks that:
    - ARISTOTLE_API_KEY is set and non-empty
    - The aristotle command can be found (via ERDOS_ARISTOTLE_COMMAND or PATH)

    Args:
        api_key: Explicit API key (falls back to ARISTOTLE_API_KEY env var).
        command: Explicit command path (falls back to ERDOS_ARISTOTLE_COMMAND env var).

    Returns:
        AristotleConfig with validated command path

    Raises:
        AristotleError: If configuration is invalid (error_type="ConfigError")
    """
    config: AppConfig | None = None
    if api_key is None or command is None:
        config = AppConfig.from_env()

    # Check for API key (explicit > env var)
    if api_key is not None:
        effective_api_key = api_key.strip()
        if not effective_api_key:
            raise AristotleError(
                "Provided api_key parameter is empty.",
                error_type="ConfigError",
            )
    else:
        if config is None:
            config = AppConfig.from_env()
        effective_api_key = config.aristotle_api_key
        if not effective_api_key:
            raise AristotleError(
                "ARISTOTLE_API_KEY environment variable is not set or empty. "
                "Set it in your environment or in `.env` (auto-loaded by the `erdos` CLI "
                "unless `ERDOS_LOAD_DOTENV` is set to 0/false/no/off).",
                error_type="ConfigError",
            )

    # Get command (explicit > env var > default)
    if command is not None:
        effective_command = command.strip()
        if not effective_command:
            raise AristotleError(
                "Provided command parameter is empty.",
                error_type="ConfigError",
            )
    else:
        if config is None:
            config = AppConfig.from_env()
        effective_command = config.aristotle_command.strip()

    # Resolve command path
    resolved_command = _resolve_command(effective_command)
    if resolved_command is None:
        raise AristotleError(
            f"Aristotle command not found: {effective_command}. "
            "Ensure aristotlelib is installed (pip install aristotlelib) "
            "or set ERDOS_ARISTOTLE_COMMAND to the correct path.",
            error_type="ConfigError",
        )

    return AristotleConfig(command=resolved_command)


def _resolve_command(command: str) -> str | None:
    """Resolve a command to an absolute path.

    Args:
        command: Command name or path

    Returns:
        Absolute path to the command, or None if not found
    """
    cmd_path = Path(command)
    # If it's an absolute path, check if it exists and is executable
    if cmd_path.is_absolute():
        if cmd_path.is_file() and os.access(command, os.X_OK):
            return command
        return None

    # Otherwise, look it up via PATH
    return shutil.which(command)


def build_aristotle_command(
    config: AristotleConfig,
    input_file: Path,
    output_file: Path,
) -> list[str]:
    """Build the command list for subprocess execution.

    Args:
        config: Aristotle configuration
        input_file: Path to input Lean file
        output_file: Path to output Lean file

    Returns:
        Command list suitable for subprocess.run
    """
    cmd = [
        config.command,
        "prove-from-file",
        str(input_file),
        "--output-file",
        str(output_file),
    ]

    if config.informal:
        cmd.append("--informal")

    if config.formal_input_context is not None:
        cmd.extend(["--formal-input-context", str(config.formal_input_context)])

    return cmd


def run_aristotle_prove_from_file(
    input_file: Path,
    output_file: Path,
    *,
    api_key: str | None = None,
    command: str | None = None,
    timeout: int = LAKE_UPDATE_TIMEOUT,
    informal: bool = False,
    formal_input_context: Path | None = None,
) -> AristotleResult:
    """Run Aristotle prove-from-file command.

    Args:
        input_file: Path to the input Lean file
        output_file: Path for the output Lean file (must differ from input)
        api_key: Explicit API key (falls back to ARISTOTLE_API_KEY env var)
        command: Explicit command path (falls back to ERDOS_ARISTOTLE_COMMAND env var)
        timeout: Maximum seconds to wait for completion (default: LAKE_UPDATE_TIMEOUT)
        informal: Pass --informal flag to Aristotle
        formal_input_context: Path to Lean file with formal context (optional)

    Returns:
        AristotleResult with execution details

    Raises:
        AristotleError: On configuration, validation, or timeout errors
    """
    base_config = validate_aristotle_config(api_key=api_key, command=command)
    config = replace(
        base_config,
        timeout=timeout,
        informal=informal,
        formal_input_context=formal_input_context,
    )

    # Validate input file exists
    if not input_file.exists():
        raise AristotleError(
            f"Input file not found: {input_file}",
            error_type="NotFoundError",
        )
    if not input_file.is_file():
        raise AristotleError(
            f"Input file must be a file: {input_file}",
            error_type="UsageError",
        )

    if formal_input_context is not None:
        if not formal_input_context.exists():
            raise AristotleError(
                f"Formal input context not found: {formal_input_context}",
                error_type="NotFoundError",
            )
        if not formal_input_context.is_file():
            raise AristotleError(
                f"Formal input context must be a file: {formal_input_context}",
                error_type="UsageError",
            )

    # Validate output file is different from input
    resolved_input = input_file.resolve()
    resolved_output = output_file.resolve()
    if resolved_input == resolved_output:
        raise AristotleError(
            f"Output file cannot be the same as input file: {input_file}",
            error_type="UsageError",
        )

    # Build and execute command
    cmd = build_aristotle_command(config, input_file, output_file)
    logger.debug("Running Aristotle: %s (timeout=%ds)", " ".join(cmd), config.timeout)

    env: dict[str, str] | None = None
    if api_key is not None:
        env = build_subprocess_env({"ARISTOTLE_API_KEY": api_key.strip()})

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise AristotleError(
            f"Aristotle timed out after {config.timeout} seconds",
            error_type="TimeoutError",
        ) from exc

    success = result.returncode == 0
    logger.debug(
        "Aristotle completed: exit_code=%d, success=%s",
        result.returncode,
        success,
    )

    return AristotleResult(
        success=success,
        input_file=input_file,
        output_file=output_file,
        command=config.command,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        timeout=config.timeout,
        informal=config.informal,
        formal_input_context=config.formal_input_context,
    )
