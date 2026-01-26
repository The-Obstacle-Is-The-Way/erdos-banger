"""Shared helpers for CLI command modules."""

from __future__ import annotations

from erdos.commands.presenter import err_console
from erdos.core.models import ProblemStatus


PROBLEM_STATUS_CHOICES = [status.value for status in ProblemStatus]


def print_if_human(message: str, *, json_output: bool, style: str = "dim") -> None:
    """Print a message only when not in JSON mode."""
    if json_output:
        return
    err_console.print(f"[{style}]{message}[/{style}]")
