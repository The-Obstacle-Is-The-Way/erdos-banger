"""Loop orchestration for iterative Lean proof attempts.

Per spec-012-loop-command.md and spec-012-design.md.

This package provides the loop functionality split into modules:
- result.py: LoopStatus, IterationRecord, LoopResult
- logging.py: LoopLogger, generate_run_id, file_hash
- prompt.py: build_loop_prompt, budget_context
- runner.py: run_loop, apply_patch
"""

# Re-export public API for backward compatibility
from erdos.core.loop.logging import LoopLogger, file_hash, generate_run_id
from erdos.core.loop.prompt import budget_context, build_loop_prompt
from erdos.core.loop.result import IterationRecord, LoopResult, LoopStatus
from erdos.core.loop.runner import apply_patch, run_loop


__all__ = [
    "IterationRecord",
    # Logging
    "LoopLogger",
    "LoopResult",
    # Result types
    "LoopStatus",
    "apply_patch",
    "budget_context",
    # Prompt building
    "build_loop_prompt",
    "file_hash",
    "generate_run_id",
    # Runner
    "run_loop",
]
