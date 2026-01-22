"""Unit tests for formal_conjectures module."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import responses
import yaml

from erdos.core.formal_conjectures import (
    FORMAL_CONJECTURES_BASE_URL,
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
    LocalFormalizationInfo,
    ProvenanceEntry,
    ProvenanceFile,
    build_upstream_url,
    compute_file_sha256,
    fetch_upstream_lean_file,
    get_cache_path,
    get_local_file_path,
    has_sorry,
    load_provenance,
    load_upstream_metadata,
    parse_upstream_formalization_status,
    save_provenance,
)


# ============================================================================
# Upstream Metadata Parsing Tests
# ============================================================================


class TestParseUpstreamFormalizationStatus:
    """Tests for parse_upstream_formalization_status function."""

    def test_formalized_yes(self) -> None:
        """Parse formalized.state == 'yes'."""
        metadata = {
            "number": "6",
            "formalized": {"state": "yes", "last_update": "2025-09-18"},
        }
        result = parse_upstream_formalization_status(metadata)
        assert result.formalized is True
        assert result.state == "yes"
        assert result.last_update == "2025-09-18"

    def test_formalized_no(self) -> None:
        """Parse formalized.state == 'no'."""
        metadata = {
            "number": "42",
            "formalized": {"state": "no", "last_update": "2025-08-31"},
        }
        result = parse_upstream_formalization_status(metadata)
        assert result.formalized is False
        assert result.state == "no"

    def test_missing_formalized_key(self) -> None:
        """When formalized key is missing, formalized=False."""
        metadata = {"number": "99"}
        result = parse_upstream_formalization_status(metadata)
        assert result.formalized is False
        assert result.state is None

    def test_none_formalized_value(self) -> None:
        """When formalized value is None, formalized=False."""
        metadata = {"number": "10", "formalized": None}
        result = parse_upstream_formalization_status(metadata)
        assert result.formalized is False


class TestLoadUpstreamMetadata:
    """Tests for load_upstream_metadata function."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Load upstream metadata from valid YAML."""
        problems = [
            {
                "number": "1",
                "formalized": {"state": "yes", "last_update": "2025-08-31"},
            },
            {"number": "2", "formalized": {"state": "no", "last_update": "2025-08-31"}},
            {
                "number": "6",
                "formalized": {"state": "yes", "last_update": "2025-09-18"},
            },
        ]
        yaml_path = tmp_path / "problems.yaml"
        yaml_path.write_text(yaml.dump(problems), encoding="utf-8")

        result = load_upstream_metadata(yaml_path)
        assert len(result) == 3
        assert result[1].formalized is True
        assert result[2].formalized is False
        assert result[6].formalized is True
        assert result[6].last_update == "2025-09-18"

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Raise error when file not found."""
        yaml_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FormalConjecturesError, match="not found"):
            load_upstream_metadata(yaml_path)

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Raise error for invalid YAML."""
        yaml_path = tmp_path / "problems.yaml"
        yaml_path.write_text("{ invalid yaml", encoding="utf-8")
        with pytest.raises(FormalConjecturesError, match="parse"):
            load_upstream_metadata(yaml_path)

    def test_non_list_yaml(self, tmp_path: Path) -> None:
        """Raise error when YAML is not a list."""
        yaml_path = tmp_path / "problems.yaml"
        yaml_path.write_text("foo: bar", encoding="utf-8")
        with pytest.raises(FormalConjecturesError, match="Expected list"):
            load_upstream_metadata(yaml_path)


# ============================================================================
# URL Building Tests
# ============================================================================


class TestBuildUpstreamUrl:
    """Tests for build_upstream_url function."""

    def test_default_source(self) -> None:
        """Build URL for formal-conjectures repo."""
        url = build_upstream_url(6)
        expected = (
            f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        )
        assert url == expected

    def test_problem_id_as_string(self) -> None:
        """Build URL with problem ID as integer."""
        url = build_upstream_url(42)
        assert "42.lean" in url


class TestGetCachePath:
    """Tests for get_cache_path function."""

    def test_default_cache_path(self) -> None:
        """Get cache path under formal/lean."""
        project_path = Path("/project/formal/lean")
        result = get_cache_path(project_path, 6)
        expected = (
            project_path
            / ".upstream_cache"
            / "formal-conjectures"
            / "ErdosProblems"
            / "6.lean"
        )
        assert result == expected

    def test_cache_path_for_different_id(self) -> None:
        """Cache path varies with problem ID."""
        project_path = Path("/project/formal/lean")
        assert get_cache_path(project_path, 6) != get_cache_path(project_path, 42)


class TestGetLocalFilePath:
    """Tests for get_local_file_path function."""

    def test_zero_padded_id(self) -> None:
        """Local file path uses 3-digit zero-padded ID."""
        project_path = Path("/project/formal/lean")
        result = get_local_file_path(project_path, 6)
        assert result == project_path / "Erdos" / "Problem006.lean"

    def test_three_digit_id(self) -> None:
        """Local file path for 3-digit problem ID."""
        project_path = Path("/project/formal/lean")
        result = get_local_file_path(project_path, 999)
        assert result == project_path / "Erdos" / "Problem999.lean"


# ============================================================================
# Sorry Detection Tests
# ============================================================================


class TestHasSorry:
    """Tests for has_sorry function."""

    def test_with_sorry(self) -> None:
        """Detect sorry in content."""
        content = "theorem foo : 1 + 1 = 2 := sorry"
        assert has_sorry(content) is True

    def test_with_admit(self) -> None:
        """Detect admit in content."""
        content = "theorem bar : True := by admit"
        assert has_sorry(content) is True

    def test_sorry_in_comment(self) -> None:
        """Ignore sorry in single-line comment."""
        content = "-- This is a sorry comment\ntheorem foo : True := by trivial"
        assert has_sorry(content) is False

    def test_sorry_in_block_comment(self) -> None:
        """Ignore sorry in block comment."""
        content = "/- sorry -/\ntheorem foo : True := by trivial"
        assert has_sorry(content) is False

    def test_no_sorry(self) -> None:
        """Clean content without sorry/admit."""
        content = "theorem foo : 1 + 1 = 2 := rfl"
        assert has_sorry(content) is False

    def test_multiple_sorries(self) -> None:
        """Detect multiple sorry instances."""
        content = "theorem a := sorry\ntheorem b := sorry"
        assert has_sorry(content) is True

    def test_sorry_at_word_boundary(self) -> None:
        """Sorry must be at word boundary (not sorrythanks)."""
        content = "-- sorrythanks\ntheorem foo := rfl"
        assert has_sorry(content) is False


# ============================================================================
# File Hash Tests
# ============================================================================


class TestComputeFileSha256:
    """Tests for compute_file_sha256 function."""

    def test_compute_hash(self, tmp_path: Path) -> None:
        """Compute SHA-256 hash of file content."""
        test_file = tmp_path / "test.lean"
        content = b"theorem foo := sorry"
        test_file.write_bytes(content)

        result = compute_file_sha256(test_file)
        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Raise error for missing file."""
        with pytest.raises(FormalConjecturesError, match="not found"):
            compute_file_sha256(tmp_path / "missing.lean")


# ============================================================================
# Provenance File Tests
# ============================================================================


class TestProvenanceEntry:
    """Tests for ProvenanceEntry dataclass."""

    def test_create_entry(self) -> None:
        """Create a valid provenance entry."""
        entry = ProvenanceEntry(
            problem_id=6,
            source=FORMAL_CONJECTURES_REPO,
            url="https://example.com/6.lean",
            imported_at=datetime.now(tz=UTC),
            sha256="abc123",
        )
        assert entry.problem_id == 6
        assert entry.source == FORMAL_CONJECTURES_REPO

    def test_optional_etag(self) -> None:
        """Provenance entry with remote_etag."""
        entry = ProvenanceEntry(
            problem_id=6,
            source=FORMAL_CONJECTURES_REPO,
            url="https://example.com/6.lean",
            imported_at=datetime.now(tz=UTC),
            sha256="abc123",
            remote_etag='"5feb9d6a..."',
        )
        assert entry.remote_etag == '"5feb9d6a..."'


class TestProvenanceFile:
    """Tests for ProvenanceFile model."""

    def test_empty_provenance(self) -> None:
        """Create empty provenance file."""
        prov = ProvenanceFile()
        assert prov.schema_version == 1
        assert len(prov.imports) == 0

    def test_add_entry(self) -> None:
        """Add entry to provenance."""
        prov = ProvenanceFile()
        entry = ProvenanceEntry(
            problem_id=6,
            source=FORMAL_CONJECTURES_REPO,
            url="https://example.com/6.lean",
            imported_at=datetime.now(tz=UTC),
            sha256="abc123",
        )
        prov.imports.append(entry)
        assert len(prov.imports) == 1

    def test_find_by_problem_id(self) -> None:
        """Find entry by problem ID."""
        prov = ProvenanceFile()
        entry = ProvenanceEntry(
            problem_id=6,
            source=FORMAL_CONJECTURES_REPO,
            url="https://example.com/6.lean",
            imported_at=datetime.now(tz=UTC),
            sha256="abc123",
        )
        prov.imports.append(entry)

        found = prov.get_by_problem_id(6)
        assert found is not None
        assert found.problem_id == 6

        not_found = prov.get_by_problem_id(99)
        assert not_found is None


class TestSaveLoadProvenance:
    """Tests for save_provenance and load_provenance functions."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Save and reload provenance file."""
        prov_path = tmp_path / "Erdos" / ".provenance.yaml"
        prov = ProvenanceFile()
        entry = ProvenanceEntry(
            problem_id=6,
            source=FORMAL_CONJECTURES_REPO,
            url="https://example.com/6.lean",
            imported_at=datetime(2026, 1, 18, 10, 30, 45, tzinfo=UTC),
            sha256="abc123def456",
        )
        prov.imports.append(entry)

        save_provenance(prov_path, prov)
        assert prov_path.exists()

        loaded = load_provenance(prov_path)
        assert loaded.schema_version == 1
        assert len(loaded.imports) == 1
        assert loaded.imports[0].problem_id == 6
        assert loaded.imports[0].sha256 == "abc123def456"

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Load missing provenance returns empty file."""
        prov_path = tmp_path / ".provenance.yaml"
        loaded = load_provenance(prov_path)
        assert loaded.schema_version == 1
        assert len(loaded.imports) == 0

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid provenance YAML type raises ValueError."""
        prov_path = tmp_path / ".provenance.yaml"
        prov_path.write_text("- not a mapping\n- still not\n", encoding="utf-8")

        with pytest.raises(ValueError, match=r"expected a mapping"):
            load_provenance(prov_path)


# ============================================================================
# Fetch Upstream Tests (mocked network)
# ============================================================================


class TestFetchUpstreamLeanFile:
    """Tests for fetch_upstream_lean_file function."""

    @responses.activate
    def test_fetch_and_cache(self, tmp_path: Path) -> None:
        """Fetch file from URL and cache it."""
        project_path = tmp_path / "formal" / "lean"
        project_path.mkdir(parents=True)

        url = build_upstream_url(6)
        lean_content = b"-- Problem 6\ntheorem problem_6 := sorry"
        responses.add(responses.GET, url, body=lean_content, status=200)

        result = fetch_upstream_lean_file(project_path, 6)
        assert result.content == lean_content.decode("utf-8")
        assert result.sha256 == hashlib.sha256(lean_content).hexdigest()

        # Verify cache was written
        cache_path = get_cache_path(project_path, 6)
        assert cache_path.exists()
        assert cache_path.read_bytes() == lean_content

    @responses.activate
    def test_use_cache_when_available(self, tmp_path: Path) -> None:
        """Use cached file instead of fetching."""
        project_path = tmp_path / "formal" / "lean"
        project_path.mkdir(parents=True)

        # Pre-populate cache
        cache_path = get_cache_path(project_path, 6)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cached_content = b"-- Cached content"
        cache_path.write_bytes(cached_content)

        # No network mock - should use cache
        result = fetch_upstream_lean_file(project_path, 6)
        assert result.content == cached_content.decode("utf-8")

    @responses.activate
    def test_no_network_mode_with_cache(self, tmp_path: Path) -> None:
        """No-network mode uses cached file."""
        project_path = tmp_path / "formal" / "lean"
        project_path.mkdir(parents=True)

        # Pre-populate cache
        cache_path = get_cache_path(project_path, 6)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cached_content = b"-- Cached"
        cache_path.write_bytes(cached_content)

        result = fetch_upstream_lean_file(project_path, 6, no_network=True)
        assert result.content == cached_content.decode("utf-8")

    def test_no_network_mode_without_cache(self, tmp_path: Path) -> None:
        """No-network mode without cache raises error."""
        project_path = tmp_path / "formal" / "lean"
        project_path.mkdir(parents=True)

        with pytest.raises(FormalConjecturesError, match="not cached"):
            fetch_upstream_lean_file(project_path, 6, no_network=True)

    @responses.activate
    def test_network_error(self, tmp_path: Path) -> None:
        """Network error raises FormalConjecturesError."""
        project_path = tmp_path / "formal" / "lean"
        project_path.mkdir(parents=True)

        url = build_upstream_url(6)
        responses.add(responses.GET, url, status=404)

        with pytest.raises(FormalConjecturesError, match="404"):
            fetch_upstream_lean_file(project_path, 6)


# ============================================================================
# Local Formalization Info Tests
# ============================================================================


class TestLocalFormalizationInfo:
    """Tests for LocalFormalizationInfo."""

    def test_from_file(self, tmp_path: Path) -> None:
        """Create info from existing file."""
        project_path = tmp_path / "formal" / "lean"
        project_path.mkdir(parents=True)
        local_path = project_path / "Erdos" / "Problem006.lean"
        local_path.parent.mkdir(parents=True)
        content = "theorem foo := sorry"
        local_path.write_text(content, encoding="utf-8")

        info = LocalFormalizationInfo.from_file(local_path)
        assert info.exists is True
        assert info.path == local_path
        assert info.has_sorry is True
        assert info.sha256 == hashlib.sha256(content.encode()).hexdigest()

    def test_missing_file(self, tmp_path: Path) -> None:
        """Create info for missing file."""
        local_path = tmp_path / "missing.lean"
        info = LocalFormalizationInfo.from_file(local_path)
        assert info.exists is False
        assert info.has_sorry is None
        assert info.sha256 is None
