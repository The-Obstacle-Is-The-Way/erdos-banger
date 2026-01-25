"""Tests for erdos sync proof command (SPEC-035)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from erdos.core.sync.proof_service import sync_proof_links


# =============================================================================
# Fixtures
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sync" / "forum"


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / name
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def html_thread_with_github() -> str:
    """Forum thread with a GitHub proof link."""
    return load_fixture("thread_347_with_github_link.html")


@pytest.fixture
def html_thread_no_links() -> str:
    """Forum thread with no proof links."""
    return load_fixture("thread_no_links.html")


@pytest.fixture
def html_thread_multiple_links() -> str:
    """Forum thread with multiple links."""
    return load_fixture("thread_with_multiple_links.html")


# =============================================================================
# sync_proof_links core logic tests
# =============================================================================


class TestSyncProofLinks:
    """Tests for the sync_proof_links core logic."""

    def test_extracts_github_link(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Extract GitHub link from forum HTML."""
        result = sync_proof_links(
            347,
            html_content=html_thread_with_github,
            cache_path=tmp_path / "proofs",
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["problem_id"] == 347
        assert result.data["links_count"] == 1
        assert (
            result.data["links"][0]["url"]
            == "https://github.com/mathprover123/erdos-347-proof"
        )

    def test_extracts_multiple_links(
        self, html_thread_multiple_links: str, tmp_path: Path
    ) -> None:
        """Extract multiple links from forum HTML."""
        result = sync_proof_links(
            100,
            html_content=html_thread_multiple_links,
            cache_path=tmp_path / "proofs",
        )

        assert result.success is True
        assert result.data["links_count"] == 3

    def test_handles_no_links(self, html_thread_no_links: str, tmp_path: Path) -> None:
        """Handle forum with no proof links gracefully."""
        result = sync_proof_links(
            50,
            html_content=html_thread_no_links,
            cache_path=tmp_path / "proofs",
        )

        assert result.success is True
        assert result.data["links_count"] == 0
        assert result.data["links"] == []

    def test_dry_run_does_not_write(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Dry run mode does not write files."""
        result = sync_proof_links(
            347,
            html_content=html_thread_with_github,
            cache_path=tmp_path / "proofs",
            dry_run=True,
        )

        assert result.success is True
        # Cache directory should not exist
        assert not (tmp_path / "proofs" / "347").exists()

    def test_writes_links_json(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Sync writes links.json to cache directory."""
        result = sync_proof_links(
            347,
            html_content=html_thread_with_github,
            cache_path=tmp_path / "proofs",
        )

        assert result.success is True
        links_path = tmp_path / "proofs" / "347" / "links.json"
        assert links_path.exists()

        with links_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["problem_id"] == 347
        assert len(data["links"]) == 1

    def test_writes_provenance_json(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Discover-only mode records provenance.json (best-effort)."""
        result = sync_proof_links(
            347,
            html_content=html_thread_with_github,
            cache_path=tmp_path / "proofs",
        )

        assert result.success is True
        provenance_path = tmp_path / "proofs" / "347" / "provenance.json"
        assert provenance_path.exists()

        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        assert provenance["problem_id"] == 347
        assert (
            provenance["repo_url"] == "https://github.com/mathprover123/erdos-347-proof"
        )

    def test_json_output_contract(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Verify JSON output matches spec contract."""
        result = sync_proof_links(
            347,
            html_content=html_thread_with_github,
            cache_path=tmp_path / "proofs",
        )

        assert result.success is True
        data = result.data

        # Check required fields per SPEC-035
        assert "problem_id" in data
        assert "links" in data
        assert isinstance(data["links"], list)
        assert "provenance_path" in data
        assert "verification_status" in data

        # Each link must have url field
        for link in data["links"]:
            assert "url" in link


# =============================================================================
# CLI integration tests
# =============================================================================


class TestProofCLI:
    """CLI integration tests for erdos sync proof."""

    def test_help_message(
        self, runner: CliRunner, strip_ansi: Callable[[str], str]
    ) -> None:
        """Help message displays correctly."""
        result = runner.invoke(app, ["sync", "proof", "--help"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Extract proof repository links" in output

    def test_json_output(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """JSON output mode works correctly."""
        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            # Mock to return parsed data from fixture
            from erdos.core.sync.forum import parse_forum_html

            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["--json", "sync", "proof", "347"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["problem_id"] == 347
        assert data["data"]["links_count"] == 1

    def test_dry_run_option(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--dry-run option prevents file writes."""
        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            from erdos.core.sync.forum import parse_forum_html

            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["sync", "proof", "347", "--dry-run"])

        assert result.exit_code == 0
        # Should not create cache directory
        assert not (tmp_path / "proofs" / "347").exists()

    def test_network_error_handling(self, runner: CliRunner, tmp_path: Path) -> None:
        """Network errors are handled gracefully."""
        from erdos.core.sync.forum import ForumFetchError

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            mock_fetch.side_effect = ForumFetchError("Connection refused")

            result = runner.invoke(app, ["--json", "sync", "proof", "347"])

        assert result.exit_code == ExitCode.NETWORK_ERROR.value
        data = json.loads(result.output)
        assert data["success"] is False
        assert "Connection refused" in data["error"]["message"]

    def test_not_found_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """404 errors return NOT_FOUND exit code."""
        from erdos.core.sync.forum import ForumFetchError

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            mock_fetch.side_effect = ForumFetchError(
                "Forum thread not found", status_code=404
            )

            result = runner.invoke(app, ["--json", "sync", "proof", "9999"])

        assert result.exit_code == ExitCode.NOT_FOUND.value


# =============================================================================
# Verification tests (--verify flag)
# =============================================================================


class TestProofVerification:
    """Tests for the --verify flag functionality."""

    def test_verify_flag_in_help(
        self, runner: CliRunner, strip_ansi: Callable[[str], str]
    ) -> None:
        """--verify flag appears in help."""
        result = runner.invoke(app, ["sync", "proof", "--help"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "--verify" in output

    def test_verify_with_no_links(
        self, runner: CliRunner, html_thread_no_links: str, tmp_path: Path
    ) -> None:
        """--verify with no links returns appropriate status."""
        cache_path = tmp_path / "proofs"
        result = sync_proof_links(
            50,
            html_content=html_thread_no_links,
            verify=True,
            cache_path=cache_path,
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["verification_status"] == "unverified"
        assert "No proof links found" in result.data.get("verification_error", "")

    def test_verify_calls_verification(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--verify flag triggers verification pipeline."""
        from erdos.core.sync.forum import parse_forum_html
        from erdos.core.sync.models import VerificationStatus, VerificationStrength
        from erdos.core.sync.proofs import VerificationResult

        mock_result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            strength=VerificationStrength.NO_SORRIES,
            repo_commit="abc123",
            toolchain="leanprover/lean4:v4.3.0",
            verified_files=["Problem347.lean"],
            log_content="Build succeeded",
        )

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
            patch(
                "erdos.core.sync.proof_service.verify_proof", return_value=mock_result
            ),
        ):
            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["--json", "sync", "proof", "347", "--verify"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["verification_status"] == "verified"
        assert data["data"]["verification_strength"] == "no_sorries"
        assert data["data"]["verified_commit"] == "abc123"

    def test_verify_saves_provenance(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--verify saves provenance.json with verification details."""
        from erdos.core.sync.forum import parse_forum_html
        from erdos.core.sync.models import VerificationStatus, VerificationStrength
        from erdos.core.sync.proofs import VerificationResult

        mock_result = VerificationResult(
            status=VerificationStatus.INCONCLUSIVE,
            strength=VerificationStrength.BUILD_ONLY,
            repo_commit="abc123",
            error="Could not identify problem file",
            log_content="Build passed",
        )

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
            patch(
                "erdos.core.sync.proof_service.verify_proof", return_value=mock_result
            ),
        ):
            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["sync", "proof", "347", "--verify"])

        assert result.exit_code == 0

        # Check provenance was saved
        provenance_path = tmp_path / "proofs" / "347" / "provenance.json"
        assert provenance_path.exists()

        with provenance_path.open(encoding="utf-8") as f:
            provenance = json.load(f)

        assert provenance["problem_id"] == 347
        assert provenance["verification_status"] == "inconclusive"
        assert provenance["verification_strength"] == "build_only"

    def test_verify_saves_log(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--verify saves verification log."""
        from erdos.core.sync.forum import parse_forum_html
        from erdos.core.sync.models import VerificationStatus, VerificationStrength
        from erdos.core.sync.proofs import VerificationResult

        mock_result = VerificationResult(
            status=VerificationStatus.FAILED,
            strength=VerificationStrength.NONE,
            error="Build failed",
            log_content="Error: missing dependency Mathlib",
        )

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
            patch(
                "erdos.core.sync.proof_service.verify_proof", return_value=mock_result
            ),
        ):
            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["sync", "proof", "347", "--verify"])

        assert result.exit_code == 0

        # Check log was saved
        log_path = tmp_path / "proofs" / "347" / "verify.log"
        assert log_path.exists()
        assert "missing dependency Mathlib" in log_path.read_text(encoding="utf-8")

    def test_verify_dry_run_no_write(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--verify --dry-run does not write files."""
        from erdos.core.sync.forum import parse_forum_html
        from erdos.core.sync.models import VerificationStatus, VerificationStrength
        from erdos.core.sync.proofs import VerificationResult

        mock_result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            strength=VerificationStrength.NO_SORRIES,
            repo_commit="abc123",
        )

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
            patch(
                "erdos.core.sync.proof_service.verify_proof", return_value=mock_result
            ),
        ):
            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(
                app, ["--json", "sync", "proof", "347", "--verify", "--dry-run"]
            )

        assert result.exit_code == 0
        # Should not create any files
        assert not (tmp_path / "proofs" / "347").exists()

    def test_verify_json_output_contract(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--verify JSON output matches SPEC-035 contract."""
        from erdos.core.sync.forum import parse_forum_html
        from erdos.core.sync.models import VerificationStatus, VerificationStrength
        from erdos.core.sync.proofs import VerificationResult

        mock_result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            strength=VerificationStrength.NO_SORRIES,
            repo_commit="abc123",
            toolchain="leanprover/lean4:v4.3.0",
            verified_files=["Problem347.lean"],
        )

        with (
            patch("erdos.core.sync.proof_service.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
            patch(
                "erdos.core.sync.proof_service.verify_proof", return_value=mock_result
            ),
        ):
            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["--json", "sync", "proof", "347", "--verify"])

        assert result.exit_code == 0
        data = json.loads(result.output)

        # Check required fields per SPEC-035 JSON contract
        d = data["data"]
        assert "problem_id" in d
        assert "links" in d
        assert "provenance_path" in d
        assert "verification_status" in d

        # Additional verification fields
        assert "verification_strength" in d
        assert "verified_repo" in d
        assert "verified_commit" in d
        assert "verified_files" in d
