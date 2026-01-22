"""Loop orchestration for iterative Lean proof attempts.

Per spec-012-loop-command.md and spec-012-design.md.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, PackageLoader, select_autoescape

from erdos.core.ask.llm import execute_llm
from erdos.core.loop_verifier import (
    LoopExitCondition,
    LoopVerification,
    count_admits,
    count_sorries,
)
from erdos.core.patch_validator import PatchStatus, validate_patch


if TYPE_CHECKING:
    from erdos.core.lean_runner import LeanRunner
    from erdos.core.loop_config import LoopConfig
    from erdos.core.models import LeanCheckResult, LeanError, ProblemRecord


logger = logging.getLogger(__name__)


# Template environment for loop prompts
_env = Environment(
    loader=PackageLoader("erdos", "templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


class LoopStatus(str, Enum):
    """Status of a loop execution."""

    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"
    NO_PROGRESS = "no_progress"
    NO_FIX_POSSIBLE = "no_fix_possible"
    REGRESSION = "regression"
    LLM_REQUIRED = "llm_required"
    ERROR = "error"


@dataclass
class IterationRecord:
    """Record of a single loop iteration."""

    iteration: int
    patch_applied: bool
    sorry_before: int = 0
    sorry_after: int = 0
    admit_before: int = 0
    admit_after: int = 0
    check_success: bool = False
    error_count: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "iteration": self.iteration,
            "patch_applied": self.patch_applied,
            "sorry_before": self.sorry_before,
            "sorry_after": self.sorry_after,
            "admit_before": self.admit_before,
            "admit_after": self.admit_after,
            "check_success": self.check_success,
            "error_count": self.error_count,
            "reason": self.reason if self.reason else None,
        }


@dataclass
class LoopResult:
    """Result of a loop execution."""

    problem_id: int
    status: LoopStatus
    iterations_completed: int
    iterations_max: int
    file: Path
    no_apply: bool
    llm_enabled: bool
    llm_command: str | None
    run_log_path: Path | None
    last_check: LeanCheckResult | None
    iterations: list[IterationRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        last_check_dict = None
        if self.last_check is not None:
            last_check_dict = {
                "success": self.last_check.success,
                "error_count": len(self.last_check.errors),
                "has_sorry": False,  # Populated from file content
                "has_admit": False,
            }

        return {
            "problem_id": self.problem_id,
            "status": self.status.value,
            "iterations_completed": self.iterations_completed,
            "iterations_max": self.iterations_max,
            "file": str(self.file),
            "no_apply": self.no_apply,
            "llm": {
                "enabled": self.llm_enabled,
                "command": self.llm_command,
            },
            "run_log_path": str(self.run_log_path) if self.run_log_path else None,
            "last_check": last_check_dict,
            "iterations": [it.to_dict() for it in self.iterations],
        }


def _truncate_bytes(text: str, max_bytes: int) -> str:
    """Truncate text to fit within max_bytes (UTF-8)."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    # Truncate and add ellipsis
    truncated = encoded[: max_bytes - 3]
    # Decode safely (may cut off mid-character)
    return truncated.decode("utf-8", errors="ignore") + "..."


def budget_context(
    *,
    lean_file: str,
    errors_text: str,
    problem_text: str,
    rag_text: str,
    config: LoopConfig,
) -> dict[str, str]:
    """Truncate context components to fit within byte budget.

    Per spec-012-design.md D2: Byte-Based Budget with Hard Caps.

    Priority: lean_file > errors > problem > rag

    Args:
        lean_file: Content of the Lean file
        errors_text: Formatted error messages
        problem_text: Problem statement text
        rag_text: Retrieved context from RAG
        config: Loop configuration with budget limits

    Returns:
        Dictionary with truncated content
    """
    return {
        "lean_file": _truncate_bytes(lean_file, config.max_file_bytes_prompt),
        "errors_text": _truncate_bytes(errors_text, 4096),
        "problem_text": _truncate_bytes(problem_text, 2048),
        "rag_text": _truncate_bytes(rag_text, 8192),
    }


def _format_errors(errors: list[LeanError]) -> str:
    """Format errors for the prompt."""
    lines = []
    for i, error in enumerate(errors, 1):
        lines.append(f"### Error {i} at line {error.line}")
        lines.append(f"```\n{error.message}\n```")
    return "\n".join(lines)


def build_loop_prompt(
    *,
    file_path: Path,
    file_content: str,
    problem: ProblemRecord,
    check_result: LeanCheckResult,
    rag_chunks: list[Any],
    config: LoopConfig,
) -> str:
    """Build the prompt for the LLM.

    Uses the loop_prompt.j2 template for deterministic output.

    Args:
        file_path: Path to the Lean file
        file_content: Content of the Lean file
        problem: Problem record
        check_result: Result of Lean compilation check
        rag_chunks: Retrieved context chunks
        config: Loop configuration

    Returns:
        Formatted prompt string
    """
    # Budget the context
    budgeted = budget_context(
        lean_file=file_content,
        errors_text=_format_errors(check_result.errors),
        problem_text=problem.statement or "",
        rag_text="",  # RAG chunks handled separately
        config=config,
    )

    template = _env.get_template("loop_prompt.j2")
    return template.render(
        file_path=str(file_path),
        file_content=budgeted["lean_file"],
        compilation_success=check_result.success,
        error_count=len(check_result.errors),
        errors=check_result.errors,
        problem=problem,
        rag_chunks=rag_chunks,
    )


def apply_patch(file_path: Path, search_text: str, replace_text: str) -> str:
    """Apply a patch to a file.

    Args:
        file_path: Path to the file
        search_text: Text to find and replace
        replace_text: Replacement text

    Returns:
        New file content after patch
    """
    content = file_path.read_text(encoding="utf-8")
    new_content = content.replace(search_text, replace_text, 1)
    file_path.write_text(new_content, encoding="utf-8")
    return new_content


def _generate_run_id() -> str:
    """Generate a unique run ID."""
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_suffix = secrets.token_hex(3)  # 6 hex chars, cryptographically secure
    return f"run_{timestamp}_{random_suffix}"


def _file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file content for logging/cache purposes."""
    content = path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


class LoopLogger:
    """JSON Lines logger for loop iterations."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = log_path.open("a", encoding="utf-8")

    def log_event(self, event: str, iteration: int, data: dict[str, Any]) -> None:
        """Log an event to the run log."""
        entry = {
            "schema_version": 1,
            "iteration": iteration,
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        self._file.close()


def run_loop(  # noqa: PLR0911, PLR0912, PLR0915
    *,
    problem: ProblemRecord,
    file_path: Path,
    config: LoopConfig,
    lean_runner: LeanRunner,
    llm_command: str | None,
    no_apply: bool = False,
    rag_chunks: list[Any] | None = None,
) -> LoopResult:
    """Run the iterative proof loop.

    Per spec-012-loop-command.md execution model.

    Args:
        problem: Problem record
        file_path: Path to the Lean file
        config: Loop configuration
        lean_runner: Lean runner instance
        llm_command: External LLM command (or None to disable)
        no_apply: If True, propose changes only (don't write)
        rag_chunks: Retrieved context chunks (optional)

    Returns:
        LoopResult with execution details
    """
    if rag_chunks is None:
        rag_chunks = []

    # Set up logging
    run_id = _generate_run_id()
    log_dir = Path("logs/loop")
    log_path = log_dir / f"{run_id}.jsonl"
    loop_logger = LoopLogger(log_path)

    iterations: list[IterationRecord] = []
    stall_count = 0
    last_check: LeanCheckResult | None = None

    try:
        # Initial check
        file_content = file_path.read_text(encoding="utf-8")
        initial_sorries = count_sorries(file_content)
        initial_admits = count_admits(file_content)
        _ = len(file_content.encode("utf-8"))  # initial size (for future use)

        # Check if already complete
        if initial_sorries == 0 and initial_admits == 0:
            last_check = lean_runner.check(
                file_path, timeout=config.lean_timeout_seconds
            )
            if last_check.success:
                return LoopResult(
                    problem_id=problem.id,
                    status=LoopStatus.SUCCESS,
                    iterations_completed=0,
                    iterations_max=config.max_iterations,
                    file=file_path,
                    no_apply=no_apply,
                    llm_enabled=llm_command is not None,
                    llm_command=llm_command,
                    run_log_path=log_path,
                    last_check=last_check,
                    iterations=[],
                )

        # LLM required but not configured
        if llm_command is None:
            return LoopResult(
                problem_id=problem.id,
                status=LoopStatus.LLM_REQUIRED,
                iterations_completed=0,
                iterations_max=config.max_iterations,
                file=file_path,
                no_apply=no_apply,
                llm_enabled=False,
                llm_command=None,
                run_log_path=log_path,
                last_check=None,
                iterations=[],
            )

        # Main loop
        for i in range(1, config.max_iterations + 1):
            logger.info("Loop iteration %d/%d", i, config.max_iterations)

            # Read current state
            file_content = file_path.read_text(encoding="utf-8")
            sorries_before = count_sorries(file_content)
            admits_before = count_admits(file_content)
            size_before = len(file_content.encode("utf-8"))

            # Run Lean check
            last_check = lean_runner.check(
                file_path, timeout=config.lean_timeout_seconds
            )
            loop_logger.log_event(
                "lean_check",
                i,
                {
                    "success": last_check.success,
                    "error_count": len(last_check.errors),
                    "file_hash": _file_hash(file_path),
                },
            )

            # Check if already complete
            if last_check.success and sorries_before == 0 and admits_before == 0:
                return LoopResult(
                    problem_id=problem.id,
                    status=LoopStatus.SUCCESS,
                    iterations_completed=i - 1,
                    iterations_max=config.max_iterations,
                    file=file_path,
                    no_apply=no_apply,
                    llm_enabled=True,
                    llm_command=llm_command,
                    run_log_path=log_path,
                    last_check=last_check,
                    iterations=iterations,
                )

            # Build prompt
            prompt = build_loop_prompt(
                file_path=file_path,
                file_content=file_content,
                problem=problem,
                check_result=last_check,
                rag_chunks=rag_chunks,
                config=config,
            )
            loop_logger.log_event("llm_prompt", i, {"prompt": prompt})

            # Call LLM
            try:
                response, exit_code = execute_llm(llm_command, prompt)
            except Exception as e:
                logger.error("LLM execution failed: %s", e)
                return LoopResult(
                    problem_id=problem.id,
                    status=LoopStatus.ERROR,
                    iterations_completed=i,
                    iterations_max=config.max_iterations,
                    file=file_path,
                    no_apply=no_apply,
                    llm_enabled=True,
                    llm_command=llm_command,
                    run_log_path=log_path,
                    last_check=last_check,
                    iterations=iterations,
                )

            loop_logger.log_event(
                "llm_response",
                i,
                {
                    "response": response,
                    "exit_code": exit_code,
                },
            )

            if exit_code != 0:
                logger.warning("LLM exited with code %d", exit_code)
                stall_count += 1
                iterations.append(
                    IterationRecord(
                        iteration=i,
                        patch_applied=False,
                        sorry_before=sorries_before,
                        sorry_after=sorries_before,
                        admit_before=admits_before,
                        admit_after=admits_before,
                        check_success=last_check.success,
                        error_count=len(last_check.errors),
                        reason="llm_error",
                    )
                )
                if stall_count >= config.stall_threshold:
                    return LoopResult(
                        problem_id=problem.id,
                        status=LoopStatus.NO_PROGRESS,
                        iterations_completed=i,
                        iterations_max=config.max_iterations,
                        file=file_path,
                        no_apply=no_apply,
                        llm_enabled=True,
                        llm_command=llm_command,
                        run_log_path=log_path,
                        last_check=last_check,
                        iterations=iterations,
                    )
                continue

            # Validate patch
            patch_result = validate_patch(response, file_path, config)

            if patch_result.status == PatchStatus.NO_FIX:
                loop_logger.log_event(
                    "patch_rejected", i, {"reason": "no_fix_possible"}
                )
                return LoopResult(
                    problem_id=problem.id,
                    status=LoopStatus.NO_FIX_POSSIBLE,
                    iterations_completed=i,
                    iterations_max=config.max_iterations,
                    file=file_path,
                    no_apply=no_apply,
                    llm_enabled=True,
                    llm_command=llm_command,
                    run_log_path=log_path,
                    last_check=last_check,
                    iterations=iterations,
                )

            if patch_result.status == PatchStatus.REJECTED:
                logger.warning("Patch rejected: %s", patch_result.rejection_reason)
                loop_logger.log_event(
                    "patch_rejected",
                    i,
                    {
                        "reason": patch_result.rejection_reason,
                    },
                )
                stall_count += 1
                iterations.append(
                    IterationRecord(
                        iteration=i,
                        patch_applied=False,
                        sorry_before=sorries_before,
                        sorry_after=sorries_before,
                        admit_before=admits_before,
                        admit_after=admits_before,
                        check_success=last_check.success,
                        error_count=len(last_check.errors),
                        reason=patch_result.rejection_reason,
                    )
                )
                if stall_count >= config.stall_threshold:
                    return LoopResult(
                        problem_id=problem.id,
                        status=LoopStatus.NO_PROGRESS,
                        iterations_completed=i,
                        iterations_max=config.max_iterations,
                        file=file_path,
                        no_apply=no_apply,
                        llm_enabled=True,
                        llm_command=llm_command,
                        run_log_path=log_path,
                        last_check=last_check,
                        iterations=iterations,
                    )
                continue

            # Apply patch (unless --no-apply)
            # We only reach here when patch_result.status == PatchStatus.OK
            # which guarantees search_text and replace_text are not None
            search_text = patch_result.search_text
            replace_text = patch_result.replace_text
            if search_text is None or replace_text is None:
                # Should never happen due to PatchStatus.OK contract
                continue

            if no_apply:
                loop_logger.log_event("patch_skipped", i, {"reason": "no_apply"})
                iterations.append(
                    IterationRecord(
                        iteration=i,
                        patch_applied=False,
                        sorry_before=sorries_before,
                        sorry_after=sorries_before,
                        admit_before=admits_before,
                        admit_after=admits_before,
                        check_success=last_check.success,
                        error_count=len(last_check.errors),
                        reason="no_apply",
                    )
                )
                # In no-apply mode, exit after first valid proposal
                return LoopResult(
                    problem_id=problem.id,
                    status=LoopStatus.NO_PROGRESS,
                    iterations_completed=i,
                    iterations_max=config.max_iterations,
                    file=file_path,
                    no_apply=no_apply,
                    llm_enabled=True,
                    llm_command=llm_command,
                    run_log_path=log_path,
                    last_check=last_check,
                    iterations=iterations,
                )

            # Apply the patch
            hash_before = _file_hash(file_path)
            new_content = apply_patch(
                file_path,
                search_text,
                replace_text,
            )
            hash_after = _file_hash(file_path)

            loop_logger.log_event(
                "patch_applied",
                i,
                {
                    "hash_before": hash_before,
                    "hash_after": hash_after,
                },
            )

            # Verify the patch
            sorries_after = count_sorries(new_content)
            admits_after = count_admits(new_content)
            size_after = len(new_content.encode("utf-8"))

            verification = LoopVerification(
                compiles=True,  # Will be checked next iteration
                sorry_count_before=sorries_before,
                sorry_count_after=sorries_after,
                admit_count_before=admits_before,
                admit_count_after=admits_after,
                file_size_before=size_before,
                file_size_after=size_after,
                min_file_size_ratio=config.min_file_size_ratio,
            )

            if verification.exit_condition == LoopExitCondition.REGRESSION:
                return LoopResult(
                    problem_id=problem.id,
                    status=LoopStatus.REGRESSION,
                    iterations_completed=i,
                    iterations_max=config.max_iterations,
                    file=file_path,
                    no_apply=no_apply,
                    llm_enabled=True,
                    llm_command=llm_command,
                    run_log_path=log_path,
                    last_check=last_check,
                    iterations=iterations,
                )

            # Record the iteration
            iterations.append(
                IterationRecord(
                    iteration=i,
                    patch_applied=True,
                    sorry_before=sorries_before,
                    sorry_after=sorries_after,
                    admit_before=admits_before,
                    admit_after=admits_after,
                    check_success=True,  # Will be updated next iteration
                    error_count=0,
                )
            )

            # Reset stall count on progress
            if verification.is_progress:
                stall_count = 0
            else:
                stall_count += 1

            # Check for completion
            if sorries_after == 0 and admits_after == 0:
                # Do a final check
                final_check = lean_runner.check(
                    file_path, timeout=config.lean_timeout_seconds
                )
                if final_check.success:
                    return LoopResult(
                        problem_id=problem.id,
                        status=LoopStatus.SUCCESS,
                        iterations_completed=i,
                        iterations_max=config.max_iterations,
                        file=file_path,
                        no_apply=no_apply,
                        llm_enabled=True,
                        llm_command=llm_command,
                        run_log_path=log_path,
                        last_check=final_check,
                        iterations=iterations,
                    )

        # Max iterations reached
        return LoopResult(
            problem_id=problem.id,
            status=LoopStatus.MAX_ITERATIONS,
            iterations_completed=config.max_iterations,
            iterations_max=config.max_iterations,
            file=file_path,
            no_apply=no_apply,
            llm_enabled=True,
            llm_command=llm_command,
            run_log_path=log_path,
            last_check=last_check,
            iterations=iterations,
        )

    finally:
        loop_logger.close()
