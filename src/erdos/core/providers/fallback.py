"""Fallback metadata provider chain (SPEC-022)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord
    from erdos.core.ports import MetadataProvider


logger = logging.getLogger(__name__)


class FallbackProvider:
    """MetadataProvider that chains multiple providers with fallback.

    Tries the primary provider first. If it returns None (not found) or raises
    an exception, falls back to the next provider in the chain.

    Example:
        provider = FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider.from_env(),
        )
        # Tries OpenAlex first, falls back to Crossref if OpenAlex fails
    """

    __slots__ = ("_providers",)

    def __init__(self, *providers: MetadataProvider) -> None:
        """Initialize with ordered list of providers.

        Args:
            *providers: Providers in priority order (first is primary).

        Raises:
            ValueError: If no providers are given.
        """
        if not providers:
            raise ValueError("FallbackProvider requires at least one provider")
        self._providers = list(providers)

    @property
    def provider_name(self) -> str:
        """Human-readable name showing the fallback chain."""
        names = [p.provider_name for p in self._providers]
        return f"fallback({' -> '.join(names)})"

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Try each provider in order until one returns a result."""
        for provider in self._providers:
            try:
                result = provider.get_by_doi(doi)
                if result is not None:
                    logger.debug("DOI %s resolved by %s", doi, provider.provider_name)
                    return result
                logger.debug(
                    "DOI %s not found in %s, trying next", doi, provider.provider_name
                )
            except Exception:
                logger.warning(
                    "Provider %s failed for DOI %s, trying next",
                    provider.provider_name,
                    doi,
                    exc_info=True,
                )
        logger.debug("DOI %s not found in any provider", doi)
        return None

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Try each provider in order until one returns a result."""
        for provider in self._providers:
            try:
                result = provider.get_by_arxiv(arxiv_id)
                if result is not None:
                    logger.debug(
                        "arXiv %s resolved by %s", arxiv_id, provider.provider_name
                    )
                    return result
                logger.debug(
                    "arXiv %s not found in %s, trying next",
                    arxiv_id,
                    provider.provider_name,
                )
            except Exception:
                logger.warning(
                    "Provider %s failed for arXiv %s, trying next",
                    provider.provider_name,
                    arxiv_id,
                    exc_info=True,
                )
        logger.debug("arXiv %s not found in any provider", arxiv_id)
        return None

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Use first provider that returns non-empty results."""
        for provider in self._providers:
            try:
                results = provider.search(query, limit=limit)
                if results:
                    logger.debug(
                        "Search '%s' returned %d results from %s",
                        query,
                        len(results),
                        provider.provider_name,
                    )
                    return results
            except Exception:
                logger.warning(
                    "Provider %s failed for search '%s', trying next",
                    provider.provider_name,
                    query,
                    exc_info=True,
                )
        logger.debug("Search '%s' returned no results from any provider", query)
        return []
