"""Integration tests for Typer validation on common CLI options."""

from __future__ import annotations

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _combined_output(result: object) -> str:
    stdout = getattr(result, "stdout", "")
    stderr = getattr(result, "stderr", "")
    output = f"{stdout}{stderr}"
    if output:
        return output
    return getattr(result, "output", "")


def test_search_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(app, ["search", "test", "--limit", "0"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_search_limit_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(app, ["search", "test", "--limit", "-1"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_ask_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(app, ["ask", "6", "test", "--no-llm", "--limit", "0"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_ask_limit_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(app, ["ask", "6", "test", "--no-llm", "--limit", "-1"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_refs_s2_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(
        app, ["refs", "s2", "citations", "10.1234/test", "--limit", "0"]
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_refs_s2_limit_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(
        app, ["refs", "s2", "citations", "10.1234/test", "--limit", "-1"]
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_refs_s2_cited_by_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(
        app, ["refs", "s2", "cited-by", "10.1234/test", "--limit", "0"]
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_refs_s2_references_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(
        app, ["refs", "s2", "references", "10.1234/test", "--limit", "0"]
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_refs_zbmath_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(app, ["refs", "zbmath", "--msc", "11B05", "--limit", "0"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_refs_zbmath_year_range_rejects_invalid_order(strip_ansi) -> None:
    result = runner.invoke(
        app,
        [
            "refs",
            "zbmath",
            "--msc",
            "11B05",
            "--year-min",
            "2020",
            "--year-max",
            "2010",
            "--limit",
            "1",
        ],
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "--year-min must be <= --year-max" in output
    assert "Traceback" not in output


def test_search_msc_year_range_rejects_invalid_order(strip_ansi) -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "--msc",
            "11B05",
            "--year-min",
            "2020",
            "--year-max",
            "2010",
            "--limit",
            "1",
        ],
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "--year-min must be <= --year-max" in output
    assert "Traceback" not in output


def test_global_log_level_rejects_invalid_value(strip_ansi) -> None:
    result = runner.invoke(app, ["--log-level", "INVALID", "list", "--limit", "1"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--log-level'" in output
    assert "Traceback" not in output


def test_ingest_batch_limit_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(app, ["ingest", "--all", "--limit", "-5", "--dry-run"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_ingest_batch_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(app, ["ingest", "--all", "--limit", "0", "--dry-run"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_ingest_skip_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(app, ["ingest", "--all", "--skip", "-1", "--dry-run"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--skip'" in output
    assert "Traceback" not in output


def test_ingest_delay_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(app, ["ingest", "1", "--delay", "-1"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--delay'" in output
    assert "Traceback" not in output


def test_ingest_timeout_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(app, ["ingest", "1", "--timeout", "0"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--timeout'" in output
    assert "Traceback" not in output


def test_lean_formalize_batch_limit_rejects_negative(strip_ansi) -> None:
    result = runner.invoke(
        app, ["lean", "formalize", "--all", "--limit", "-1", "--dry-run"]
    )
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output


def test_lean_formalize_batch_limit_rejects_zero(strip_ansi) -> None:
    result = runner.invoke(app, ["lean", "formalize", "--all", "--limit", "0"])
    assert result.exit_code == 2
    output = strip_ansi(_combined_output(result))
    assert "Invalid value for '--limit'" in output
    assert "Traceback" not in output
