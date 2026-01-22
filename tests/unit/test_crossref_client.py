"""Unit tests for Crossref API client (SPEC-010-C)."""

import json
from pathlib import Path

import pytest
import requests
import responses

from erdos.core.clients.crossref import fetch_crossref_work, parse_crossref_work
from erdos.core.models import ReferenceRecord


@pytest.fixture
def fixture_dir() -> Path:
    """Return the path to the crossref_responses fixture directory."""
    return Path(__file__).parent.parent / "fixtures" / "crossref_responses"


@pytest.fixture
def crossref_success_payload(fixture_dir: Path) -> dict[str, object]:
    """Load the successful Crossref work response fixture."""
    fixture_path = fixture_dir / "doi_10.1007_BF01940595.json"
    return json.loads(fixture_path.read_text())  # type: ignore[no-any-return]


@pytest.fixture
def crossref_not_found_payload(fixture_dir: Path) -> dict[str, object]:
    """Load the Crossref not-found error response fixture."""
    fixture_path = fixture_dir / "doi_not_found.json"
    return json.loads(fixture_path.read_text())  # type: ignore[no-any-return]


# --- parse_crossref_work tests (no network) ---


def test_parse_crossref_work_success(
    crossref_success_payload: dict[str, object],
) -> None:
    """parse_crossref_work extracts metadata from a successful Crossref response."""
    doi = "10.1007/BF01940595"
    record = parse_crossref_work(crossref_success_payload, doi=doi)

    assert isinstance(record, ReferenceRecord)
    assert record.doi == doi
    assert record.title == "Some problems on number theory"
    assert record.authors == ["Paul Erdős"]
    assert record.year == 1975
    assert record.venue == "Journal of Number Theory"
    assert record.source == "crossref"


def test_parse_crossref_work_missing_title(
    crossref_success_payload: dict[str, object],
) -> None:
    """parse_crossref_work raises ValueError when title is missing."""
    # Remove title from payload
    message = crossref_success_payload["message"]
    assert isinstance(message, dict)
    del message["title"]

    with pytest.raises(ValueError, match="title"):
        parse_crossref_work(crossref_success_payload, doi="10.1007/BF01940595")


def test_parse_crossref_work_not_found(
    crossref_not_found_payload: dict[str, object],
) -> None:
    """parse_crossref_work raises ValueError for Crossref error responses."""
    with pytest.raises(ValueError, match="Resource not found"):
        parse_crossref_work(crossref_not_found_payload, doi="10.1234/missing")


def test_parse_crossref_work_no_authors(
    crossref_success_payload: dict[str, object],
) -> None:
    """parse_crossref_work handles missing authors gracefully."""
    message = crossref_success_payload["message"]
    assert isinstance(message, dict)
    del message["author"]

    record = parse_crossref_work(crossref_success_payload, doi="10.1007/BF01940595")
    assert record.authors == []


def test_parse_crossref_work_no_year(
    crossref_success_payload: dict[str, object],
) -> None:
    """parse_crossref_work handles missing publication year gracefully."""
    message = crossref_success_payload["message"]
    assert isinstance(message, dict)
    del message["published-print"]

    record = parse_crossref_work(crossref_success_payload, doi="10.1007/BF01940595")
    assert record.year is None


# --- fetch_crossref_work tests (mocked network) ---


@responses.activate
def test_fetch_crossref_work_success(
    crossref_success_payload: dict[str, object],
) -> None:
    """fetch_crossref_work retrieves a DOI work from Crossref API."""
    doi = "10.1007/BF01940595"
    url = f"https://api.crossref.org/works/{doi}"

    # Mock the HTTP response
    responses.add(
        responses.GET,
        url,
        json=crossref_success_payload,
        status=200,
    )

    result = fetch_crossref_work(doi, mailto="test@example.com", timeout=10.0)

    assert result == crossref_success_payload
    assert len(responses.calls) == 1
    request_url = responses.calls[0].request.url
    assert request_url is not None
    assert request_url.startswith(url)
    # Check for mailto parameter (may be URL-encoded)
    assert "mailto=test" in request_url


@responses.activate
def test_fetch_crossref_work_not_found(
    crossref_not_found_payload: dict[str, object],
) -> None:
    """fetch_crossref_work raises an exception for 404 responses."""
    doi = "10.1234/missing"
    url = f"https://api.crossref.org/works/{doi}"

    # Mock the HTTP 404 response
    responses.add(
        responses.GET,
        url,
        json=crossref_not_found_payload,
        status=404,
    )

    with pytest.raises(requests.HTTPError):
        fetch_crossref_work(doi, mailto="test@example.com", timeout=10.0)


@responses.activate
def test_fetch_crossref_work_timeout() -> None:
    """fetch_crossref_work respects the timeout parameter."""
    doi = "10.1007/BF01940595"
    url = f"https://api.crossref.org/works/{doi}"

    # Mock a timeout by raising requests.Timeout
    responses.add(
        responses.GET,
        url,
        body=requests.Timeout("Request timed out"),
    )

    with pytest.raises(requests.Timeout):
        fetch_crossref_work(doi, mailto="test@example.com", timeout=0.1)


@responses.activate
def test_fetch_crossref_work_includes_user_agent(
    crossref_success_payload: dict[str, object],
) -> None:
    """fetch_crossref_work includes a User-Agent header."""
    doi = "10.1007/BF01940595"
    url = f"https://api.crossref.org/works/{doi}"

    responses.add(
        responses.GET,
        url,
        json=crossref_success_payload,
        status=200,
    )

    fetch_crossref_work(doi, mailto="test@example.com", timeout=10.0)

    assert len(responses.calls) == 1
    user_agent = responses.calls[0].request.headers.get("User-Agent", "")
    assert user_agent  # Should not be empty
    assert "erdos" in user_agent.lower() or "python" in user_agent.lower()
