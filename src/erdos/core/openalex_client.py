"""Backward-compatible shim for openalex_client.

This module has been moved to erdos.core.clients.openalex.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.clients.openalex import (
    OpenAlexClient,
    OpenAlexConfig,
    _map_oa_status,
    extract_arxiv_id,
    extract_arxiv_id_from_work,
    find_pdf_url,
    openalex_to_reference,
    reconstruct_abstract,
)


__all__ = [
    "OpenAlexClient",
    "OpenAlexConfig",
    "_map_oa_status",
    "extract_arxiv_id",
    "extract_arxiv_id_from_work",
    "find_pdf_url",
    "openalex_to_reference",
    "reconstruct_abstract",
]
