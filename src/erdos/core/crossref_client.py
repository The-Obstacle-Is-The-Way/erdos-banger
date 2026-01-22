"""Backward-compatible shim for crossref_client.

This module has been moved to erdos.core.clients.crossref.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.clients.crossref import (
    fetch_crossref_work,
    parse_crossref_work,
)


__all__ = [
    "fetch_crossref_work",
    "parse_crossref_work",
]
