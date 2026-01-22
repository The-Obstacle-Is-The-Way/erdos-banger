"""Backward-compatible shim for arxiv_client.

This module has been moved to erdos.core.clients.arxiv.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.clients.arxiv import (
    ARXIV_USER_AGENT,
    ATOM_NS,
    extract_arxiv_text,
    fetch_arxiv_atom,
    parse_arxiv_atom,
)


__all__ = [
    "ARXIV_USER_AGENT",
    "ATOM_NS",
    "extract_arxiv_text",
    "fetch_arxiv_atom",
    "parse_arxiv_atom",
]
