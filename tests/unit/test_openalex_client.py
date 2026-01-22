"""Unit tests for OpenAlex API client."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import requests
import responses

from erdos.core.models import OpenAccessStatus
from erdos.core.openalex_client import (
    OpenAlexClient,
    OpenAlexConfig,
    _map_oa_status,
    extract_arxiv_id,
    find_pdf_url,
    openalex_to_reference,
    reconstruct_abstract,
)


# Test data fixtures
SAMPLE_OPENALEX_WORK = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1038/nature12373",
    "title": "Gravitational wave background detection",
    "publication_year": 2013,
    "authorships": [
        {"author": {"display_name": "John Doe", "id": "A123"}},
        {"author": {"display_name": "Jane Smith", "id": "A456"}},
    ],
    "primary_location": {
        "source": {"display_name": "Nature"},
        "pdf_url": "https://example.com/paper.pdf",
    },
    "locations": [
        {"pdf_url": "https://arxiv.org/pdf/1234.5678.pdf"},
    ],
    "abstract_inverted_index": {
        "This": [0],
        "is": [1],
        "a": [2],
        "test": [3],
        "abstract": [4],
    },
    "ids": {
        "openalex": "https://openalex.org/W2741809807",
        "doi": "https://doi.org/10.1038/nature12373",
    },
    "open_access": {"is_oa": True, "oa_status": "green"},
    "cited_by_count": 150,
    "concepts": [
        {"display_name": "Physics", "id": "C123"},
        {"display_name": "Astronomy", "id": "C456"},
        {"display_name": "General Relativity", "id": "C789"},
    ],
}

SAMPLE_OPENALEX_ARXIV_WORK = {
    "id": "https://openalex.org/W9999999999",
    "doi": "https://doi.org/10.48550/arxiv.1234.5678",
    "title": "Example arXiv Paper",
    "publication_year": 2023,
    "primary_location": {
        "landing_page_url": "http://arxiv.org/abs/1234.5678",
        "source": {"display_name": "arXiv"},
    },
    "ids": {
        "openalex": "https://openalex.org/W9999999999",
        "doi": "https://doi.org/10.48550/arxiv.1234.5678",
    },
    "open_access": {"is_oa": True, "oa_status": "green"},
    "cited_by_count": 42,
}

SAMPLE_OPENALEX_ARXIV_IN_LOCATION_ONLY = {
    "id": "https://openalex.org/W2626778328",
    # Canonical DOI is not the arXiv DataCite DOI (OpenAlex may canonicalize differently)
    "doi": "https://doi.org/10.65215/ctdc8e75",
    "title": "Attention Is All You Need",
    "publication_year": 2017,
    "primary_location": {
        "landing_page_url": "https://doi.org/10.65215/ctdc8e75",
        "source": {"display_name": "Some Venue"},
    },
    "locations": [
        {"landing_page_url": "https://doi.org/10.48550/arxiv.1706.03762"},
        {"landing_page_url": "http://arxiv.org/abs/1706.03762"},
        {"landing_page_url": "https://arxiv.org/pdf/1706.03762v5"},
    ],
    "ids": {
        "openalex": "https://openalex.org/W2626778328",
        "doi": "https://doi.org/10.65215/ctdc8e75",
    },
    "open_access": {"is_oa": True, "oa_status": "green"},
    "cited_by_count": 12345,
}

SAMPLE_OPENALEX_SEARCH_RESPONSE = {
    "meta": {"count": 1, "page": 1, "per_page": 25},
    "results": [SAMPLE_OPENALEX_WORK],
}


class TestOpenAlexConfig:
    """Tests for OpenAlexConfig."""

    def test_default_config(self) -> None:
        """Config has sensible defaults."""

        config = OpenAlexConfig()
        assert config.email is None
        assert config.timeout == 30.0
        assert config.max_retries == 3

    def test_from_env_with_erdos_mailto(self) -> None:
        """Config loads ERDOS_MAILTO from environment."""

        with patch.dict(os.environ, {"ERDOS_MAILTO": "test@example.com"}, clear=False):
            config = OpenAlexConfig.from_env()
            assert config.email == "test@example.com"

    def test_from_env_with_openalex_email(self) -> None:
        """Config loads OPENALEX_EMAIL from environment."""

        # Clear ERDOS_MAILTO to test fallback
        env = {"OPENALEX_EMAIL": "openalex@example.com"}
        with patch.dict(os.environ, env, clear=True):
            config = OpenAlexConfig.from_env()
            assert config.email == "openalex@example.com"

    def test_from_env_prefers_erdos_mailto(self) -> None:
        """ERDOS_MAILTO takes precedence over OPENALEX_EMAIL."""

        env = {
            "ERDOS_MAILTO": "erdos@example.com",
            "OPENALEX_EMAIL": "openalex@example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            config = OpenAlexConfig.from_env()
            assert config.email == "erdos@example.com"


class TestReconstructAbstract:
    """Tests for abstract reconstruction from inverted index."""

    def test_reconstruct_simple(self) -> None:
        """Reconstructs abstract from inverted index."""

        inverted_index = {"Hello": [0], "world": [1]}
        assert reconstruct_abstract(inverted_index) == "Hello world"

    def test_reconstruct_out_of_order(self) -> None:
        """Handles words stored in non-sequential order."""

        inverted_index = {"world": [1], "Hello": [0]}
        assert reconstruct_abstract(inverted_index) == "Hello world"

    def test_reconstruct_with_repeated_words(self) -> None:
        """Handles words appearing multiple times."""

        inverted_index = {"the": [0, 2], "cat": [1], "dog": [3]}
        assert reconstruct_abstract(inverted_index) == "the cat the dog"

    def test_reconstruct_empty(self) -> None:
        """Returns None for empty index."""

        assert reconstruct_abstract({}) is None

    def test_reconstruct_none(self) -> None:
        """Returns None for None input."""

        assert reconstruct_abstract(None) is None


class TestExtractArxivId:
    """Tests for arXiv ID extraction from OpenAlex IDs."""

    def test_extract_modern_arxiv_id(self) -> None:
        """Extracts post-2007 arXiv ID from arXiv DataCite DOI."""

        ids = {"doi": "https://doi.org/10.48550/arxiv.2301.00001"}
        assert extract_arxiv_id(ids) == "2301.00001"

    def test_extract_legacy_arxiv_id(self) -> None:
        """Extracts pre-2007 arXiv ID from arXiv DataCite DOI."""

        ids = {"doi": "https://doi.org/10.48550/arxiv.math/0703001"}
        assert extract_arxiv_id(ids) == "math/0703001"

    def test_extract_from_explicit_arxiv_url(self) -> None:
        """Defensive support: extract arXiv ID from explicit ids['arxiv'] URL."""
        ids = {"arxiv": "https://arxiv.org/abs/2301.00001v2"}
        assert extract_arxiv_id(ids) == "2301.00001"

    def test_extract_no_arxiv(self) -> None:
        """Returns None when no arXiv ID present."""

        ids = {"doi": "https://doi.org/10.1234/example"}
        assert extract_arxiv_id(ids) is None

    def test_extract_empty_ids(self) -> None:
        """Returns None for empty IDs dict."""

        assert extract_arxiv_id({}) is None


class TestFindPdfUrl:
    """Tests for PDF URL extraction from OpenAlex work."""

    def test_find_primary_pdf(self) -> None:
        """Finds PDF URL from primary location."""

        work = {
            "primary_location": {"pdf_url": "https://example.com/paper.pdf"},
            "locations": [],
        }
        assert find_pdf_url(work) == "https://example.com/paper.pdf"

    def test_find_alternate_pdf(self) -> None:
        """Finds PDF URL from alternate locations when primary is empty."""

        work = {
            "primary_location": {"pdf_url": None},
            "locations": [
                {"pdf_url": None},
                {"pdf_url": "https://example.com/alternate.pdf"},
            ],
        }
        assert find_pdf_url(work) == "https://example.com/alternate.pdf"

    def test_find_no_pdf(self) -> None:
        """Returns None when no PDF URL available."""
        work: dict[str, object] = {"primary_location": {}, "locations": []}
        assert find_pdf_url(work) is None

    def test_find_pdf_missing_keys(self) -> None:
        """Handles missing keys gracefully."""
        work: dict[str, object] = {}
        assert find_pdf_url(work) is None


class TestOpenAlexToReference:
    """Tests for converting OpenAlex work to ReferenceRecord."""

    def test_converts_full_work(self) -> None:
        """Converts complete OpenAlex work to ReferenceRecord."""

        ref = openalex_to_reference(SAMPLE_OPENALEX_WORK)

        assert ref.doi == "10.1038/nature12373"
        assert ref.arxiv_id is None
        assert ref.title == "Gravitational wave background detection"
        assert ref.authors == ["John Doe", "Jane Smith"]
        assert ref.year == 2013
        assert ref.venue == "Nature"
        assert ref.abstract == "This is a test abstract"
        assert ref.openalex_id == "https://openalex.org/W2741809807"
        assert ref.cited_by_count == 150
        assert ref.concepts == ["Physics", "Astronomy", "General Relativity"]
        assert ref.pdf_url == "https://example.com/paper.pdf"
        assert ref.oa_status == OpenAccessStatus.GREEN
        assert ref.source == "openalex"

    def test_converts_minimal_work(self) -> None:
        """Converts work with minimal fields."""

        minimal_work = {
            "id": "https://openalex.org/W123",
            "title": "Test Paper",
            "doi": "https://doi.org/10.1234/test",
        }
        ref = openalex_to_reference(minimal_work)

        assert ref.doi == "10.1234/test"
        assert ref.title == "Test Paper"
        assert ref.authors == []
        assert ref.year is None
        assert ref.venue is None
        assert ref.abstract is None
        assert ref.openalex_id == "https://openalex.org/W123"

    def test_handles_missing_doi(self) -> None:
        """Works with arXiv ID when DOI is missing."""

        work = {
            "id": "https://openalex.org/W123",
            "title": "ArXiv Paper",
            "ids": {"arxiv": "https://arxiv.org/abs/2301.00001"},
        }
        ref = openalex_to_reference(work)

        assert ref.doi is None
        assert ref.arxiv_id == "2301.00001"

    def test_converts_arxiv_work_sets_arxiv_id(self) -> None:
        """Converts an arXiv work to ReferenceRecord with arxiv_id populated."""
        ref = openalex_to_reference(SAMPLE_OPENALEX_ARXIV_WORK)
        assert ref.doi == "10.48550/arxiv.1234.5678"
        assert ref.arxiv_id == "1234.5678"

    def test_extracts_arxiv_id_from_non_primary_location(self) -> None:
        """Extracts arXiv ID when only locations contain an arXiv landing page."""
        ref = openalex_to_reference(SAMPLE_OPENALEX_ARXIV_IN_LOCATION_ONLY)
        assert ref.arxiv_id == "1706.03762"


class TestOpenAlexClient:
    """Tests for OpenAlex API client."""

    @responses.activate
    def test_get_by_doi_success(self) -> None:
        """Fetches work by DOI successfully."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.1038/nature12373",
            json=SAMPLE_OPENALEX_WORK,
            status=200,
        )

        config = OpenAlexConfig(email="test@example.com")
        client = OpenAlexClient(config)
        ref = client.get_by_doi("10.1038/nature12373")

        assert ref.doi == "10.1038/nature12373"
        assert ref.title == "Gravitational wave background detection"
        assert len(responses.calls) == 1
        url = responses.calls[0].request.url
        assert url is not None
        assert "mailto=test%40example.com" in url

    @responses.activate
    def test_get_by_arxiv_success(self) -> None:
        """Fetches work by arXiv ID successfully."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.48550/arxiv.1234.5678",
            json=SAMPLE_OPENALEX_ARXIV_WORK,
            status=200,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)
        ref = client.get_by_arxiv("1234.5678")

        assert ref.arxiv_id == "1234.5678"
        assert len(responses.calls) == 1
        url = responses.calls[0].request.url
        assert url is not None
        assert "works/https://doi.org/10.48550/arxiv.1234.5678" in url

    @responses.activate
    def test_get_by_arxiv_not_found(self) -> None:
        """Raises error when arXiv ID not found."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.48550/arxiv.9999.99999",
            status=404,
        )
        # Fallback path: search by locations.landing_page_url in /works
        # OpenAlexClient.get_by_arxiv tries 3 landing candidates; responses matches
        # by URL path (query params are ignored by default).
        for _ in range(3):
            responses.add(
                responses.GET,
                "https://api.openalex.org/works",
                json={"meta": {"count": 0}, "results": []},
                status=200,
            )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)

        with pytest.raises(ValueError, match=r"No work found for arXiv:9999\.99999"):
            client.get_by_arxiv("9999.99999")

    @responses.activate
    def test_get_by_arxiv_falls_back_to_locations_filter(self) -> None:
        """Falls back to locations filter when DOI lookup 404s but work exists."""
        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.48550/arxiv.1706.03762",
            status=404,
        )
        responses.add(
            responses.GET,
            "https://api.openalex.org/works",
            json={
                "meta": {"count": 1},
                "results": [SAMPLE_OPENALEX_ARXIV_IN_LOCATION_ONLY],
            },
            status=200,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)
        ref = client.get_by_arxiv("1706.03762v5")

        assert ref.arxiv_id == "1706.03762"
        assert ref.title == "Attention Is All You Need"

    @responses.activate
    def test_search_success(self) -> None:
        """Searches works successfully."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works",
            json=SAMPLE_OPENALEX_SEARCH_RESPONSE,
            status=200,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)
        results = client.search("gravitational waves", limit=10)

        assert len(results) == 1
        assert results[0].title == "Gravitational wave background detection"
        assert len(responses.calls) == 1
        url = responses.calls[0].request.url
        assert url is not None
        assert "search=gravitational" in url

    @responses.activate
    def test_search_empty_results(self) -> None:
        """Returns empty list when no results found."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works",
            json={"meta": {"count": 0}, "results": []},
            status=200,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)
        results = client.search("nonexistent query")

        assert results == []

    @responses.activate
    def test_get_citations_success(self) -> None:
        """Fetches citing works successfully."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works",
            json=SAMPLE_OPENALEX_SEARCH_RESPONSE,
            status=200,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)
        citations = client.get_citations("https://openalex.org/W2741809807", limit=5)

        assert len(citations) == 1
        assert len(responses.calls) == 1
        url = responses.calls[0].request.url
        assert url is not None
        assert "cites%3A" in url

    @responses.activate
    def test_get_references_success(self) -> None:
        """Fetches referenced works successfully."""

        responses.add(
            responses.GET,
            "https://api.openalex.org/works",
            json=SAMPLE_OPENALEX_SEARCH_RESPONSE,
            status=200,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)
        refs = client.get_references("https://openalex.org/W2741809807", limit=5)

        assert len(refs) == 1
        assert len(responses.calls) == 1
        url = responses.calls[0].request.url
        assert url is not None
        assert "cited_by%3A" in url

    @responses.activate
    def test_uses_retry_on_429(self) -> None:
        """Retries on rate limit (429) errors."""

        # First request returns 429, second succeeds
        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.1234/test",
            status=429,
            headers={"Retry-After": "0.1"},
        )
        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.1234/test",
            json={
                "id": "https://openalex.org/W123",
                "title": "Test",
                "doi": "https://doi.org/10.1234/test",
            },
            status=200,
        )

        config = OpenAlexConfig(max_retries=3)
        client = OpenAlexClient(config)
        ref = client.get_by_doi("10.1234/test")

        assert ref.title == "Test"
        assert len(responses.calls) == 2

    @responses.activate
    def test_raises_on_404(self) -> None:
        """Raises HTTPError on 404."""
        responses.add(
            responses.GET,
            "https://api.openalex.org/works/https://doi.org/10.1234/notfound",
            status=404,
        )

        config = OpenAlexConfig()
        client = OpenAlexClient(config)

        with pytest.raises(requests.HTTPError):
            client.get_by_doi("10.1234/notfound")


class TestOpenAccessStatusMapping:
    """Tests for OpenAlex OA status mapping."""

    def test_maps_green_status(self) -> None:
        """Maps green OA status correctly."""

        oa = {"is_oa": True, "oa_status": "green"}
        assert _map_oa_status(oa) == OpenAccessStatus.GREEN

    def test_maps_gold_status(self) -> None:
        """Maps gold OA status correctly."""

        oa = {"is_oa": True, "oa_status": "gold"}
        assert _map_oa_status(oa) == OpenAccessStatus.GOLD

    def test_maps_hybrid_status(self) -> None:
        """Maps hybrid OA status correctly."""

        oa = {"is_oa": True, "oa_status": "hybrid"}
        assert _map_oa_status(oa) == OpenAccessStatus.HYBRID

    def test_maps_bronze_status(self) -> None:
        """Maps bronze OA status correctly."""

        oa = {"is_oa": True, "oa_status": "bronze"}
        assert _map_oa_status(oa) == OpenAccessStatus.BRONZE

    def test_maps_closed_status(self) -> None:
        """Maps closed (non-OA) status correctly."""

        oa = {"is_oa": False, "oa_status": "closed"}
        assert _map_oa_status(oa) == OpenAccessStatus.CLOSED

    def test_maps_unknown_for_empty(self) -> None:
        """Maps to unknown for empty/missing data."""

        assert _map_oa_status({}) == OpenAccessStatus.UNKNOWN
        assert _map_oa_status(None) == OpenAccessStatus.UNKNOWN
