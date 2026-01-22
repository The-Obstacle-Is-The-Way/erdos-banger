"""Unit tests for MetadataProvider implementations (SPEC-022)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from erdos.core.models import ReferenceRecord


class MockProvider:
    """Mock MetadataProvider for testing fallback chains."""

    def __init__(
        self,
        name: str,
        results: dict[tuple[str, str], ReferenceRecord | list[ReferenceRecord]]
        | None = None,
    ) -> None:
        self._name = name
        self._results: dict[
            tuple[str, str], ReferenceRecord | list[ReferenceRecord]
        ] = results or {}
        self._call_log: list[tuple[str, tuple[str, ...]]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        self._call_log.append(("get_by_doi", (doi,)))
        result = self._results.get(("doi", doi))
        return result if isinstance(result, ReferenceRecord) else None

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        self._call_log.append(("get_by_arxiv", (arxiv_id,)))
        result = self._results.get(("arxiv", arxiv_id))
        return result if isinstance(result, ReferenceRecord) else None

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        self._call_log.append(("search", (query, str(limit))))
        result = self._results.get(("search", query))
        return result if isinstance(result, list) else []


class TestMetadataProviderProtocol:
    """Tests for MetadataProvider protocol definition."""

    def test_protocol_exists_in_ports(self) -> None:
        """MetadataProvider protocol should be defined in ports.py."""
        from erdos.core.ports import MetadataProvider

        assert hasattr(MetadataProvider, "provider_name")
        assert hasattr(MetadataProvider, "get_by_doi")
        assert hasattr(MetadataProvider, "get_by_arxiv")
        assert hasattr(MetadataProvider, "search")

    def test_mock_provider_satisfies_protocol(self) -> None:
        """MockProvider should satisfy the MetadataProvider protocol."""
        mock = MockProvider("test")
        # Verify mock has protocol's interface
        assert hasattr(mock, "provider_name")
        assert hasattr(mock, "get_by_doi")
        assert hasattr(mock, "get_by_arxiv")
        assert hasattr(mock, "search")
        assert mock.provider_name == "test"


class TestFallbackProvider:
    """Tests for FallbackProvider chain logic."""

    def test_requires_at_least_one_provider(self) -> None:
        """FallbackProvider should require at least one provider."""
        from erdos.core.providers import FallbackProvider

        with pytest.raises(ValueError, match="at least one provider"):
            FallbackProvider()

    def test_uses_primary_when_successful(self) -> None:
        """Primary provider result is returned if found."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")
        primary = MockProvider("primary", {("doi", "10.1234/test"): record})
        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record
        # Fallback should not be called
        assert len(fallback._call_log) == 0

    def test_falls_back_when_primary_returns_none(self) -> None:
        """Fallback is used when primary returns None."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")
        primary = MockProvider("primary")  # Returns None
        fallback = MockProvider("fallback", {("doi", "10.1234/test"): record})

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record
        # Both should be called
        assert len(primary._call_log) == 1
        assert len(fallback._call_log) == 1

    def test_falls_back_when_primary_raises_expected_error(self) -> None:
        """Fallback is used when primary raises an expected exception type."""
        import requests

        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")

        primary = MagicMock()
        primary.provider_name = "primary"
        # RequestException is an expected error type per port contract
        primary.get_by_doi.side_effect = requests.RequestException("API error")

        fallback = MockProvider("fallback", {("doi", "10.1234/test"): record})

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_propagates_unexpected_exceptions(self) -> None:
        """Unexpected exceptions (programming errors) should propagate, not be caught."""
        from erdos.core.providers import FallbackProvider

        primary = MagicMock()
        primary.provider_name = "primary"
        # RuntimeError is NOT an expected error type - should propagate
        primary.get_by_doi.side_effect = RuntimeError("Programming bug")

        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)

        with pytest.raises(RuntimeError, match="Programming bug"):
            provider.get_by_doi("10.1234/test")

    def test_propagates_unexpected_exceptions_arxiv(self) -> None:
        """Unexpected exceptions for arXiv lookups should propagate."""
        from erdos.core.providers import FallbackProvider

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.get_by_arxiv.side_effect = TypeError("Unexpected type bug")

        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)

        with pytest.raises(TypeError, match="Unexpected type bug"):
            provider.get_by_arxiv("2103.03874")

    def test_propagates_unexpected_exceptions_search(self) -> None:
        """Unexpected exceptions for search should propagate."""
        from erdos.core.providers import FallbackProvider

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.search.side_effect = AttributeError("Missing attribute")

        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)

        with pytest.raises(AttributeError, match="Missing attribute"):
            provider.search("erdos", limit=10)

    def test_falls_back_on_value_error(self) -> None:
        """ValueError (invalid identifier) should trigger fallback per contract."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.get_by_doi.side_effect = ValueError("Invalid DOI format")

        fallback = MockProvider("fallback", {("doi", "10.1234/test"): record})

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_returns_none_when_all_providers_fail(self) -> None:
        """None is returned when all providers return None."""
        from erdos.core.providers import FallbackProvider

        primary = MockProvider("primary")
        fallback = MockProvider("fallback")

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_doi("10.1234/nonexistent")

        assert result is None

    def test_provider_name_shows_chain(self) -> None:
        """Provider name reflects the fallback chain."""
        from erdos.core.providers import FallbackProvider

        primary = MockProvider("openalex")
        fallback = MockProvider("crossref")

        provider = FallbackProvider(primary, fallback)

        assert provider.provider_name == "fallback(openalex -> crossref)"

    def test_get_by_arxiv_fallback(self) -> None:
        """Fallback works for arXiv lookups."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="arXiv Paper", arxiv_id="2103.03874")
        primary = MockProvider("primary")
        fallback = MockProvider("fallback", {("arxiv", "2103.03874"): record})

        provider = FallbackProvider(primary, fallback)
        result = provider.get_by_arxiv("2103.03874")

        assert result == record

    def test_search_fallback(self) -> None:
        """Fallback works for search queries."""
        from erdos.core.providers import FallbackProvider

        records = [
            ReferenceRecord(title="Paper 1", doi="10.1234/1"),
            ReferenceRecord(title="Paper 2", doi="10.1234/2"),
        ]
        primary = MockProvider("primary")  # Returns empty list
        fallback = MockProvider("fallback", {("search", "erdos"): records})

        provider = FallbackProvider(primary, fallback)
        result = provider.search("erdos", limit=10)

        assert result == records


class TestOpenAlexProvider:
    """Tests for OpenAlexProvider wrapper."""

    def test_provider_name(self) -> None:
        """OpenAlexProvider should have 'openalex' as provider name."""
        from erdos.core.providers import OpenAlexProvider

        # Create with a mock client to avoid network
        provider = OpenAlexProvider._create_with_client(MagicMock())
        assert provider.provider_name == "openalex"

    def test_get_by_doi_delegates_to_client(self) -> None:
        """get_by_doi should delegate to the wrapped OpenAlexClient."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        expected = ReferenceRecord(title="Test", doi="10.1234/test")
        mock_client.get_by_doi.return_value = expected

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_doi("10.1234/test")

        assert result == expected
        mock_client.get_by_doi.assert_called_once_with("10.1234/test")

    def test_get_by_doi_returns_none_on_404(self) -> None:
        """get_by_doi should return None on 404, not raise."""
        import requests

        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.HTTPError(response=mock_response)
        mock_client.get_by_doi.side_effect = http_error

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_doi("10.1234/notfound")

        assert result is None

    def test_get_by_arxiv_delegates_to_client(self) -> None:
        """get_by_arxiv should delegate to the wrapped OpenAlexClient."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        expected = ReferenceRecord(title="arXiv paper", arxiv_id="2103.03874")
        mock_client.get_by_arxiv.return_value = expected

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_arxiv("2103.03874")

        assert result == expected
        mock_client.get_by_arxiv.assert_called_once_with("2103.03874")

    def test_get_by_arxiv_returns_none_on_value_error(self) -> None:
        """get_by_arxiv should return None when client raises ValueError."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        mock_client.get_by_arxiv.side_effect = ValueError("Not found")

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_arxiv("2103.03874")

        assert result is None

    def test_search_delegates_to_client(self) -> None:
        """search should delegate to the wrapped OpenAlexClient."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        expected = [ReferenceRecord(title="Paper", doi="10.1234/test")]
        mock_client.search.return_value = expected

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.search("erdos", limit=10)

        assert result == expected
        mock_client.search.assert_called_once_with("erdos", limit=10)


class TestCrossrefProvider:
    """Tests for CrossrefProvider wrapper."""

    def test_provider_name(self) -> None:
        """CrossrefProvider should have 'crossref' as provider name."""
        from erdos.core.providers import CrossrefProvider

        provider = CrossrefProvider(mailto="test@example.com")
        assert provider.provider_name == "crossref"

    def test_get_by_arxiv_returns_none(self) -> None:
        """CrossrefProvider.get_by_arxiv should always return None (not supported)."""
        from erdos.core.providers import CrossrefProvider

        provider = CrossrefProvider(mailto="test@example.com")
        result = provider.get_by_arxiv("2103.03874")

        assert result is None

    def test_search_returns_empty(self) -> None:
        """CrossrefProvider.search should return empty list (not implemented)."""
        from erdos.core.providers import CrossrefProvider

        provider = CrossrefProvider(mailto="test@example.com")
        result = provider.search("erdos", limit=10)

        assert result == []


class TestBuildMetadataProvider:
    """Tests for build_metadata_provider factory function."""

    def test_creates_fallback_chain(self) -> None:
        """build_metadata_provider should create a FallbackProvider chain."""
        from erdos.core.context import build_metadata_provider
        from erdos.core.providers import FallbackProvider

        provider = build_metadata_provider(mailto="test@example.com", timeout=30.0)

        assert isinstance(provider, FallbackProvider)
        assert "openalex" in provider.provider_name
        assert "crossref" in provider.provider_name
