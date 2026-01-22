"""Unit tests for ingest command CLI helpers (printer functions).

Note: Core orchestration tests are in test_ingest_app.py.
This file tests CLI-specific helpers in commands/ingest.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import pytest

from erdos.commands.ingest import (
    _create_progress_callback,
    _show_progress_message,
)


def test_show_progress_message_in_json_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _show_progress_message is silent in JSON mode."""
    _show_progress_message(6, json_output=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_show_progress_message_in_human_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _show_progress_message shows output in human mode."""
    _show_progress_message(6, json_output=False)

    captured = capsys.readouterr()
    assert "Problem 6" in captured.err


def test_show_progress_message_batch_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _show_progress_message for batch mode (problem_id=None)."""
    _show_progress_message(None, json_output=False)

    captured = capsys.readouterr()
    assert "batch ingest" in captured.err.lower()


def test_create_progress_callback_json_mode() -> None:
    """Test _create_progress_callback returns None callback in JSON mode."""
    _, callback = _create_progress_callback(json_mode=True)

    assert callback is None


def test_create_progress_callback_human_mode() -> None:
    """Test _create_progress_callback returns callable in human mode."""
    _, callback = _create_progress_callback(json_mode=False)

    assert callable(callback)
