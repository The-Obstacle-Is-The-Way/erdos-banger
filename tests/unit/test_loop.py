"""Tests for loop orchestration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erdos.core.loop import (
    IterationRecord,
    LoopResult,
    LoopStatus,
    apply_patch,
    budget_context,
    build_loop_prompt,
    run_loop,
)
from erdos.core.loop_config import LoopConfig
from erdos.core.models import LeanCheckResult, LeanError, ProblemRecord
from erdos.core.models.problem import ProblemStatus


class TestBudgetContext:
    """Test context budgeting."""

    def test_truncates_large_file(self) -> None:
        lean_file = "x" * 20000  # Exceeds 16KB
        config = LoopConfig(max_file_bytes_prompt=16384)
        result = budget_context(
            lean_file=lean_file,
            errors_text="error",
            problem_text="problem",
            rag_text="",
            config=config,
        )
        assert len(result["lean_file"].encode()) <= config.max_file_bytes_prompt

    def test_truncates_large_errors(self) -> None:
        errors = "x" * 5000  # Exceeds 4KB
        config = LoopConfig()
        result = budget_context(
            lean_file="file",
            errors_text=errors,
            problem_text="problem",
            rag_text="",
            config=config,
        )
        # Errors should be truncated
        assert len(result["errors_text"].encode()) <= 4096

    def test_preserves_small_content(self) -> None:
        config = LoopConfig()
        result = budget_context(
            lean_file="small file",
            errors_text="error",
            problem_text="problem",
            rag_text="rag",
            config=config,
        )
        assert result["lean_file"] == "small file"
        assert result["errors_text"] == "error"
        assert result["problem_text"] == "problem"
        assert result["rag_text"] == "rag"


class TestBuildLoopPrompt:
    """Test prompt building."""

    @pytest.fixture
    def sample_problem(self) -> ProblemRecord:
        return ProblemRecord(
            id=6,
            title="Test Problem",
            statement="Prove something",
            status=ProblemStatus.OPEN,
            tags=["combinatorics"],
        )

    @pytest.fixture
    def sample_check_result(self) -> LeanCheckResult:
        return LeanCheckResult(
            file="Problem006.lean",
            success=False,
            errors=[
                LeanError(
                    file="Problem006.lean",
                    line=10,
                    column=5,
                    message="unknown identifier 'foo'",
                    severity="error",
                )
            ],
            warnings=[],
        )

    def test_prompt_includes_file_content(
        self, sample_problem: ProblemRecord, sample_check_result: LeanCheckResult
    ) -> None:
        prompt = build_loop_prompt(
            file_path=Path("formal/lean/Erdos/Problem006.lean"),
            file_content="theorem foo : True := sorry",
            problem=sample_problem,
            check_result=sample_check_result,
            rag_chunks=[],
            config=LoopConfig(),
        )
        assert "theorem foo : True := sorry" in prompt

    def test_prompt_includes_problem_context(
        self, sample_problem: ProblemRecord, sample_check_result: LeanCheckResult
    ) -> None:
        prompt = build_loop_prompt(
            file_path=Path("formal/lean/Erdos/Problem006.lean"),
            file_content="content",
            problem=sample_problem,
            check_result=sample_check_result,
            rag_chunks=[],
            config=LoopConfig(),
        )
        assert "Test Problem" in prompt
        assert "Prove something" in prompt

    def test_prompt_includes_errors(
        self, sample_problem: ProblemRecord, sample_check_result: LeanCheckResult
    ) -> None:
        prompt = build_loop_prompt(
            file_path=Path("formal/lean/Erdos/Problem006.lean"),
            file_content="content",
            problem=sample_problem,
            check_result=sample_check_result,
            rag_chunks=[],
            config=LoopConfig(),
        )
        assert "unknown identifier 'foo'" in prompt
        assert "line 10" in prompt

    def test_prompt_includes_output_format(
        self, sample_problem: ProblemRecord, sample_check_result: LeanCheckResult
    ) -> None:
        prompt = build_loop_prompt(
            file_path=Path("formal/lean/Erdos/Problem006.lean"),
            file_content="content",
            problem=sample_problem,
            check_result=sample_check_result,
            rag_chunks=[],
            config=LoopConfig(),
        )
        assert "SEARCH" in prompt
        assert "REPLACE" in prompt
        assert "NO_FIX_POSSIBLE" in prompt


class TestApplyPatch:
    """Test patch application."""

    def test_applies_simple_patch(self, tmp_path: Path) -> None:
        # Create a Lean file structure
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem001.lean"
        lean_file.write_text("old content\n", encoding="utf-8")

        new_content = apply_patch(lean_file, "old content", "new content")
        assert new_content == "new content\n"
        assert lean_file.read_text() == "new content\n"

    def test_preserves_surrounding_content(self, tmp_path: Path) -> None:
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem001.lean"
        lean_file.write_text("before\ntarget\nafter\n", encoding="utf-8")

        new_content = apply_patch(lean_file, "target", "replaced")
        assert new_content == "before\nreplaced\nafter\n"


class TestIterationRecord:
    """Test iteration record creation."""

    def test_to_dict(self) -> None:
        record = IterationRecord(
            iteration=1,
            patch_applied=True,
            sorry_before=2,
            sorry_after=1,
            admit_before=0,
            admit_after=0,
            check_success=True,
            error_count=0,
        )
        d = record.to_dict()
        assert d["iteration"] == 1
        assert d["patch_applied"] is True
        assert d["sorry_before"] == 2
        assert d["sorry_after"] == 1


class TestLoopResult:
    """Test loop result creation."""

    def test_success_result(self) -> None:
        result = LoopResult(
            problem_id=6,
            status=LoopStatus.SUCCESS,
            iterations_completed=3,
            iterations_max=10,
            file=Path("formal/lean/Erdos/Problem006.lean"),
            no_apply=False,
            llm_enabled=True,
            llm_command="./llm.sh",
            run_log_path=Path("logs/loop/run_123.jsonl"),
            last_check=LeanCheckResult(
                file="Problem006.lean",
                success=True,
                errors=[],
                warnings=[],
            ),
            iterations=[],
        )
        assert result.status == LoopStatus.SUCCESS
        assert result.problem_id == 6

    def test_to_dict(self) -> None:
        result = LoopResult(
            problem_id=6,
            status=LoopStatus.SUCCESS,
            iterations_completed=3,
            iterations_max=10,
            file=Path("formal/lean/Erdos/Problem006.lean"),
            no_apply=False,
            llm_enabled=True,
            llm_command="./llm.sh",
            run_log_path=Path("logs/loop/run_123.jsonl"),
            last_check=LeanCheckResult(
                file="Problem006.lean",
                success=True,
                errors=[],
                warnings=[],
            ),
            iterations=[],
        )
        d = result.to_dict()
        assert d["problem_id"] == 6
        assert d["status"] == "success"
        assert d["llm"]["enabled"] is True


class TestRunLoop:
    """Test main loop execution."""

    @pytest.fixture
    def mock_lean_runner(self) -> MagicMock:
        runner = MagicMock()
        runner.check.return_value = LeanCheckResult(
            file="Problem006.lean",
            success=True,
            errors=[],
            warnings=[],
        )
        return runner

    @pytest.fixture
    def sample_problem(self) -> ProblemRecord:
        return ProblemRecord(
            id=6,
            title="Test",
            statement="Test",
            status=ProblemStatus.OPEN,
        )

    def test_exits_immediately_if_already_complete(
        self,
        tmp_path: Path,
        mock_lean_runner: MagicMock,
        sample_problem: ProblemRecord,
    ) -> None:
        # Create a file with no sorry
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem006.lean"
        lean_file.write_text("theorem foo : True := by trivial\n", encoding="utf-8")

        config = LoopConfig(max_iterations=10)
        result = run_loop(
            problem=sample_problem,
            file_path=lean_file,
            config=config,
            lean_runner=mock_lean_runner,
            llm_command=None,
            no_apply=True,
        )

        assert result.status == LoopStatus.SUCCESS
        assert result.iterations_completed == 0

    def test_no_llm_exits_with_llm_required(
        self,
        tmp_path: Path,
        mock_lean_runner: MagicMock,
        sample_problem: ProblemRecord,
    ) -> None:
        # Create a file with sorry
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem006.lean"
        lean_file.write_text("theorem foo : True := sorry\n", encoding="utf-8")

        # No LLM command, file has sorry
        config = LoopConfig(max_iterations=10)
        result = run_loop(
            problem=sample_problem,
            file_path=lean_file,
            config=config,
            lean_runner=mock_lean_runner,
            llm_command=None,
            no_apply=True,
        )

        assert result.status == LoopStatus.LLM_REQUIRED
        assert result.iterations_completed == 0

    @patch("erdos.core.loop.runner.execute_llm")
    def test_applies_patch_and_checks(
        self,
        mock_execute_llm: MagicMock,
        tmp_path: Path,
        sample_problem: ProblemRecord,
    ) -> None:
        # Create a file with sorry
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem006.lean"
        lean_file.write_text("theorem foo : True := sorry\n", encoding="utf-8")

        # Mock LLM to return valid patch
        mock_execute_llm.return_value = (
            """<<<<<<< SEARCH
sorry
=======
by trivial
>>>>>>> REPLACE""",
            0,
        )

        # Mock Lean runner to return success after patch
        mock_runner = MagicMock()
        mock_runner.check.return_value = LeanCheckResult(
            file="Problem006.lean",
            success=True,
            errors=[],
            warnings=[],
        )

        config = LoopConfig(max_iterations=3)
        result = run_loop(
            problem=sample_problem,
            file_path=lean_file,
            config=config,
            lean_runner=mock_runner,
            llm_command="./llm.sh",
            no_apply=False,
        )

        assert result.status == LoopStatus.SUCCESS
        assert result.iterations_completed == 1
        assert "by trivial" in lean_file.read_text()

    @patch("erdos.core.loop.runner.execute_llm")
    def test_no_apply_mode_does_not_write(
        self,
        mock_execute_llm: MagicMock,
        tmp_path: Path,
        sample_problem: ProblemRecord,
    ) -> None:
        # Create a file with sorry
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem006.lean"
        original_content = "theorem foo : True := sorry\n"
        lean_file.write_text(original_content, encoding="utf-8")

        # Mock LLM to return valid patch
        mock_execute_llm.return_value = (
            """<<<<<<< SEARCH
sorry
=======
by trivial
>>>>>>> REPLACE""",
            0,
        )

        mock_runner = MagicMock()
        mock_runner.check.return_value = LeanCheckResult(
            file="Problem006.lean",
            success=False,
            errors=[
                LeanError(
                    file="Problem006.lean",
                    line=1,
                    column=1,
                    message="sorry",
                    severity="error",
                )
            ],
            warnings=[],
        )

        config = LoopConfig(max_iterations=1)
        result = run_loop(
            problem=sample_problem,
            file_path=lean_file,
            config=config,
            lean_runner=mock_runner,
            llm_command="./llm.sh",
            no_apply=True,
        )

        # File should not be modified
        assert lean_file.read_text() == original_content
        assert result.no_apply is True

    @patch("erdos.core.loop.runner.execute_llm")
    def test_max_iterations_reached(
        self,
        mock_execute_llm: MagicMock,
        tmp_path: Path,
        sample_problem: ProblemRecord,
    ) -> None:
        # Create a file with sorry
        erdos_dir = tmp_path / "formal" / "lean" / "Erdos"
        erdos_dir.mkdir(parents=True)
        lean_file = erdos_dir / "Problem006.lean"
        lean_file.write_text("theorem foo : True := sorry\n", encoding="utf-8")

        # Mock LLM to always return NO_FIX_POSSIBLE
        mock_execute_llm.return_value = ("NO_FIX_POSSIBLE", 0)

        mock_runner = MagicMock()
        mock_runner.check.return_value = LeanCheckResult(
            file="Problem006.lean",
            success=False,
            errors=[
                LeanError(
                    file="Problem006.lean",
                    line=1,
                    column=1,
                    message="sorry",
                    severity="error",
                )
            ],
            warnings=[],
        )

        config = LoopConfig(max_iterations=2)
        result = run_loop(
            problem=sample_problem,
            file_path=lean_file,
            config=config,
            lean_runner=mock_runner,
            llm_command="./llm.sh",
            no_apply=False,
        )

        # Should hit NO_FIX status on first iteration
        assert result.status == LoopStatus.NO_FIX_POSSIBLE


class TestLoopLoggerSanitization:
    """Test that LoopLogger sanitizes secrets from log data."""

    def test_sanitizes_api_keys_in_prompt(self, tmp_path: Path) -> None:
        """API keys in prompt data should be redacted."""
        import json

        from erdos.core.loop import LoopLogger

        log_path = tmp_path / "test.jsonl"
        logger = LoopLogger(log_path)

        # Prompt containing an API key
        prompt_with_key = "Use this API key: sk-abcdefghij1234567890abcd"
        logger.log_event("llm_prompt", 1, {"prompt": prompt_with_key})
        logger.close()

        logged = json.loads(log_path.read_text().strip())
        assert "sk-abcdefghij1234567890abcd" not in logged["data"]["prompt"]
        assert "[REDACTED]" in logged["data"]["prompt"]

    def test_sanitizes_authorization_headers_in_prompt(self, tmp_path: Path) -> None:
        """Authorization headers in prompt should be redacted."""
        import json

        from erdos.core.loop import LoopLogger

        log_path = tmp_path / "test.jsonl"
        logger = LoopLogger(log_path)

        prompt_with_auth = "Headers: Authorization: Bearer my-secret-token-xyz"
        logger.log_event("llm_prompt", 1, {"prompt": prompt_with_auth})
        logger.close()

        logged = json.loads(log_path.read_text().strip())
        assert "my-secret-token-xyz" not in logged["data"]["prompt"]
        assert "[REDACTED]" in logged["data"]["prompt"]

    def test_sanitizes_response_with_nested_secrets(self, tmp_path: Path) -> None:
        """Nested data structures with secrets should be sanitized."""
        import json

        from erdos.core.loop import LoopLogger

        log_path = tmp_path / "test.jsonl"
        logger = LoopLogger(log_path)

        # Response with nested structure containing secrets
        data = {
            "response": "Use token: sk-test1234567890abcdefghij",
            "exit_code": 0,
            "metadata": {
                "api_key": "secret-key-value",
                "auth_header": "Authorization: secret123",
            },
        }
        logger.log_event("llm_response", 1, data)
        logger.close()

        logged = json.loads(log_path.read_text().strip())
        # Check that api_key is redacted by key name
        assert logged["data"]["metadata"]["api_key"] == "[REDACTED]"
        # Check that response string has API key redacted
        assert "sk-test1234567890abcdefghij" not in logged["data"]["response"]
        # Check that Authorization header is redacted
        assert "secret123" not in logged["data"]["metadata"]["auth_header"]

    def test_preserves_non_secret_data(self, tmp_path: Path) -> None:
        """Non-secret data should be preserved unchanged."""
        import json

        from erdos.core.loop import LoopLogger

        log_path = tmp_path / "test.jsonl"
        logger = LoopLogger(log_path)

        data = {
            "prompt": "Fix the theorem: by trivial",
            "file_path": "/path/to/file.lean",
            "iteration": 3,
        }
        logger.log_event("llm_prompt", 1, data)
        logger.close()

        logged = json.loads(log_path.read_text().strip())
        assert logged["data"]["prompt"] == "Fix the theorem: by trivial"
        assert logged["data"]["file_path"] == "/path/to/file.lean"
        assert logged["data"]["iteration"] == 3
