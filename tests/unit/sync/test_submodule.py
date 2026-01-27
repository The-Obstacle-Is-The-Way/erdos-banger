"""Tests for submodule sync (SPEC-035/3).

This module tests the git submodule operations for syncing with
teorth/erdosproblems upstream data.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from erdos.core.sync.models import SubmoduleProblemData, SubmoduleSyncStatus
from erdos.core.sync.submodule import (
    SubmoduleCheckError,
    SubmoduleError,
    SubmoduleFetchError,
    SubmoduleNotInitializedError,
    SubmoduleTimeoutError,
    check_submodule_staleness,
    get_submodule_commit,
    get_submodule_path,
    load_submodule_problems,
    parse_problems_yaml,
    update_submodule,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_problems_yaml() -> str:
    """Sample problems.yaml content matching upstream format."""
    return """
- number: '1'
  prize: $500
  status:
    state: proved
    last_update: '2025-01-01'
  oeis:
    - N/A
  formalized:
    state: 'yes'
    last_update: '2025-02-01'
  tags:
    - number theory
    - primes
- number: '2'
  prize: 'no'
  status:
    state: open
  oeis:
    - A000001
    - A000002
  formalized:
    state: 'no'
  tags:
    - combinatorics
- number: '3'
  prize: $1000
  status:
    state: disproved
    last_update: '2024-06-15'
  oeis:
    - N/A
  formalized:
    state: 'no'
  tags: []
"""


@pytest.fixture
def sample_problems_dict(sample_problems_yaml: str) -> list[dict[str, Any]]:
    """Parse sample YAML into list of dicts."""
    data: list[dict[str, Any]] = yaml.safe_load(sample_problems_yaml)
    return data


@pytest.fixture
def mock_submodule_dir(tmp_path: Path, sample_problems_yaml: str) -> Path:
    """Create a mock submodule directory structure."""
    submodule_dir = tmp_path / "erdosproblems"
    data_dir = submodule_dir / "data"
    data_dir.mkdir(parents=True)

    # Write problems.yaml
    (data_dir / "problems.yaml").write_text(sample_problems_yaml, encoding="utf-8")

    # Create a fake .git file to simulate submodule
    (submodule_dir / ".git").write_text("gitdir: ../.git/modules/erdosproblems")

    return submodule_dir


# =============================================================================
# parse_problems_yaml tests
# =============================================================================


class TestParseProblemsYaml:
    """Tests for parse_problems_yaml()."""

    def test_parse_valid_yaml(self, sample_problems_dict: list[dict[str, Any]]) -> None:
        """Parse valid YAML returns dict keyed by problem_id."""
        result = parse_problems_yaml(sample_problems_dict)

        assert len(result) == 3
        assert 1 in result
        assert 2 in result
        assert 3 in result

    def test_parse_problem_data(
        self, sample_problems_dict: list[dict[str, Any]]
    ) -> None:
        """Parsed data has correct fields."""
        result = parse_problems_yaml(sample_problems_dict)

        p1 = result[1]
        assert p1.problem_id == 1
        assert p1.status == "proved"
        assert p1.status_last_update == "2025-01-01"
        assert p1.prize == 500
        assert p1.formalized is True
        assert p1.formalized_last_update == "2025-02-01"
        assert p1.oeis_ids == []  # N/A filtered out
        assert p1.tags == ["number theory", "primes"]

    def test_parse_open_problem(
        self, sample_problems_dict: list[dict[str, Any]]
    ) -> None:
        """Open problem with no prize parsed correctly."""
        result = parse_problems_yaml(sample_problems_dict)

        p2 = result[2]
        assert p2.status == "open"
        assert p2.prize == 0
        assert p2.formalized is False
        assert p2.oeis_ids == ["A000001", "A000002"]

    def test_parse_empty_list(self) -> None:
        """Empty list returns empty dict."""
        result = parse_problems_yaml([])
        assert result == {}

    def test_parse_skips_invalid_entries(self) -> None:
        """Invalid entries are skipped with warning (not raised)."""
        data: list[dict[str, Any]] = [
            {"number": "1", "status": {"state": "open"}},  # Valid
            {"prize": "$100"},  # Missing number - skip
            {"number": "abc", "status": {"state": "open"}},  # Invalid number - skip
        ]
        result = parse_problems_yaml(data)
        assert len(result) == 1
        assert 1 in result


# =============================================================================
# get_submodule_path tests
# =============================================================================


class TestGetSubmodulePath:
    """Tests for get_submodule_path()."""

    def test_returns_default_path(self) -> None:
        """Returns default path when no override."""
        from erdos.core.config import AppConfig

        config = AppConfig()  # No submodule_path set
        path = get_submodule_path(config)
        assert path == Path("data/erdosproblems")

    def test_respects_config_override(self) -> None:
        """Respects submodule_path from AppConfig."""
        from erdos.core.config import AppConfig

        config = AppConfig(submodule_path=Path("/custom/path"))
        path = get_submodule_path(config)
        assert path == Path("/custom/path")


# =============================================================================
# get_submodule_commit tests
# =============================================================================


class TestGetSubmoduleCommit:
    """Tests for get_submodule_commit()."""

    def test_returns_commit_hash(self, mock_submodule_dir: Path) -> None:
        """Returns commit hash from submodule."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="abc123def456789\n", stderr=""
            )
            commit = get_submodule_commit(mock_submodule_dir)
            assert commit == "abc123def456789"
            mock_run.assert_called_once()

    def test_strips_whitespace(self, mock_submodule_dir: Path) -> None:
        """Strips whitespace from commit hash."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="  abc123  \n", stderr=""
            )
            commit = get_submodule_commit(mock_submodule_dir)
            assert commit == "abc123"

    def test_raises_on_not_initialized(self, tmp_path: Path) -> None:
        """Raises SubmoduleNotInitializedError if submodule not initialized."""
        with pytest.raises(SubmoduleNotInitializedError, match="not initialized"):
            get_submodule_commit(tmp_path / "nonexistent")

    def test_raises_on_git_error(self, mock_submodule_dir: Path) -> None:
        """Raises SubmoduleError on git command failure."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git", "error")
            with pytest.raises(SubmoduleError, match="Failed to get"):
                get_submodule_commit(mock_submodule_dir)

    def test_raises_on_timeout(self, mock_submodule_dir: Path) -> None:
        """Raises SubmoduleTimeoutError when git times out (BUG-048)."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
            with pytest.raises(SubmoduleTimeoutError, match="timed out"):
                get_submodule_commit(mock_submodule_dir)


# =============================================================================
# load_submodule_problems tests
# =============================================================================


class TestLoadSubmoduleProblems:
    """Tests for load_submodule_problems()."""

    def test_load_from_directory(self, mock_submodule_dir: Path) -> None:
        """Loads problems from submodule directory."""
        result = load_submodule_problems(mock_submodule_dir)

        assert len(result) == 3
        assert 1 in result
        assert result[1].status == "proved"

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Raises SubmoduleError when problems.yaml missing."""
        submodule = tmp_path / "erdosproblems"
        submodule.mkdir(parents=True)

        with pytest.raises(SubmoduleError, match=r"problems\.yaml not found"):
            load_submodule_problems(submodule)

    def test_raises_on_invalid_yaml(self, tmp_path: Path) -> None:
        """Raises SubmoduleError on YAML parse error."""
        submodule = tmp_path / "erdosproblems"
        data_dir = submodule / "data"
        data_dir.mkdir(parents=True)
        (data_dir / "problems.yaml").write_text(
            "invalid: yaml: content", encoding="utf-8"
        )

        with pytest.raises(SubmoduleError, match="Failed to parse"):
            load_submodule_problems(submodule)


# =============================================================================
# check_submodule_staleness tests
# =============================================================================


class TestCheckSubmoduleStaleness:
    """Tests for check_submodule_staleness()."""

    def test_returns_false_when_up_to_date(self, mock_submodule_dir: Path) -> None:
        """Returns False (not stale) when local matches remote."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            # First call: fetch, second call: rev-list --count returns 0
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # fetch
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # rev-list
            ]
            is_stale = check_submodule_staleness(mock_submodule_dir)
            assert is_stale is False

    def test_returns_true_when_behind(self, mock_submodule_dir: Path) -> None:
        """Returns True (stale) when local is behind remote."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            # First call: fetch, second call: rev-list --count
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # fetch
                MagicMock(returncode=0, stdout="5\n", stderr=""),  # rev-list
            ]
            is_stale = check_submodule_staleness(mock_submodule_dir)
            assert is_stale is True

    def test_raises_on_network_error(self, mock_submodule_dir: Path) -> None:
        """Raises SubmoduleCheckError when network unavailable."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git", "Could not resolve host"
            )
            with pytest.raises(SubmoduleCheckError, match=r"network|fetch"):
                check_submodule_staleness(mock_submodule_dir)

    def test_raises_on_timeout(self, mock_submodule_dir: Path) -> None:
        """Raises SubmoduleTimeoutError when git fetch times out (BUG-048)."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git fetch", 120)
            with pytest.raises(SubmoduleTimeoutError, match="timed out"):
                check_submodule_staleness(mock_submodule_dir)


# =============================================================================
# update_submodule tests
# =============================================================================


class TestUpdateSubmodule:
    """Tests for update_submodule()."""

    def test_update_successful(self, mock_submodule_dir: Path) -> None:
        """Successful update returns SubmoduleSyncStatus."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch("erdos.core.sync.submodule.get_submodule_commit") as mock_commit:
                mock_commit.side_effect = ["old123", "new456"]
                status = update_submodule(mock_submodule_dir)

        assert status.previous_commit_hash == "old123"
        assert status.commit_hash == "new456"
        assert status.synced_at is not None

    def test_update_no_changes(self, mock_submodule_dir: Path) -> None:
        """Update with no changes (same commit) still succeeds."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch("erdos.core.sync.submodule.get_submodule_commit") as mock_commit:
                mock_commit.return_value = "same123"
                status = update_submodule(mock_submodule_dir)

        assert status.previous_commit_hash == "same123"
        assert status.commit_hash == "same123"

    def test_raises_on_fetch_error(self, mock_submodule_dir: Path) -> None:
        """Raises SubmoduleFetchError when git fetch fails."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git", "Network error"
            )
            with patch("erdos.core.sync.submodule.get_submodule_commit") as mock_commit:
                mock_commit.return_value = "abc123"
                with pytest.raises(SubmoduleFetchError, match=r"network|fetch"):
                    update_submodule(mock_submodule_dir)

    def test_check_only_mode(self, mock_submodule_dir: Path) -> None:
        """Check-only mode doesn't update, just checks staleness."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            # fetch returns successfully, rev-list shows 0 commits behind
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # fetch
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # rev-list
            ]
            with patch("erdos.core.sync.submodule.get_submodule_commit") as mock_commit:
                mock_commit.return_value = "abc123"
                status = update_submodule(mock_submodule_dir, check_only=True)

        assert status.stale is False
        assert status.commit_hash == "abc123"

    def test_raises_on_timeout(self, mock_submodule_dir: Path) -> None:
        """Raises SubmoduleTimeoutError when git operations time out (BUG-048)."""
        with patch("erdos.core.sync.submodule.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git fetch", 120)
            with patch("erdos.core.sync.submodule.get_submodule_commit") as mock_commit:
                mock_commit.return_value = "abc123"
                with pytest.raises(SubmoduleTimeoutError, match="timed out"):
                    update_submodule(mock_submodule_dir)


# =============================================================================
# Integration-style tests (with fixture directory)
# =============================================================================


class TestSubmoduleIntegration:
    """Integration tests using fixture directories."""

    def test_full_load_workflow(self, mock_submodule_dir: Path) -> None:
        """Full workflow: load problems and verify data integrity."""
        problems = load_submodule_problems(mock_submodule_dir)

        # Verify all problems loaded
        assert len(problems) == 3

        # Verify problem 1 (proved with prize)
        p1 = problems[1]
        assert isinstance(p1, SubmoduleProblemData)
        assert p1.status == "proved"
        assert p1.prize == 500
        assert p1.formalized is True

        # Verify problem 2 (open without prize)
        p2 = problems[2]
        assert p2.status == "open"
        assert p2.prize == 0
        assert len(p2.oeis_ids) == 2

    def test_sync_status_serialization(self) -> None:
        """SubmoduleSyncStatus can be serialized to JSON for cache."""
        status = SubmoduleSyncStatus(
            commit_hash="abc123",
            previous_commit_hash="def456",
            synced_at=datetime.now(UTC),
            problems_count=1135,
            stale=False,
        )

        # Serialize to JSON
        json_str = status.model_dump_json()
        data = json.loads(json_str)

        assert data["commit_hash"] == "abc123"
        assert data["stale"] is False

        # Deserialize back
        restored = SubmoduleSyncStatus.model_validate_json(json_str)
        assert restored.commit_hash == status.commit_hash
