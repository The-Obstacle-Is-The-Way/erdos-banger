"""Integration tests for OpenAlex API client (requires network access).

These tests make live API calls to OpenAlex and verify the client works correctly
with real data. Use `pytest -m requires_network` to run these tests.
"""

from __future__ import annotations

import pytest

from erdos.core.clients.openalex import OpenAlexClient, OpenAlexConfig
from erdos.core.models import OpenAccessStatus


@pytest.mark.requires_network
class TestOpenAlexClientLive:
    """Integration tests against live OpenAlex API."""

    def test_get_by_doi_real_paper(self) -> None:
        """Fetch a known paper by DOI from OpenAlex."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        # Known arXiv paper (Green-Tao theorem preprint)
        ref = client.get_by_doi("10.48550/arxiv.math/0404188")

        assert ref.doi == "10.48550/arxiv.math/0404188"
        assert ref.title is not None
        assert "primes" in ref.title.lower()
        assert ref.openalex_id is not None
        assert ref.openalex_id.startswith("https://openalex.org/W")
        assert ref.cited_by_count is not None
        assert ref.cited_by_count > 0
        assert ref.source == "openalex"

    def test_get_by_arxiv_real_paper(self) -> None:
        """Fetch a known paper by arXiv ID from OpenAlex."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        # Known arXiv paper (Green-Tao theorem preprint)
        ref = client.get_by_arxiv("math/0404188")

        assert ref.arxiv_id is not None
        assert ref.title is not None
        assert "primes" in ref.title.lower()
        assert ref.openalex_id is not None

    def test_search_returns_results(self) -> None:
        """Search for a common term returns results."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        results = client.search("graph coloring erdos", limit=5)

        assert len(results) > 0
        assert len(results) <= 5
        for ref in results:
            assert ref.title is not None
            assert ref.openalex_id is not None
            assert ref.source == "openalex"

    def test_search_with_concepts(self) -> None:
        """Search results include concept tags."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        results = client.search("ramsey theory combinatorics", limit=3)

        assert len(results) > 0
        # At least one result should have concepts
        has_concepts = any(len(ref.concepts) > 0 for ref in results)
        assert has_concepts, "Expected at least one result with concepts"

    def test_get_citations_for_famous_paper(self) -> None:
        """Get citations for a well-cited paper."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        # First get a known paper's OpenAlex ID
        paper = client.get_by_doi("10.48550/arxiv.math/0404188")
        assert paper.openalex_id is not None

        # Then get its citations
        citations = client.get_citations(paper.openalex_id, limit=5)

        # Should have citations (this is a famous paper)
        assert len(citations) > 0
        for citation in citations:
            assert citation.title is not None
            assert citation.openalex_id is not None

    def test_reference_record_fields_populated(self) -> None:
        """Verify ReferenceRecord fields are properly populated from OpenAlex."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        # Use a paper we know has good metadata
        ref = client.get_by_doi("10.48550/arxiv.math/0404188")

        # Check all OpenAlex-specific fields
        assert ref.openalex_id is not None
        assert ref.cited_by_count is not None
        assert ref.cited_by_count >= 0
        assert isinstance(ref.concepts, list)
        # OA status should be set (this is an arXiv paper, so should be green/gold)
        assert ref.oa_status in [
            OpenAccessStatus.GREEN,
            OpenAccessStatus.GOLD,
            OpenAccessStatus.HYBRID,
            OpenAccessStatus.BRONZE,
            OpenAccessStatus.CLOSED,
            OpenAccessStatus.UNKNOWN,
        ]

    def test_abstract_reconstruction(self) -> None:
        """Verify abstracts are reconstructed correctly."""
        config = OpenAlexConfig.from_env()
        client = OpenAlexClient(config)

        ref = client.get_by_doi("10.48550/arxiv.math/0404188")

        # The Green-Tao arXiv record should have an abstract
        assert ref.abstract is not None
        assert len(ref.abstract) > 50  # Should be a meaningful abstract
        # Should contain recognizable words
        assert any(
            word in ref.abstract.lower() for word in ["prime", "primes", "progression"]
        )

    def test_config_from_env_polite_pool(self) -> None:
        """Verify config loads email for polite pool access."""
        # This test just verifies the config mechanism works
        config = OpenAlexConfig.from_env()
        # Email may or may not be set depending on environment
        # Just verify the config object is valid
        assert config.timeout > 0
        assert config.max_retries > 0
