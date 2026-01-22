"""OpenAlex API client for academic metadata.

OpenAlex (https://openalex.org/) is a fully open catalog of scholarly works
with 271M+ works. This client provides access to work metadata using the
OpenAlex REST API.

API Reference: https://docs.openalex.org/
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from erdos.core.models import OpenAccessStatus, ReferenceRecord
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenAlexConfig:
    """OpenAlex client configuration."""

    email: str | None = None
    api_key: str | None = None
    timeout: float = 30.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> OpenAlexConfig:
        """Create config from environment variables.

        Checks ERDOS_MAILTO first, then OPENALEX_EMAIL for email.
        Checks OPENALEX_API_KEY for API key authentication.
        """
        return cls(
            email=os.getenv("ERDOS_MAILTO") or os.getenv("OPENALEX_EMAIL"),
            api_key=os.getenv("OPENALEX_API_KEY"),
        )


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Convert OpenAlex inverted index to plain text abstract.

    OpenAlex stores abstracts as inverted indexes where each word maps to
    its positions in the text. This function reconstructs the original text.

    Args:
        inverted_index: Word -> positions mapping from OpenAlex.

    Returns:
        Plain text abstract or None if input is empty/None.
    """
    if not inverted_index:
        return None

    # Build (position, word) pairs
    words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))

    # Sort by position and join
    words.sort(key=lambda x: x[0])
    return " ".join(word for _, word in words)


_ARXIV_ABS_PREFIX = "https://arxiv.org/abs/"
_ARXIV_DOI_PREFIX = "https://doi.org/10.48550/arxiv."


def extract_arxiv_id(ids: dict[str, Any]) -> str | None:
    """Extract arXiv ID from an OpenAlex work `ids` object.

    Args:
        ids: OpenAlex IDs object containing various identifiers.

    Returns:
        arXiv ID (e.g., "2301.00001" or "math/0703001") or None if not present.
    """
    # Some OpenAlex payloads may include an explicit arXiv URL (defensive support).
    arxiv_url = ids.get("arxiv")
    if isinstance(arxiv_url, str) and arxiv_url:
        if arxiv_url.startswith(_ARXIV_ABS_PREFIX):
            return arxiv_url[len(_ARXIV_ABS_PREFIX) :]
        if "/abs/" in arxiv_url:
            return arxiv_url.split("/abs/")[-1]
        return arxiv_url.rsplit("/", 1)[-1]

    # OpenAlex commonly exposes arXiv via the arXiv DataCite DOI in ids.doi:
    #   https://doi.org/10.48550/arxiv.<arxiv_id>
    doi_url = ids.get("doi")
    if (
        isinstance(doi_url, str)
        and doi_url
        and doi_url.lower().startswith(_ARXIV_DOI_PREFIX)
    ):
        return doi_url[len(_ARXIV_DOI_PREFIX) :]

    return None


def _extract_arxiv_id_from_landing_page_url(url: str | None) -> str | None:
    """Extract arXiv ID from an OpenAlex landing_page_url."""
    if not url or not isinstance(url, str):
        return None
    match = re.search(r"arxiv\\.org/abs/([^\\s?#]+)", url)
    if not match:
        return None
    return match.group(1)


def extract_arxiv_id_from_work(work: dict[str, Any]) -> str | None:
    """Extract arXiv ID from a full OpenAlex work object.

    OpenAlex does not provide an `ids.arxiv` field. The arXiv identifier is usually
    discoverable via either:
    - ids.doi (arXiv DataCite DOI: 10.48550/arxiv.<id>)
    - primary_location.landing_page_url (arxiv.org/abs/<id>)
    """
    ids = work.get("ids")
    if isinstance(ids, dict) and (arxiv_id := extract_arxiv_id(ids)):
        return arxiv_id

    primary_loc = work.get("primary_location")
    if isinstance(primary_loc, dict):
        landing = primary_loc.get("landing_page_url")
        if isinstance(landing, str):
            return _extract_arxiv_id_from_landing_page_url(landing)

    return None


def find_pdf_url(work: dict[str, Any]) -> str | None:
    """Find best PDF URL from OpenAlex work locations.

    Checks primary location first, then alternate locations.

    Args:
        work: OpenAlex work object.

    Returns:
        PDF URL or None if not available.
    """
    # Check primary location first
    primary: dict[str, Any] = work.get("primary_location", {}) or {}
    pdf_url: str | None = primary.get("pdf_url")
    if pdf_url:
        return pdf_url

    # Check alternate locations
    for loc in work.get("locations", []):
        pdf_url = loc.get("pdf_url")
        if pdf_url:
            return pdf_url

    return None


def _map_oa_status(oa: dict[str, Any] | None) -> OpenAccessStatus:
    """Map OpenAlex OA status to our enum.

    Args:
        oa: OpenAlex open_access object.

    Returns:
        OpenAccessStatus enum value.
    """
    if not oa:
        return OpenAccessStatus.UNKNOWN

    status = oa.get("oa_status", "").lower()
    mapping = {
        "gold": OpenAccessStatus.GOLD,
        "green": OpenAccessStatus.GREEN,
        "bronze": OpenAccessStatus.BRONZE,
        "hybrid": OpenAccessStatus.HYBRID,
        "closed": OpenAccessStatus.CLOSED,
    }
    return mapping.get(status, OpenAccessStatus.UNKNOWN)


def openalex_to_reference(work: dict[str, Any]) -> ReferenceRecord:
    """Convert OpenAlex work to ReferenceRecord.

    Args:
        work: OpenAlex work object from API.

    Returns:
        ReferenceRecord with OpenAlex metadata.
    """
    # Extract DOI (remove https://doi.org/ prefix). Prefer work.doi, fall back to ids.doi.
    doi_raw = work.get("doi") or ""
    if not doi_raw:
        ids = work.get("ids")
        if isinstance(ids, dict):
            doi_raw = ids.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None

    arxiv_id = extract_arxiv_id_from_work(work)

    # Extract authors from authorships
    authors: list[str] = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        if author.get("display_name"):
            authors.append(author["display_name"])

    # Extract venue from primary location
    primary_loc = work.get("primary_location", {}) or {}
    source = primary_loc.get("source", {}) or {}
    venue = source.get("display_name")

    # Extract concepts (top 5)
    concepts: list[str] = []
    for concept in work.get("concepts", [])[:5]:
        if concept.get("display_name"):
            concepts.append(concept["display_name"])

    # Map OA status
    oa = work.get("open_access", {})
    oa_status = _map_oa_status(oa)

    return ReferenceRecord(
        doi=doi or None,
        arxiv_id=arxiv_id,
        title=work.get("title", ""),
        authors=authors,
        year=work.get("publication_year"),
        venue=venue,
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        openalex_id=work.get("id"),
        cited_by_count=work.get("cited_by_count"),
        concepts=concepts,
        pdf_url=find_pdf_url(work),
        oa_status=oa_status,
        source="openalex",
    )


class OpenAlexClient:
    """Client for OpenAlex API.

    Provides methods to fetch academic metadata by DOI, arXiv ID,
    or search query. Uses retry logic for transient failures.
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(self, config: OpenAlexConfig | None = None):
        """Initialize client with configuration.

        Args:
            config: Client configuration. If None, loads from environment.
        """
        self.config = config or OpenAlexConfig.from_env()

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        """Build request parameters with optional mailto and api_key."""
        params = dict(kwargs)
        if self.config.email:
            params["mailto"] = self.config.email
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        return params

    def _fetch(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch JSON from OpenAlex API with retry.

        Args:
            url: API endpoint URL.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            requests.HTTPError: On non-retryable HTTP errors.
            requests.Timeout: After all retries exhausted.
        """
        logger.debug("Fetching OpenAlex: %s", url)
        start_time = time.monotonic()

        response = fetch_with_retry(
            url,
            timeout=self.config.timeout,
            max_attempts=self.config.max_retries,
            params=params,
        )
        elapsed = time.monotonic() - start_time
        logger.debug(
            "OpenAlex response: %d bytes in %.2fs (status %d)",
            len(response.content),
            elapsed,
            response.status_code,
        )

        return response.json()  # type: ignore[no-any-return]

    def get_by_doi(self, doi: str) -> ReferenceRecord:
        """Fetch work by DOI.

        Args:
            doi: DOI without prefix (e.g., "10.1038/nature12373").

        Returns:
            ReferenceRecord with work metadata.

        Raises:
            requests.HTTPError: If work not found (404) or other HTTP error.
        """
        # Encode DOI for URL, keeping "/" unencoded (per OpenAlex API format)
        encoded_doi = quote(doi, safe="/")
        url = f"{self.BASE_URL}/works/https://doi.org/{encoded_doi}"
        params = self._params()

        work = self._fetch(url, params)
        return openalex_to_reference(work)

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord:
        """Fetch work by arXiv ID.

        Args:
            arxiv_id: arXiv identifier (e.g., "2301.00001").

        Returns:
            ReferenceRecord with work metadata.

        Raises:
            ValueError: If no work found for the arXiv ID.
        """
        # OpenAlex does not support an ids.arxiv filter. arXiv e-prints are
        # deterministically addressable via their DataCite DOIs:
        #   10.48550/arxiv.<arxiv_id_without_version>
        arxiv_id_clean = re.sub(r"v\d+$", "", arxiv_id)
        doi = f"10.48550/arxiv.{arxiv_id_clean}"

        try:
            ref = self.get_by_doi(doi)
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None and response.status_code == 404:
                raise ValueError(f"No work found for arXiv:{arxiv_id_clean}") from e
            raise

        # Ensure the arXiv ID is populated consistently.
        ref.arxiv_id = arxiv_id_clean
        return ref

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract.

        Args:
            query: Search query string.
            limit: Maximum results to return.

        Returns:
            List of matching ReferenceRecords.
        """
        url = f"{self.BASE_URL}/works"
        params = self._params(search=query, per_page=limit)

        response = self._fetch(url, params)
        results = response.get("results", [])

        return [openalex_to_reference(work) for work in results]

    def get_citations(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Get works that cite this work.

        Args:
            work_id: OpenAlex work ID (e.g., "https://openalex.org/W2741809807").
            limit: Maximum results to return.

        Returns:
            List of citing ReferenceRecords.
        """
        url = f"{self.BASE_URL}/works"
        params = self._params(filter=f"cites:{work_id}", per_page=limit)

        response = self._fetch(url, params)
        results = response.get("results", [])

        return [openalex_to_reference(work) for work in results]

    def get_references(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Get works cited by this work.

        Args:
            work_id: OpenAlex work ID (e.g., "https://openalex.org/W2741809807").
            limit: Maximum results to return.

        Returns:
            List of referenced ReferenceRecords.
        """
        url = f"{self.BASE_URL}/works"
        params = self._params(filter=f"cited_by:{work_id}", per_page=limit)

        response = self._fetch(url, params)
        results = response.get("results", [])

        return [openalex_to_reference(work) for work in results]
