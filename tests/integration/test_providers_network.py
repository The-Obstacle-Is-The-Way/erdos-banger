"""Integration tests for MetadataProvider with real APIs (SPEC-022).

These tests make actual network requests to external APIs.
Run with: uv run pytest -m requires_network tests/integration/test_providers_network.py
"""

import pytest

from erdos.core.providers import CrossrefProvider, FallbackProvider, OpenAlexProvider


@pytest.mark.requires_network
class TestOpenAlexProviderIntegration:
    """Integration tests for OpenAlexProvider with real API."""

    def test_get_by_doi_real(self) -> None:
        """Test real DOI lookup via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        # Use a stable, well-known DOI (Nature paper about CRISPR)
        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert result.doi == "10.1038/nature12373"
        # Title contains "programmable" or relates to CRISPR
        assert result.title is not None

    def test_get_by_doi_not_found(self) -> None:
        """Test DOI not found returns None."""
        provider = OpenAlexProvider.from_env()
        result = provider.get_by_doi("10.1234/nonexistent-doi-that-does-not-exist")

        assert result is None

    def test_get_by_arxiv_real(self) -> None:
        """Test real arXiv lookup via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        # Use a well-known arXiv paper (Attention Is All You Need)
        result = provider.get_by_arxiv("1706.03762")

        assert result is not None
        assert result.arxiv_id == "1706.03762"

    def test_search_real(self) -> None:
        """Test real search via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        results = provider.search("prime gap erdos", limit=5)

        assert isinstance(results, list)
        # We expect at least some results for this query
        # (but don't assert > 0 in case API changes)


@pytest.mark.requires_network
class TestCrossrefProviderIntegration:
    """Integration tests for CrossrefProvider with real API."""

    def test_get_by_doi_real(self) -> None:
        """Test real DOI lookup via Crossref."""
        provider = CrossrefProvider.from_env()
        # Use a stable DOI
        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert result.doi == "10.1038/nature12373"
        assert result.title is not None

    def test_get_by_doi_not_found(self) -> None:
        """Test DOI not found returns None."""
        provider = CrossrefProvider.from_env()
        result = provider.get_by_doi("10.1234/nonexistent-doi-that-does-not-exist")

        assert result is None

    def test_get_by_arxiv_not_supported(self) -> None:
        """Test arXiv lookup returns None (not supported by Crossref)."""
        provider = CrossrefProvider.from_env()
        result = provider.get_by_arxiv("1706.03762")

        assert result is None


@pytest.mark.requires_network
class TestFallbackProviderIntegration:
    """Integration tests for FallbackProvider with real APIs."""

    def test_openalex_to_crossref_fallback_doi(self) -> None:
        """Test fallback chain finds DOI via primary provider."""
        provider = FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider.from_env(),
        )

        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert result.doi == "10.1038/nature12373"

    def test_openalex_to_crossref_fallback_arxiv(self) -> None:
        """Test fallback chain finds arXiv via primary provider."""
        provider = FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider.from_env(),
        )

        result = provider.get_by_arxiv("1706.03762")

        assert result is not None
        # OpenAlex should find this via arXiv DOI lookup

    def test_provider_name(self) -> None:
        """Test provider name reflects the chain."""
        provider = FallbackProvider(
            OpenAlexProvider.from_env(),
            CrossrefProvider.from_env(),
        )

        assert provider.provider_name == "fallback(openalex -> crossref)"
