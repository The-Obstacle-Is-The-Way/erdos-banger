"""arXiv API client for literature metadata.

This module provides functions to fetch and parse arXiv metadata from the
arXiv export API (Atom XML format).

API Reference: https://info.arxiv.org/help/api/user-manual.html
"""

import io
import logging
import posixpath
import re
import tarfile
import time
from datetime import datetime

import defusedxml.ElementTree as ET

from erdos.core.constants import MAX_TEX_FILE_SIZE
from erdos.core.models import OpenAccessStatus, ReferenceRecord
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


# Atom namespace
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

ARXIV_USER_AGENT = (
    "erdos-banger/1.0 (https://github.com/The-Obstacle-Is-The-Way/erdos-banger)"
)


def parse_arxiv_atom(xml_text: str) -> ReferenceRecord:
    """Parse arXiv Atom XML response into a ReferenceRecord.

    Args:
        xml_text: Raw XML text from arXiv export API.

    Returns:
        ReferenceRecord with arXiv metadata.

    Raises:
        ValueError: If XML contains no entry (not found) or missing required fields.
        xml.etree.ElementTree.ParseError: If XML is malformed.
    """
    root = ET.fromstring(xml_text)

    # Find the entry element
    entry = root.find("atom:entry", ATOM_NS)
    if entry is None:
        raise ValueError("No entry found in arXiv response (paper may not exist)")

    # Extract required fields
    title_elem = entry.find("atom:title", ATOM_NS)
    if title_elem is None or not title_elem.text:
        raise ValueError("Missing required field: title")
    title = title_elem.text.strip()

    # Extract arXiv ID from the id element
    id_elem = entry.find("atom:id", ATOM_NS)
    if id_elem is None or not id_elem.text:
        raise ValueError("Missing required field: id")

    # Parse ID: http://arxiv.org/abs/2203.00001v1 -> 2203.00001v1
    id_url = id_elem.text.strip()
    arxiv_id_match = re.search(r"arxiv\.org/abs/([^\s]+)$", id_url)
    if not arxiv_id_match:
        raise ValueError(f"Could not parse arXiv ID from: {id_url}")
    arxiv_id = arxiv_id_match.group(1)

    # Extract authors
    authors = []
    for author_elem in entry.findall("atom:author", ATOM_NS):
        name_elem = author_elem.find("atom:name", ATOM_NS)
        if name_elem is not None and name_elem.text:
            authors.append(name_elem.text.strip())

    # Extract year from published date
    year = None
    published_elem = entry.find("atom:published", ATOM_NS)
    if published_elem is not None and published_elem.text:
        try:
            dt = datetime.fromisoformat(
                published_elem.text.strip().replace("Z", "+00:00")
            )
            year = dt.year
        except (ValueError, AttributeError):
            logger.debug(
                "Failed to parse arXiv published date: %s",
                published_elem.text,
                exc_info=True,
            )

    # Construct OA URL (use https)
    oa_url = f"https://arxiv.org/abs/{arxiv_id}"

    return ReferenceRecord(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        year=year,
        source="arxiv",
        oa_status=OpenAccessStatus.GREEN,
        oa_url=oa_url,
    )


def fetch_arxiv_atom(arxiv_id: str, *, timeout: float = 30.0) -> str:
    """Fetch arXiv metadata via export API.

    Args:
        arxiv_id: arXiv identifier (with or without version, e.g., "2203.00001" or "2203.00001v1").
        timeout: HTTP timeout in seconds.

    Returns:
        Raw XML text from arXiv export API.

    Raises:
        requests.HTTPError: If HTTP request fails.
        requests.Timeout: If request times out after all retries.
        requests.ConnectionError: If connection fails after all retries.
    """
    # Strip version suffix for API query (2203.00001v1 -> 2203.00001)
    arxiv_id_clean = re.sub(r"v\d+$", "", arxiv_id)

    url = "https://export.arxiv.org/api/query"
    params = {"id_list": arxiv_id_clean}
    headers = {"User-Agent": ARXIV_USER_AGENT}

    logger.debug("Fetching arXiv metadata for ID: %s", arxiv_id)
    start_time = time.monotonic()

    response = fetch_with_retry(url, timeout=timeout, params=params, headers=headers)
    elapsed = time.monotonic() - start_time
    logger.debug(
        "arXiv response: %d bytes in %.2fs (status %d)",
        len(response.content),
        elapsed,
        response.status_code,
    )

    return response.text


def extract_arxiv_text(tarball_bytes: bytes) -> bytes:
    """Extract text from arXiv source tarball.

    Implements a best-effort heuristic:
    1. Find all .tex files in the tarball
    2. Select the largest .tex file by byte size
    3. Return its raw content (up to 2 MiB)

    Args:
        tarball_bytes: Raw bytes of a tar archive (gzip, bzip2, xz, or uncompressed).

    Returns:
        Raw bytes of the largest .tex file (capped at 2 MiB).

    Raises:
        ValueError: If no .tex files found in tarball.
        tarfile.TarError: If tarball is malformed.
    """
    tar_buffer = io.BytesIO(tarball_bytes)

    def _is_safe_member_name(name: str) -> bool:
        """Return True if a tar member name is safe to handle."""
        normalized = posixpath.normpath(name)
        return not (
            normalized.startswith("/")
            or normalized == ".."
            or normalized.startswith("../")
        )

    with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
        largest_member: tarfile.TarInfo | None = None
        for member in tar.getmembers():
            if (
                member.isfile()
                and member.name.endswith(".tex")
                and _is_safe_member_name(member.name)
                and (largest_member is None or member.size > largest_member.size)
            ):
                largest_member = member

        if largest_member is None:
            raise ValueError("No .tex files found in arXiv source tarball")

        file_obj = tar.extractfile(largest_member)
        if file_obj is None:
            raise ValueError(f"Could not extract {largest_member.name}")
        with file_obj:
            return file_obj.read(MAX_TEX_FILE_SIZE)
