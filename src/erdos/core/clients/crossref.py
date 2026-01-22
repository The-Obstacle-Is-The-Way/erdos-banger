"""Crossref API client for literature metadata.

This module provides functions to fetch and parse metadata from the Crossref
REST API.

API Reference: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
"""

import logging
import time
from urllib.parse import quote

from erdos.core.models import ReferenceRecord
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


def parse_crossref_work(payload: dict[str, object], *, doi: str) -> ReferenceRecord:
    """Parse Crossref work JSON into a ReferenceRecord.

    Args:
        payload: Crossref API JSON response (full response object).
        doi: The DOI for this work (used as identifier).

    Returns:
        ReferenceRecord with Crossref metadata.

    Raises:
        ValueError: If response is an error or missing required fields.
    """
    # Check for error response
    status = payload.get("status")
    if status == "error":
        message = payload.get("message", "Unknown error")
        raise ValueError(f"Crossref error: {message}")

    # Extract the message object (the actual work data)
    message = payload.get("message")
    if not message or not isinstance(message, dict):
        raise ValueError("Invalid Crossref response: missing 'message' object")

    # Extract title (required)
    title_list = message.get("title")
    if not title_list or not isinstance(title_list, list) or not title_list[0]:
        raise ValueError("Missing required field: title")
    title = title_list[0]

    # Extract authors (optional)
    authors = []
    author_list = message.get("author", [])
    if isinstance(author_list, list):
        for author in author_list:
            if isinstance(author, dict):
                given = author.get("given", "")
                family = author.get("family", "")
                if family:
                    # Format as "Given Family"
                    name = f"{given} {family}".strip()
                    authors.append(name)

    # Extract year (optional) from published-print
    year = None
    published_print = message.get("published-print")
    if published_print and isinstance(published_print, dict):
        date_parts = published_print.get("date-parts")
        if date_parts and isinstance(date_parts, list) and len(date_parts) > 0:
            year_parts = date_parts[0]
            if isinstance(year_parts, list) and len(year_parts) > 0:
                year = year_parts[0]

    # Extract venue (optional) from container-title
    venue = None
    container_title = message.get("container-title")
    if container_title and isinstance(container_title, list) and container_title:
        venue = container_title[0]

    return ReferenceRecord(
        doi=doi,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        source="crossref",
    )


def fetch_crossref_work(
    doi: str, *, mailto: str, timeout: float = 30.0
) -> dict[str, object]:
    """Fetch Crossref work metadata via REST API.

    Args:
        doi: The DOI to retrieve (e.g., "10.1007/BF01940595").
        mailto: Contact email for Crossref polite pool.
        timeout: HTTP timeout in seconds.

    Returns:
        Crossref API JSON response as a dictionary.

    Raises:
        requests.HTTPError: If HTTP request fails (e.g., 404 for not found).
        requests.Timeout: If request times out after all retries.
        requests.ConnectionError: If connection fails after all retries.
    """
    encoded_doi = quote(doi, safe="/")
    url = f"https://api.crossref.org/works/{encoded_doi}"
    params = {"mailto": mailto}
    headers = {
        "User-Agent": f"erdos-banger/1.0 (https://github.com/The-Obstacle-Is-The-Way/erdos-banger; mailto:{mailto})"
    }

    logger.debug("Fetching Crossref metadata for DOI: %s", doi)
    start_time = time.monotonic()

    response = fetch_with_retry(url, timeout=timeout, params=params, headers=headers)
    elapsed = time.monotonic() - start_time
    logger.debug(
        "Crossref response: %d bytes in %.2fs (status %d)",
        len(response.content),
        elapsed,
        response.status_code,
    )

    return response.json()  # type: ignore[no-any-return]
