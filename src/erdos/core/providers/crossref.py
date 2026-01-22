"""Crossref metadata provider (SPEC-022)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests

from erdos.core.clients.crossref import fetch_crossref_work, parse_crossref_work


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord


logger = logging.getLogger(__name__)


@dataclass
class CrossrefProvider:
    """MetadataProvider implementation using Crossref API.

    Note: Crossref is DOI-only. arXiv lookups and search are not supported.
    """

    mailto: str
    timeout: float = 30.0

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return "crossref"

    @classmethod
    def from_env(cls) -> CrossrefProvider:
        """Create provider using ERDOS_MAILTO for Crossref's polite pool."""
        # Keep a stable default for local dev, but real usage should set ERDOS_MAILTO.
        mailto = os.environ.get("ERDOS_MAILTO", "erdos-banger@example.com")
        return cls(mailto=mailto)

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work by DOI via Crossref."""
        logger.debug("Crossref lookup by DOI: %s", doi)
        try:
            raw = fetch_crossref_work(doi, mailto=self.mailto, timeout=self.timeout)
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise
        return parse_crossref_work(raw, doi=doi)

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Crossref does not support arXiv ID lookups."""
        logger.debug("Crossref does not support arXiv lookup: %s", arxiv_id)
        return None

    def search(
        self,
        query: str,  # noqa: ARG002
        *,
        limit: int = 25,  # noqa: ARG002
    ) -> list[ReferenceRecord]:
        """Crossref search is not implemented (use OpenAlex for search)."""
        logger.debug("Crossref search not implemented")
        return []
