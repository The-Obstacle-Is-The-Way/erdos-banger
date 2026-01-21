"""Application wiring for erdos-banger.

This module is the composition root for CLI execution. It centralizes how
concrete dependencies are created from environment defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from erdos.core.openalex_client import OpenAlexConfig
from erdos.core.problem_loader import ProblemLoader
from erdos.core.providers import CrossrefProvider, FallbackProvider, OpenAlexProvider
from erdos.core.search_index import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import (
        MetadataProvider,
        ProblemRepository,
        SearchIndexProtocol,
    )


@dataclass
class AppContext:
    """Dependency container for CLI commands."""

    problems: ProblemRepository
    index: SearchIndexProtocol | None = None

    @classmethod
    def from_environment(cls) -> AppContext:
        """Create context using environment defaults."""
        return cls(problems=ProblemLoader.from_default())

    def ensure_index(self) -> SearchIndexProtocol:
        """Ensure the search index dependency exists."""
        if self.index is None:
            self.index = SearchIndex.from_default()
        return self.index


def build_metadata_provider(*, mailto: str, timeout: float) -> MetadataProvider:
    """Create the default metadata provider chain (OpenAlex -> Crossref).

    This function exists so call sites can pass CLI-derived configuration (e.g.,
    --mailto, --timeout) without constructing concrete clients inside
    ingest/fetch.py.

    Args:
        mailto: Contact email for API polite pools.
        timeout: HTTP timeout in seconds.

    Returns:
        A MetadataProvider that tries OpenAlex first, then falls back to Crossref.
    """
    primary = OpenAlexProvider.from_config(
        OpenAlexConfig(email=mailto, timeout=timeout)
    )
    fallback = CrossrefProvider(mailto=mailto, timeout=timeout)
    return FallbackProvider(primary, fallback)
