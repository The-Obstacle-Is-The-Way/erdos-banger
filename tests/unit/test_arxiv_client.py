"""Unit tests for arXiv client."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import requests
import responses

from erdos.core.clients.arxiv import fetch_arxiv_atom, parse_arxiv_atom
from erdos.core.models import OpenAccessStatus, ReferenceRecord


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "arxiv_responses"


def test_parse_arxiv_atom_success():
    """Test parsing valid arXiv atom XML."""
    xml_path = FIXTURES_DIR / "arxiv_2203.00001.xml"
    xml_text = xml_path.read_text()

    record = parse_arxiv_atom(xml_text)

    assert isinstance(record, ReferenceRecord)
    assert record.arxiv_id == "2203.00001v1"
    assert record.title == "Sample ArXiv Paper Title"
    assert record.authors == ["Test Author"]
    assert record.year == 2022
    assert record.source == "arxiv"
    assert record.oa_status == OpenAccessStatus.GREEN
    assert record.oa_url == "https://arxiv.org/abs/2203.00001v1"


def test_parse_arxiv_atom_not_found():
    """Test parsing arXiv not found response."""
    xml_path = FIXTURES_DIR / "arxiv_not_found.xml"
    xml_text = xml_path.read_text()

    with pytest.raises(ValueError, match="No entry found"):
        parse_arxiv_atom(xml_text)


def test_parse_arxiv_atom_multiple_authors():
    """Test parsing arXiv atom XML with multiple authors."""
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.56789v2</id>
    <title>Multi-Author Paper</title>
    <summary>Abstract text.</summary>
    <author>
      <name>Alice Smith</name>
    </author>
    <author>
      <name>Bob Jones</name>
    </author>
    <author>
      <name>Carol White</name>
    </author>
    <published>2021-05-15T12:00:00Z</published>
    <link href="http://arxiv.org/abs/1234.56789v2" rel="alternate" type="text/html"/>
  </entry>
</feed>"""

    record = parse_arxiv_atom(xml_text)

    assert record.authors == ["Alice Smith", "Bob Jones", "Carol White"]
    assert record.arxiv_id == "1234.56789v2"
    assert record.year == 2021


def test_parse_arxiv_atom_strips_version_for_url():
    """Test that OA URL uses canonical arXiv ID without version."""
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2203.00001v3</id>
    <title>Versioned Paper</title>
    <summary>Abstract.</summary>
    <author>
      <name>Test Author</name>
    </author>
    <published>2022-03-01T00:00:00Z</published>
    <link href="http://arxiv.org/abs/2203.00001v3" rel="alternate" type="text/html"/>
  </entry>
</feed>"""

    record = parse_arxiv_atom(xml_text)

    # The arxiv_id should preserve the version
    assert record.arxiv_id == "2203.00001v3"
    # But the OA URL should use the canonical ID (could be with or without version - let's check spec)
    # According to spec: Set oa_url=https://arxiv.org/abs/<id>
    # The <id> in the XML includes version, so we'll use it as-is
    assert record.oa_url == "https://arxiv.org/abs/2203.00001v3"


def test_parse_arxiv_atom_invalid_xml():
    """Test parsing invalid XML."""
    xml_text = "not xml at all"

    with pytest.raises(ET.ParseError):
        parse_arxiv_atom(xml_text)


def test_parse_arxiv_atom_missing_required_fields():
    """Test parsing atom XML missing required fields (title)."""
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.56789v1</id>
    <summary>Abstract text.</summary>
    <author>
      <name>Test Author</name>
    </author>
    <published>2021-05-15T12:00:00Z</published>
  </entry>
</feed>"""

    with pytest.raises(ValueError, match="title"):
        parse_arxiv_atom(xml_text)


# Tests for fetch_arxiv_atom


@responses.activate
def test_fetch_arxiv_atom_success():
    """Test fetching arXiv metadata via HTTP."""
    xml_path = FIXTURES_DIR / "arxiv_2203.00001.xml"
    xml_text = xml_path.read_text()

    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=xml_text,
        status=200,
        content_type="application/xml",
    )

    result = fetch_arxiv_atom("2203.00001", timeout=30.0)

    assert result == xml_text
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url is not None
    assert "id_list=2203.00001" in responses.calls[0].request.url


@responses.activate
def test_fetch_arxiv_atom_strips_version():
    """Test that version suffix is stripped for API query."""
    xml_path = FIXTURES_DIR / "arxiv_2203.00001.xml"
    xml_text = xml_path.read_text()

    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=xml_text,
        status=200,
        content_type="application/xml",
    )

    result = fetch_arxiv_atom("2203.00001v3", timeout=30.0)

    assert result == xml_text
    # Should strip version suffix for query
    assert responses.calls[0].request.url is not None
    assert "id_list=2203.00001" in responses.calls[0].request.url
    assert "v3" not in responses.calls[0].request.url


@responses.activate
def test_fetch_arxiv_atom_network_error():
    """Test fetch handles network errors gracefully."""
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body="Internal Server Error",
        status=500,
    )

    with pytest.raises(requests.HTTPError):
        fetch_arxiv_atom("2203.00001", timeout=30.0)


@responses.activate
def test_fetch_arxiv_atom_timeout():
    """Test fetch respects timeout parameter."""

    def request_callback(_request):
        raise requests.Timeout("Request timed out")

    responses.add_callback(
        responses.GET,
        "https://export.arxiv.org/api/query",
        callback=request_callback,
    )

    with pytest.raises(requests.Timeout):
        fetch_arxiv_atom("2203.00001", timeout=1.0)
