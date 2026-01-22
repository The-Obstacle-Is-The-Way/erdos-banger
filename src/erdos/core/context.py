"""Application wiring for erdos-banger.

This module is the composition root for CLI execution. It centralizes how
concrete dependencies are created from environment defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from erdos.core.clients.openalex import OpenAlexConfig
from erdos.core.config import AppConfig
from erdos.core.problem_loader import ProblemLoader
from erdos.core.providers import CrossrefProvider, FallbackProvider, OpenAlexProvider
from erdos.core.search.facade import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import (
        MetadataProvider,
        ProblemRepository,
        SearchIndexProtocol,
    )


@dataclass
class AppContext:
    """Dependency container for CLI commands.

    The composition root for dependency injection. Commands access dependencies
    through this context rather than constructing them directly.

    Attributes:
        problems: Problem repository for accessing Erdős problems.
        config: Application configuration (centralized env reads).
        index: Search index (lazily initialized via ensure_index).
    """

    problems: ProblemRepository
    config: AppConfig = field(default_factory=AppConfig.from_env)
    index: SearchIndexProtocol | None = None

    @classmethod
    def from_environment(cls) -> AppContext:
        """Create context using environment defaults.

        This is the standard entry point for CLI commands. It reads all
        configuration from environment variables via AppConfig.from_env().
        """
        config = AppConfig.from_env()
        return cls(
            problems=ProblemLoader.from_default(data_path=config.data_path),
            config=config,
        )

    @classmethod
    def from_config(cls, config: AppConfig) -> AppContext:
        """Create context from explicit configuration.

        Use this in tests to avoid environment variable dependencies.

        Args:
            config: Explicit configuration values.

        Returns:
            AppContext with dependencies built from config.
        """
        return cls(
            problems=ProblemLoader.from_default(data_path=config.data_path),
            config=config,
        )

    def ensure_index(self) -> SearchIndexProtocol:
        """Ensure the search index dependency exists.

        Lazily initializes the index using configured path or default.
        """
        if self.index is not None:
            return self.index
        self.index = SearchIndex.from_default(index_path=self.config.index_path)
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
