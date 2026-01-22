"""Backward-compatible shim for loop_verifier.

This module has been moved to erdos.core.loop.verifier.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.loop.verifier import (
    LoopExitCondition,
    LoopVerification,
    count_admits,
    count_sorries,
)


__all__ = [
    "LoopExitCondition",
    "LoopVerification",
    "count_admits",
    "count_sorries",
]
