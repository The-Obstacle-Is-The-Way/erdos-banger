"""Tests for batch formalize CLIOutput shaping."""

from __future__ import annotations

from erdos.commands.lean.batch_formalize import batch_result_to_cli_output
from erdos.core.batch.models import BatchResult
from erdos.core.exit_codes import ExitCode


def test_batch_formalize_partial_failure_includes_metadata_in_error() -> None:
    """Partial failures should preserve batch metadata in the error payload."""
    result = BatchResult(
        batch_id="batch-123",
        total=3,
        completed_count=2,
        failed_count=1,
        failed_ids=[2],
        duration_ms=10,
        exit_code=ExitCode.SUCCESS,
    )

    output = batch_result_to_cli_output(result, problem_ids=[1, 2, 3], dry_run=False)
    assert output.success is False
    assert output.data is None
    assert output.error is not None
    assert output.error["type"] == "PartialFailure"
    assert output.error["code"] == ExitCode.ERROR
    assert output.error["batch_id"] == "batch-123"
    assert output.error["mode"] == "batch"
    assert output.error["total"] == 3
    assert output.error["failed_count"] == 1
    assert output.error["succeeded_count"] == 2
    assert output.error["failed_ids"] == [2]
    assert output.error["completed"] == 2
    assert output.error["dry_run"] is False
