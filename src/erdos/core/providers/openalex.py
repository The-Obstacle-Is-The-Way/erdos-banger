"""OpenAlex metadata provider (SPEC-022)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests

from erdos.core.clients.openalex import OpenAlexClient, OpenAlexConfig


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord


logger = logging.getLogger(__name__)


class OpenAlexProvider:
    """MetadataProvider implementation using OpenAlex API.

    Wraps the existing OpenAlexClient to conform to the MetadataProvider protocol.
    """

    __slots__ = ("_client",)

    def __init__(self, client: OpenAlexClient) -> None:
        """Initialize with an OpenAlexClient instance.

        Prefer using factory methods from_env() or from_config() instead.
        """
        self._client = client

    @classmethod
    def _create_with_client(cls, client: Any) -> OpenAlexProvider:
        """Internal factory for testing with mock clients."""
        instance = object.__new__(cls)
        instance._client = client
        return instance

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return "openalex"

    @classmethod
    def from_env(cls) -> OpenAlexProvider:
        """Create provider with config from environment."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)
        return cls(client)

    @classmethod
    def from_config(cls, config: OpenAlexConfig) -> OpenAlexProvider:
        """Create provider with explicit config."""
        client = OpenAlexClient(config)
        return cls(client)

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work by DOI via OpenAlex."""
        logger.debug("OpenAlex lookup by DOI: %s", doi)
        try:
            return self._client.get_by_doi(doi)
        except requests.HTTPError as e:
            # Normalize "not found" to None so fallback chains can proceed.
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch work by arXiv ID via OpenAlex."""
        logger.debug("OpenAlex lookup by arXiv: %s", arxiv_id)
        try:
            return self._client.get_by_arxiv(arxiv_id)
        except ValueError:
            # OpenAlexClient raises ValueError when the arXiv paper cannot be resolved.
            return None
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works via OpenAlex."""
        logger.debug("OpenAlex search: %s (limit=%d)", query, limit)
        return self._client.search(query, limit=limit)
