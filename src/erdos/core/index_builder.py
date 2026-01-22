"""Backward-compatible shim for index_builder.

This module has been moved to erdos.core.search.index_builder.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.search.index_builder import build_index


__all__ = ["build_index"]
