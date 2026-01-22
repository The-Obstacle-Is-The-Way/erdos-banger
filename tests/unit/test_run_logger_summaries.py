"""Unit tests for run_logger_summaries module."""

from __future__ import annotations

from typing import Any

from erdos.core.run_logger_summaries import (
    SUMMARIZERS,
    get_summarizer,
    register_summarizer,
)


class TestGetSummarizer:
    """Tests for get_summarizer() function."""

    def test_returns_registered_summarizer_for_known_command(self) -> None:
        """get_summarizer should return the registered function for known commands."""
        summarizer = get_summarizer("erdos show")
        assert summarizer is SUMMARIZERS["erdos show"]

    def test_returns_default_for_unknown_command(self) -> None:
        """get_summarizer should return default summarizer for unknown commands."""
        summarizer = get_summarizer("erdos unknown-command")
        # Default summarizer returns {"success": True}
        result = summarizer({})
        assert result == {"success": True}

    def test_all_documented_commands_have_summarizers(self) -> None:
        """All known commands should have registered summarizers."""
        expected_commands = [
            "erdos show",
            "erdos search",
            "erdos lean check",
            "erdos lean formalize",
            "erdos ingest",
            "erdos ask",
        ]
        for cmd in expected_commands:
            assert cmd in SUMMARIZERS, f"Missing summarizer for {cmd}"


class TestDefaultSummarizer:
    """Tests for default summarizer behavior."""

    def test_returns_success_true(self) -> None:
        """Default summarizer should return {success: True}."""
        summarizer = get_summarizer("erdos some-new-command")
        result = summarizer({"any": "data"})
        assert result == {"success": True}

    def test_ignores_input_data(self) -> None:
        """Default summarizer should ignore any input data."""
        summarizer = get_summarizer("erdos nonexistent")
        result = summarizer({"complex": {"nested": "data"}, "list": [1, 2, 3]})
        assert result == {"success": True}


class TestShowSummarizer:
    """Tests for 'erdos show' summarizer."""

    def test_extracts_status(self) -> None:
        """Should extract status from data."""
        summarizer = get_summarizer("erdos show")
        result = summarizer({"id": 6, "status": "open", "prize": 0})
        assert result["status"] == "open"

    def test_detects_prize(self) -> None:
        """Should detect prize presence."""
        summarizer = get_summarizer("erdos show")
        result_with_prize = summarizer({"status": "open", "prize": 1000})
        result_no_prize = summarizer({"status": "open", "prize": 0})
        assert result_with_prize["has_prize"] is True
        assert result_no_prize["has_prize"] is False

    def test_handles_missing_fields(self) -> None:
        """Should handle missing fields gracefully."""
        summarizer = get_summarizer("erdos show")
        result = summarizer({})
        assert result["status"] is None
        assert result["has_prize"] is False


class TestSearchSummarizer:
    """Tests for 'erdos search' summarizer."""

    def test_counts_results(self) -> None:
        """Should count search results."""
        summarizer = get_summarizer("erdos search")
        result = summarizer({"results": [{"id": 1}, {"id": 2}, {"id": 3}]})
        assert result["hit_count"] == 3

    def test_extracts_top_three_ids(self) -> None:
        """Should extract top 3 problem IDs."""
        summarizer = get_summarizer("erdos search")
        result = summarizer(
            {"results": [{"id": 10}, {"id": 20}, {"id": 30}, {"id": 40}]}
        )
        assert result["top_problem_ids"] == [10, 20, 30]

    def test_handles_empty_results(self) -> None:
        """Should handle empty results."""
        summarizer = get_summarizer("erdos search")
        result = summarizer({"results": []})
        assert result["hit_count"] == 0
        assert result["top_problem_ids"] == []

    def test_handles_missing_results_key(self) -> None:
        """Should handle missing results key."""
        summarizer = get_summarizer("erdos search")
        result = summarizer({})
        assert result["hit_count"] == 0
        assert result["top_problem_ids"] == []


class TestLeanCheckSummarizer:
    """Tests for 'erdos lean check' summarizer."""

    def test_extracts_success_status(self) -> None:
        """Should extract success status."""
        summarizer = get_summarizer("erdos lean check")
        result = summarizer({"success": False, "errors": [], "has_sorry": False})
        assert result["success"] is False

    def test_counts_errors(self) -> None:
        """Should count errors."""
        summarizer = get_summarizer("erdos lean check")
        result = summarizer(
            {"errors": [{"line": 1, "msg": "a"}, {"line": 2, "msg": "b"}]}
        )
        assert result["error_count"] == 2

    def test_extracts_has_sorry(self) -> None:
        """Should extract has_sorry flag."""
        summarizer = get_summarizer("erdos lean check")
        result = summarizer({"has_sorry": True, "errors": []})
        assert result["has_sorry"] is True

    def test_defaults_success_to_true(self) -> None:
        """Should default success to True if missing."""
        summarizer = get_summarizer("erdos lean check")
        result = summarizer({"errors": []})
        assert result["success"] is True


class TestLeanFormalizeSummarizer:
    """Tests for 'erdos lean formalize' summarizer."""

    def test_extracts_file_path(self) -> None:
        """Should extract created file path."""
        summarizer = get_summarizer("erdos lean formalize")
        result = summarizer({"file_path": "/path/to/Problem.lean"})
        assert result["file_created"] == "/path/to/Problem.lean"

    def test_handles_missing_path(self) -> None:
        """Should handle missing file path."""
        summarizer = get_summarizer("erdos lean formalize")
        result = summarizer({})
        assert result["file_created"] is None


class TestIngestSummarizer:
    """Tests for 'erdos ingest' summarizer."""

    def test_extracts_references_count(self) -> None:
        """Should extract references processed count."""
        summarizer = get_summarizer("erdos ingest")
        result = summarizer({"references_processed": 5})
        assert result["references_processed"] == 5

    def test_extracts_manifest_path(self) -> None:
        """Should extract manifest path."""
        summarizer = get_summarizer("erdos ingest")
        result = summarizer({"manifest_path": "/path/manifest.json"})
        assert result["manifest_path"] == "/path/manifest.json"

    def test_defaults_references_to_zero(self) -> None:
        """Should default references_processed to 0."""
        summarizer = get_summarizer("erdos ingest")
        result = summarizer({})
        assert result["references_processed"] == 0


class TestAskSummarizer:
    """Tests for 'erdos ask' summarizer."""

    def test_counts_sources(self) -> None:
        """Should count retrieved sources."""
        summarizer = get_summarizer("erdos ask")
        result = summarizer({"sources": [{"id": 1}, {"id": 2}], "answer": ""})
        assert result["sources_retrieved"] == 2

    def test_extracts_llm_enabled(self) -> None:
        """Should extract llm_enabled flag."""
        summarizer = get_summarizer("erdos ask")
        result = summarizer({"llm_enabled": True, "sources": [], "answer": ""})
        assert result["llm_enabled"] is True

    def test_calculates_answer_length(self) -> None:
        """Should calculate answer length."""
        summarizer = get_summarizer("erdos ask")
        result = summarizer({"answer": "This is the answer.", "sources": []})
        assert result["answer_length"] == 19

    def test_handles_missing_fields(self) -> None:
        """Should handle missing fields with defaults."""
        summarizer = get_summarizer("erdos ask")
        result = summarizer({})
        assert result["sources_retrieved"] == 0
        assert result["llm_enabled"] is False
        assert result["answer_length"] == 0


class TestRegisterSummarizer:
    """Tests for register_summarizer() function."""

    def test_registers_new_summarizer(self) -> None:
        """Should register a new summarizer."""

        # Custom summarizer for a hypothetical new command
        def custom_summarizer(data: dict[str, Any]) -> dict[str, Any]:
            return {"custom_field": data.get("value", "default")}

        register_summarizer("erdos custom", custom_summarizer)
        try:
            # Verify it's registered
            summarizer = get_summarizer("erdos custom")
            assert summarizer is custom_summarizer
            result = summarizer({"value": "test"})
            assert result == {"custom_field": "test"}
        finally:
            # Cleanup: remove the test registration even if assertions fail
            SUMMARIZERS.pop("erdos custom", None)

    def test_overwrites_existing_summarizer(self) -> None:
        """Should allow overwriting existing summarizers."""
        original = get_summarizer("erdos show")

        def replacement(_data: dict[str, Any]) -> dict[str, Any]:
            return {"replaced": True}

        register_summarizer("erdos show", replacement)
        try:
            assert get_summarizer("erdos show") is replacement
        finally:
            # Restore original even if assertions fail
            register_summarizer("erdos show", original)
        assert get_summarizer("erdos show") is original


class TestEndToEndIntegration:
    """Integration tests verifying summarizers work with RunLogEntry."""

    def test_run_log_entry_uses_summarizer_registry(self) -> None:
        """RunLogEntry should use the summarizer registry."""
        from erdos.core.models import CLIOutput
        from erdos.core.run_logger import RunLogEntry

        # Create a CLIOutput for search command
        cli_output = CLIOutput.ok(
            command="erdos search",
            data={"results": [{"id": 1}, {"id": 2}], "query": "prime"},
        )
        entry = RunLogEntry.from_cli_output(cli_output=cli_output, args={})

        # Verify the summarizer was applied
        assert entry.result is not None
        assert entry.result["hit_count"] == 2
        assert entry.result["top_problem_ids"] == [1, 2]

    def test_custom_summarizer_works_end_to_end(self) -> None:
        """Custom registered summarizer should be used by RunLogEntry."""
        from erdos.core.models import CLIOutput
        from erdos.core.run_logger import RunLogEntry

        def test_summarizer(summary_data: dict[str, Any]) -> dict[str, Any]:
            return {"test_value": summary_data.get("input", "none")}

        register_summarizer("erdos test-custom", test_summarizer)

        try:
            cli_output = CLIOutput.ok(
                command="erdos test-custom",
                data={"input": "hello"},
            )
            entry = RunLogEntry.from_cli_output(cli_output=cli_output, args={})
            assert entry.result == {"test_value": "hello"}
        finally:
            # Cleanup
            del SUMMARIZERS["erdos test-custom"]
