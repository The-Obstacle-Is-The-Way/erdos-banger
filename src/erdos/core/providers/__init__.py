"""Metadata provider implementations (SPEC-022).

This package provides MetadataProvider implementations that wrap existing
clients and provide dependency inversion for the ingest layer.

Usage:
    from erdos.core.providers import (
        ArxivProvider,
        OpenAlexProvider,
        CrossrefProvider,
        FallbackProvider,
    )

    # Create a fallback chain
    provider = FallbackProvider(
        OpenAlexProvider.from_env(),
        CrossrefProvider.from_env(),
    )

    # Use via the MetadataProvider protocol
    record = provider.get_by_doi("10.1038/nature12373")
"""

from erdos.core.providers.arxiv import ArxivProvider
from erdos.core.providers.crossref import CrossrefProvider

# FallbackProvider must be imported last to maintain sorted order
from erdos.core.providers.fallback import FallbackProvider
from erdos.core.providers.openalex import OpenAlexProvider


__all__ = [
    "ArxivProvider",
    "CrossrefProvider",
    "FallbackProvider",
    "OpenAlexProvider",
]
