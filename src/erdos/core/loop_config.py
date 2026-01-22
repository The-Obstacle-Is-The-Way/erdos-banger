"""Backward-compatible shim for loop_config.

This module has been moved to erdos.core.loop.config.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.loop.config import LoopConfig


__all__ = ["LoopConfig"]
