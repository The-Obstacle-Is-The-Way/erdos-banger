"""Configuration for the loop command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LoopConfig:
    """Configuration for the iterative Lean proof loop.

    All values have sensible defaults per spec-012-design.md.
    The config is immutable (frozen) to prevent accidental modification.
    """

    max_iterations: int = 10
    """Maximum number of propose-check iterations."""

    max_patch_lines: int = 50
    """Reject patches larger than this many lines."""

    max_patch_bytes: int = 8192
    """Reject patches larger than this many bytes."""

    max_file_bytes_prompt: int = 16384
    """Maximum bytes of Lean file content to include in prompt."""

    max_prompt_bytes: int = 32768
    """Total maximum bytes for the LLM prompt."""

    stall_threshold: int = 3
    """Abort after this many consecutive no-progress iterations."""

    lean_timeout_seconds: int = 120
    """Timeout for Lean compilation checks."""

    min_file_size_ratio: float = 0.8
    """Abort if file shrinks below this ratio (prevents deletion attacks)."""

    allow_sorry_increase: int = 0
    """Allow a patch to increase sorry count by up to this amount (default: reject)."""

    rag_limit: int = 5
    """Maximum number of RAG context chunks to include in prompt."""

    @classmethod
    def from_cli(cls, **overrides: Any) -> LoopConfig:
        """Create config from CLI options, filtering out None values.

        Args:
            **overrides: CLI option values (None values are ignored)

        Returns:
            LoopConfig with specified overrides applied
        """
        filtered = {k: v for k, v in overrides.items() if v is not None}
        return cls(**filtered)
