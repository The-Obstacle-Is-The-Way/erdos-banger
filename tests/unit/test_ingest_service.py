"""Unit tests for ingest core logic (SPEC-010-D).

Tests the ingest_problem_references function that orchestrates:
- Loading problem references
- Fetching metadata from arXiv/Crossref
- Managing manifest creation/updates
- Handling idempotence and error cases
"""

import io
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import responses
import yaml

import erdos.core.ingest as ingest_module
import erdos.core.ingest.fetch as fetch_module
from erdos.core.ingest import (
    ArxivDownloadResult,
    MetadataSource,
    _download_and_extract_arxiv,
    get_stable_key,
    ingest_problem_references,
)
from erdos.core.ingest.service import _entries_content_equal
from erdos.core.models import CLIOutput, ManifestEntry, ReferenceEntry, ReferenceRecord
from erdos.core.problem_loader import ProblemLoader


@pytest.fixture
def temp_repo_root(tmp_path: Path) -> Path:
    """Create a temporary repository root with required directories."""
    lit_dir = tmp_path / "literature"
    (lit_dir / "manifests").mkdir(parents=True)
    (lit_dir / "cache" / "arxiv").mkdir(parents=True)
    (lit_dir / "extracts" / "arxiv").mkdir(parents=True)
    return tmp_path


def test_ingest_no_references(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with a problem that has no references."""
    # Create a minimal problems.yaml with no references
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 999
  title: "Test problem"
  statement: "Test problem statement"
  category: "Graph Theory"
  references: []
""")

    # Set environment variable to use our test data
    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    result = ingest_problem_references(
        problem_id=999,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    # Should succeed with zero entries
    assert isinstance(result, CLIOutput)
    if not result.success:
        print(f"Error: {result.error}")
    assert result.success is True
    assert result.data["problem_id"] == 999
    assert result.data["references_total"] == 0
    assert result.data["entries_written"] == 0
    assert result.data["skipped"] == 0

    # Manifest should exist
    manifest_path = temp_repo_root / "literature" / "manifests" / "0999.yaml"
    assert manifest_path.exists()


@responses.activate
def test_ingest_arxiv_reference(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with an arXiv reference."""
    # Setup test data
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 998
  title: "Test problem with arXiv"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock arXiv API response
    arxiv_response_path = Path("tests/fixtures/arxiv_responses/arxiv_2203.00001.xml")
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=arxiv_response_path.read_text(),
        status=200,
    )

    # Mock arXiv tarball download (create minimal tar.gz)
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add a minimal .tex file
        tex_content = b"\\documentclass{article}\n\\begin{document}\nTest content\n\\end{document}"
        tex_info = tarfile.TarInfo(name="main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    responses.add(
        responses.GET,
        "https://arxiv.org/e-print/2203.00001",
        body=tar_buffer.getvalue(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=998,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
        source=MetadataSource.ARXIV,  # Use legacy arXiv source for this test
    )

    # Should succeed with one entry
    assert result.success is True
    assert result.data["references_total"] == 1
    assert result.data["entries_written"] == 1
    assert result.data["skipped"] == 0

    # Check manifest
    manifest_data = result.data["manifest"]
    assert len(manifest_data["entries"]) == 1
    entry = manifest_data["entries"][0]
    # arXiv response includes version suffix
    assert entry["reference"]["arxiv_id"] == "2203.00001v1"
    assert entry["cached"] is True
    assert entry["extracted"] is True


@responses.activate
def test_ingest_doi_reference(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with a DOI reference."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 997
  title: "Test problem with DOI"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Erdos1975"
      doi: "10.1007/BF01940595"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock Crossref API response
    crossref_response_path = Path(
        "tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json"
    )
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1007/BF01940595",
        body=crossref_response_path.read_text(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=997,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
        source=MetadataSource.CROSSREF,  # Use legacy Crossref source for this test
    )

    # Should succeed with one entry
    assert result.success is True
    assert result.data["references_total"] == 1
    assert result.data["entries_written"] == 1

    # Check manifest - DOI reference should not have cache/extract
    manifest_data = result.data["manifest"]
    assert len(manifest_data["entries"]) == 1
    entry = manifest_data["entries"][0]
    assert entry["reference"]["doi"] == "10.1007/BF01940595"
    assert entry["cached"] is False
    assert entry["extracted"] is False


@responses.activate
def test_ingest_merged_doi_arxiv(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with both DOI and arXiv (should create one merged entry)."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 996
  title: "Test problem with DOI+arXiv"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      doi: "10.1007/BF01940595"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock Crossref API
    crossref_response_path = Path(
        "tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json"
    )
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1007/BF01940595",
        body=crossref_response_path.read_text(),
        status=200,
    )

    # Mock arXiv tarball download
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_content = (
            b"\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}"
        )
        tex_info = tarfile.TarInfo(name="main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    responses.add(
        responses.GET,
        "https://arxiv.org/e-print/2203.00001",
        body=tar_buffer.getvalue(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=996,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
        source=MetadataSource.CROSSREF,  # Use legacy Crossref source for this test
    )

    # Should create ONE merged entry
    assert result.success is True
    assert result.data["references_total"] == 1
    assert result.data["entries_written"] == 1

    # Check merged entry has both DOI and arXiv ID
    manifest_data = result.data["manifest"]
    assert len(manifest_data["entries"]) == 1
    entry = manifest_data["entries"][0]
    assert entry["reference"]["doi"] == "10.1007/BF01940595"
    assert entry["reference"]["arxiv_id"] == "2203.00001"
    assert entry["cached"] is True  # arXiv tarball downloaded
    assert entry["extracted"] is True


@responses.activate
def test_ingest_no_download_flag(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test --no-download flag skips arXiv tarballs."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 995
  title: "Test problem"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock only arXiv metadata API (no tarball download expected)
    arxiv_response_path = Path("tests/fixtures/arxiv_responses/arxiv_2203.00001.xml")
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=arxiv_response_path.read_text(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=995,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=True,  # Should skip tarball download
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
        source=MetadataSource.ARXIV,  # Use legacy arXiv source for this test
    )

    # Should succeed but no cache/extract
    assert result.success is True
    manifest_data = result.data["manifest"]
    entry = manifest_data["entries"][0]
    assert entry["cached"] is False
    assert entry["extracted"] is False


def test_ingest_internal_error_does_not_truncate_manifest(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure unexpected exceptions don't cause partial manifests."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 994
  title: "Test problem internal error"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Boom2026"
      doi: "10.1000/test"
    - key: "Ok2026"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    def fake_fetch_reference_entry(
        ref: object,
        *,
        repo_root: Path,
        allow_download: bool,
        allow_network: bool,
        timeout: float,
        mailto: str,
        source: MetadataSource = MetadataSource.OPENALEX,
        provider: object = None,  # SPEC-022: optional provider
    ) -> ManifestEntry:
        # Unused params required by signature
        _ = repo_root, allow_download, allow_network, timeout, mailto, source, provider
        if getattr(ref, "key", "") == "Boom2026":
            raise Exception("boom")
        return ManifestEntry(
            reference=ReferenceRecord(
                doi=getattr(ref, "doi", None),
                arxiv_id=getattr(ref, "arxiv_id", None),
                title="Ok",
                authors=[],
                source="stub",
            ),
            ingested_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        ingest_module, "_fetch_reference_entry", fake_fetch_reference_entry
    )

    result = ingest_problem_references(
        problem_id=994,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=True,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    assert result.success is False

    manifest_path = temp_repo_root / "literature" / "manifests" / "0994.yaml"
    assert manifest_path.exists()
    manifest = yaml.safe_load(manifest_path.read_text())
    assert isinstance(manifest, dict)
    assert len(manifest.get("entries", [])) == 2


@responses.activate
def test_download_and_extract_arxiv_success(temp_repo_root: Path) -> None:
    """Test _download_and_extract_arxiv successfully downloads and extracts."""
    arxiv_id = "2203.00001"

    # Mock arXiv tarball download
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_content = b"\\documentclass{article}\n\\begin{document}\nTest content\n\\end{document}"
        tex_info = tarfile.TarInfo(name="main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    responses.add(
        responses.GET,
        f"https://arxiv.org/e-print/{arxiv_id}",
        body=tar_buffer.getvalue(),
        status=200,
    )

    result = _download_and_extract_arxiv(
        arxiv_id=arxiv_id,
        repo_root=temp_repo_root,
        timeout=30.0,
    )

    # Check result structure
    assert isinstance(result, ArxivDownloadResult)
    assert result.cache_path is not None
    assert result.cache_hash is not None
    assert result.extract_path is not None
    assert result.extracted is True
    assert result.error is None

    # Verify files were created
    cache_file = temp_repo_root / result.cache_path
    extract_file = temp_repo_root / result.extract_path
    assert cache_file.exists()
    assert extract_file.exists()
    assert "Test content" in extract_file.read_text()


@responses.activate
def test_download_and_extract_arxiv_download_error(temp_repo_root: Path) -> None:
    """Test _download_and_extract_arxiv handles download failures."""
    arxiv_id = "2203.00002"

    # Mock a failed download
    responses.add(
        responses.GET,
        f"https://arxiv.org/e-print/{arxiv_id}",
        status=404,
    )

    result = _download_and_extract_arxiv(
        arxiv_id=arxiv_id,
        repo_root=temp_repo_root,
        timeout=30.0,
    )

    # Should return error result
    assert isinstance(result, ArxivDownloadResult)
    assert result.cache_path is None
    assert result.cache_hash is None
    assert result.extract_path is None
    assert result.extracted is False
    assert result.error is not None
    assert "Download failed" in result.error


@responses.activate
def test_download_and_extract_arxiv_extraction_error(temp_repo_root: Path) -> None:
    """Test _download_and_extract_arxiv handles extraction failures."""
    arxiv_id = "2203.00003"

    # Mock a corrupted tarball (not valid tar.gz)
    responses.add(
        responses.GET,
        f"https://arxiv.org/e-print/{arxiv_id}",
        body=b"not a valid tarball",
        status=200,
    )

    result = _download_and_extract_arxiv(
        arxiv_id=arxiv_id,
        repo_root=temp_repo_root,
        timeout=30.0,
    )

    # Should have cache but failed extraction
    assert isinstance(result, ArxivDownloadResult)
    assert result.cache_path is not None
    assert result.cache_hash is not None
    assert result.extract_path is None
    assert result.extracted is False
    assert result.error is not None
    assert "Extraction failed" in result.error


def test_get_stable_key_with_doi() -> None:
    """Test get_stable_key with DOI identifier."""
    # Test with ReferenceEntry
    ref_entry = ReferenceEntry(key="Test2023", doi="10.1007/BF01940595")
    assert get_stable_key(ref_entry) == "doi:10.1007/bf01940595"

    # Test with ReferenceRecord
    ref_record = ReferenceRecord(
        doi="10.1007/BF01940595",
        title="Test Paper",
        source="crossref",
    )
    assert get_stable_key(ref_record) == "doi:10.1007/bf01940595"


def test_get_stable_key_with_arxiv() -> None:
    """Test get_stable_key with arXiv identifier."""
    # Test with ReferenceEntry
    ref_entry = ReferenceEntry(key="Test2023", arxiv_id="2203.00001")
    assert get_stable_key(ref_entry) == "arxiv:2203.00001"

    # Test with ReferenceRecord
    ref_record = ReferenceRecord(
        arxiv_id="2203.00001",
        title="Test Paper",
        source="arxiv",
    )
    assert get_stable_key(ref_record) == "arxiv:2203.00001"


def test_get_stable_key_with_both_doi_and_arxiv() -> None:
    """Test get_stable_key prioritizes DOI when both identifiers present."""
    # Test with ReferenceEntry
    ref_entry = ReferenceEntry(
        key="Test2023",
        doi="10.1007/BF01940595",
        arxiv_id="2203.00001",
    )
    assert get_stable_key(ref_entry) == "doi:10.1007/bf01940595"

    # Test with ReferenceRecord
    ref_record = ReferenceRecord(
        doi="10.1007/BF01940595",
        arxiv_id="2203.00001",
        title="Test Paper",
        source="crossref",
    )
    assert get_stable_key(ref_record) == "doi:10.1007/bf01940595"


def test_get_stable_key_with_no_identifiers() -> None:
    """Test get_stable_key with no identifiers returns empty string."""
    # Test with ReferenceEntry (can have no identifiers)
    ref_entry = ReferenceEntry(key="Test2023")
    assert get_stable_key(ref_entry) == ""

    # Test with ReferenceRecord with semantic_scholar_id only (not used by get_stable_key)
    ref_record = ReferenceRecord(
        semantic_scholar_id="abcd1234",
        title="Test Paper",
        source="manual",
    )
    assert get_stable_key(ref_record) == ""


def test_get_stable_key_doi_case_normalization() -> None:
    """Test get_stable_key normalizes DOI to lowercase."""
    # Mixed case DOI
    ref_entry = ReferenceEntry(key="Test2023", doi="10.1007/BF01940595")
    assert get_stable_key(ref_entry) == "doi:10.1007/bf01940595"

    # Already lowercase
    ref_entry2 = ReferenceEntry(key="Test2024", doi="10.1007/bf01940595")
    assert get_stable_key(ref_entry2) == "doi:10.1007/bf01940595"


def test_entries_content_equal_same_content() -> None:
    """Test _entries_content_equal returns True for same content."""
    entry1 = ManifestEntry(
        reference=ReferenceRecord(
            doi="10.1000/test",
            title="Test Paper",
            authors=["Author A"],
            source="crossref",
        ),
        cached=True,
        cache_path=Path("literature/cache/test.tar.gz"),
        ingested_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    # Same content, different timestamp
    entry2 = ManifestEntry(
        reference=ReferenceRecord(
            doi="10.1000/test",
            title="Test Paper",
            authors=["Author A"],
            source="crossref",
        ),
        cached=True,
        cache_path=Path("literature/cache/test.tar.gz"),
        ingested_at=datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC),  # Different timestamp
    )

    assert _entries_content_equal([entry1], [entry2]) is True


def test_entries_content_equal_different_content() -> None:
    """Test _entries_content_equal returns False for different content."""
    entry1 = ManifestEntry(
        reference=ReferenceRecord(
            doi="10.1000/test",
            title="Original Title",
            authors=["Author A"],
            source="crossref",
        ),
        ingested_at=datetime.now(UTC),
    )
    entry2 = ManifestEntry(
        reference=ReferenceRecord(
            doi="10.1000/test",
            title="Different Title",  # Different content
            authors=["Author A"],
            source="crossref",
        ),
        ingested_at=datetime.now(UTC),
    )

    assert _entries_content_equal([entry1], [entry2]) is False


def test_entries_content_equal_different_lengths() -> None:
    """Test _entries_content_equal returns False for different list lengths."""
    entry1 = ManifestEntry(
        reference=ReferenceRecord(
            doi="10.1000/test",
            title="Test Paper",
            authors=[],
            source="crossref",
        ),
        ingested_at=datetime.now(UTC),
    )

    assert _entries_content_equal([entry1], []) is False
    assert _entries_content_equal([], [entry1]) is False


def test_ingest_idempotent_no_file_change_on_repeat(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that running ingest twice produces no file diffs when content unchanged.

    DEBT-028: Manifest writes should be idempotent - running `erdos ingest <id>`
    twice with `--no-network --no-download` should not modify the manifest file
    if no content has changed.
    """
    # Create test problem with no references (simplest case)
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 888
  title: "Idempotency test problem"
  statement: "Test problem statement"
  category: "Graph Theory"
  references: []
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # First ingest
    result1 = ingest_problem_references(
        problem_id=888,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=True,
        no_network=True,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )
    assert result1.success is True

    # Read manifest content after first ingest
    manifest_path = temp_repo_root / "literature" / "manifests" / "0888.yaml"
    manifest_content_1 = manifest_path.read_text()

    # Second ingest (no force, should be idempotent)
    result2 = ingest_problem_references(
        problem_id=888,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=True,
        no_network=True,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )
    assert result2.success is True

    # Read manifest content after second ingest
    manifest_content_2 = manifest_path.read_text()

    # File content should be identical (no churn)
    assert manifest_content_1 == manifest_content_2, (
        "Manifest file changed on repeat ingest when content unchanged. "
        "This causes unnecessary git churn (DEBT-028)."
    )


def test_ingest_updates_manifest_when_content_changes(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that manifest is updated when content actually changes.

    Ensures the idempotency fix doesn't prevent legitimate updates.
    """
    # Create test problem with one reference
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 887
  title: "Content change test problem"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      doi: "10.1000/test"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Create a stub that returns deterministic data
    call_count = [0]

    def fake_fetch(
        ref: ReferenceEntry,
        *,
        repo_root: Path,
        allow_download: bool,
        allow_network: bool,
        timeout: float,
        mailto: str,
        source: MetadataSource = MetadataSource.OPENALEX,
        provider: object = None,  # SPEC-022: optional provider
    ) -> ManifestEntry:
        # Unused params required by signature
        _ = repo_root, allow_download, allow_network, timeout, mailto, source, provider
        call_count[0] += 1
        # Return different title on second call to simulate content change
        title = "First Title" if call_count[0] == 1 else "Updated Title"
        return ManifestEntry(
            reference=ReferenceRecord(
                doi=ref.doi,
                title=title,
                authors=[],
                source="stub",
            ),
            ingested_at=datetime.now(UTC),
        )

    # Patch at fetch module level where the call happens
    monkeypatch.setattr(fetch_module, "fetch_reference_entry", fake_fetch)

    # First ingest - allow network since we're mocking the fetch
    result1 = ingest_problem_references(
        problem_id=887,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=False,
        no_download=True,
        no_network=False,  # Allow network (mocked)
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )
    assert result1.success is True

    manifest_path = temp_repo_root / "literature" / "manifests" / "0887.yaml"
    manifest_data_1 = yaml.safe_load(manifest_path.read_text())

    # Second ingest with force=True to re-fetch
    result2 = ingest_problem_references(
        problem_id=887,
        repo=ProblemLoader(problems_yaml),
        repo_root=temp_repo_root,
        force=True,  # Force re-fetch
        no_download=True,
        no_network=False,  # Allow network (mocked)
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )
    assert result2.success is True

    manifest_data_2 = yaml.safe_load(manifest_path.read_text())

    # Content changed, so updated_at should be different
    assert manifest_data_1["updated_at"] != manifest_data_2["updated_at"], (
        "updated_at should change when content changes"
    )
    # Verify the title actually changed
    assert manifest_data_1["entries"][0]["reference"]["title"] == "First Title"
    assert manifest_data_2["entries"][0]["reference"]["title"] == "Updated Title"
