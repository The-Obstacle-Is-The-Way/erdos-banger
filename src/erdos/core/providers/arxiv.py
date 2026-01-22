"""ArXiv metadata provider (SPEC-022).

This provider fetches metadata from arXiv's API (not source content).
For downloading arXiv source tarballs, use erdos.core.ingest.arxiv_download.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import defusedxml.ElementTree as ET

from erdos.core.clients.arxiv import fetch_arxiv_atom, parse_arxiv_atom


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord


logger = logging.getLogger(__name__)


class ArxivProvider:
    """MetadataProvider implementation using arXiv API.

    Note: This is for METADATA only (title, authors, abstract).
    Does not download source tarballs - use ingest.arxiv_download for that.

    arXiv is arXiv-only. DOI lookups and search are not supported.
    """

    timeout: float

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize with HTTP timeout."""
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return "arxiv"

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """arXiv does not support DOI lookups."""
        logger.debug("arXiv does not support DOI lookup: %s", doi)
        return None

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch metadata by arXiv ID via arXiv API.

        Raises:
            requests.RequestException: On network errors.
            ValueError: On parsing errors (converted from ParseError).
        """
        logger.debug("arXiv lookup: %s", arxiv_id)
        atom_xml = fetch_arxiv_atom(arxiv_id, timeout=self.timeout)
        try:
            return parse_arxiv_atom(atom_xml)
        except ET.ParseError as e:
            # Convert ParseError to ValueError per MetadataProvider contract
            raise ValueError(
                f"Failed to parse arXiv response for {arxiv_id}: {e}"
            ) from e

    def search(
        self,
        query: str,  # noqa: ARG002
        *,
        limit: int = 25,  # noqa: ARG002
    ) -> list[ReferenceRecord]:
        """arXiv search is not implemented (use OpenAlex for search)."""
        logger.debug("arXiv search not implemented")
        return []
