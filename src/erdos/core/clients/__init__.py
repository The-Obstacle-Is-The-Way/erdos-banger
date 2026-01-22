"""HTTP client adapters for external APIs.

This package contains clients for external academic metadata APIs:
- arxiv.py: arXiv export API (Atom XML)
- crossref.py: Crossref REST API
- openalex.py: OpenAlex REST API
"""

from erdos.core.clients.arxiv import (
    ARXIV_USER_AGENT,
    ATOM_NS,
    extract_arxiv_text,
    fetch_arxiv_atom,
    parse_arxiv_atom,
)
from erdos.core.clients.crossref import (
    fetch_crossref_work,
    parse_crossref_work,
)
from erdos.core.clients.openalex import (
    OpenAlexClient,
    OpenAlexConfig,
    reconstruct_abstract,
)


__all__ = [
    "ARXIV_USER_AGENT",
    "ATOM_NS",
    "OpenAlexClient",
    "OpenAlexConfig",
    "extract_arxiv_text",
    "fetch_arxiv_atom",
    "fetch_crossref_work",
    "parse_arxiv_atom",
    "parse_crossref_work",
    "reconstruct_abstract",
]
