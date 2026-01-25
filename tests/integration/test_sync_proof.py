"""Integration tests for proof sync and verification (requires network/Lean).

These tests verify the proof sync functionality works correctly with real data.
Use `pytest -m requires_network` to run network-dependent tests.
Use `pytest -m requires_lean` to run Lean-dependent tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.sync.proof_service import sync_proof_links


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


# =============================================================================
# Network tests (forum fetching)
# =============================================================================


@pytest.mark.requires_network
class TestProofSyncNetwork:
    """Tests that require network access to erdosproblems.com."""

    def test_fetch_real_forum_thread(self, tmp_path: Path) -> None:
        """Fetch a real forum thread from erdosproblems.com.

        Note: We use problem #1 which should have a forum thread.
        This test verifies network fetching works but doesn't require
        the thread to have proof links (that may change over time).
        """
        from unittest.mock import patch

        with patch(
            "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(1)  # Problem #1

        # Should succeed (even if no links found)
        assert result.success is True
        assert result.data is not None
        assert result.data["problem_id"] == 1
        assert "links" in result.data
        assert "verification_status" in result.data

    def test_cli_real_forum_fetch(self, runner: CliRunner, tmp_path: Path) -> None:
        """CLI command fetches real forum data."""
        from unittest.mock import patch

        with patch(
            "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = runner.invoke(app, ["--json", "sync", "proof", "1"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["problem_id"] == 1

    def test_handles_nonexistent_problem(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Handles non-existent problem gracefully."""
        from unittest.mock import patch

        with patch(
            "erdos.core.sync.proof_service.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            # Use a very high problem number that shouldn't exist
            result = runner.invoke(app, ["--json", "sync", "proof", "99999"])

        # Should return an error (404 or similar)
        data = json.loads(result.output)
        assert result.exit_code != 0
        assert data["success"] is False


# =============================================================================
# Lean tests (verification)
# =============================================================================


@pytest.mark.requires_lean
class TestProofVerificationLean:
    """Tests that require Lean/elan installed.

    These tests verify the actual Lean verification pipeline works.
    They are skipped if Lean is not available.
    """

    @pytest.fixture(autouse=True)
    def check_lean_available(self) -> None:
        """Skip if Lean/lake is not available."""
        import shutil

        if shutil.which("lake") is None:
            pytest.skip("lake command not found (Lean not installed)")

    def test_verify_fixture_repo_with_sorry(self, tmp_path: Path) -> None:
        """Verify fixture repo with sorry fails verification."""
        import shutil

        from erdos.core.sync.proofs import (
            check_no_sorries,
            run_lake_build,
        )

        # Copy fixture to work dir
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sync" / "proof_repo"
        repo_dir = tmp_path / "test_repo"
        shutil.copytree(fixtures_dir / "with_sorry", repo_dir)

        # Build should succeed (sorry is just a warning/placeholder)
        build_ok, build_log = run_lake_build(repo_dir, timeout=300)

        # Note: This may fail if toolchain not installed
        # We don't assert build_ok since it depends on having the toolchain
        if not build_ok:
            pytest.skip(f"Build failed (toolchain issue?): {build_log[:200]}")

        # Check for sorries should detect them
        lean_file = repo_dir / "Problem347.lean"
        no_sorry, check_log = check_no_sorries(repo_dir, lean_file)

        # Should detect the sorry
        assert no_sorry is False, (
            f"Expected sorry to be detected, got no_sorry={no_sorry}. "
            f"Log preview: {check_log[:200]}"
        )

    def test_verify_fixture_repo_no_sorry(self, tmp_path: Path) -> None:
        """Verify fixture repo without sorry passes verification."""
        import shutil

        from erdos.core.sync.proofs import (
            check_no_sorries,
            run_lake_build,
        )

        # Copy fixture to work dir
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sync" / "proof_repo"
        repo_dir = tmp_path / "test_repo"
        shutil.copytree(fixtures_dir / "no_sorry", repo_dir)

        # Build should succeed
        build_ok, build_log = run_lake_build(repo_dir, timeout=300)

        if not build_ok:
            pytest.skip(f"Build failed (toolchain issue?): {build_log[:200]}")

        # Check for sorries should pass
        lean_file = repo_dir / "Problem347.lean"
        no_sorry, check_log = check_no_sorries(repo_dir, lean_file)

        # Should have no sorries
        assert no_sorry is True, (
            f"Expected no sorry, got no_sorry={no_sorry}. Log preview: {check_log[:200]}"
        )


# =============================================================================
# Combined network + Lean tests
# =============================================================================


@pytest.mark.requires_network
@pytest.mark.requires_lean
@pytest.mark.e2e
@pytest.mark.slow
class TestProofVerificationEndToEnd:
    """End-to-end verification tests requiring both network and Lean.

    These tests clone real repositories and verify them.
    They are slow and may fail if external repos change.
    """

    @pytest.fixture(autouse=True)
    def check_requirements(self) -> None:
        """Skip if requirements not met."""
        import shutil

        if shutil.which("lake") is None:
            pytest.skip("lake command not found")
        if shutil.which("git") is None:
            pytest.skip("git command not found")

    def test_clone_and_verify_real_repo(self, tmp_path: Path) -> None:
        """Clone a real Lean repository and verify it builds.

        Uses the batteries repository (formerly std4) as a known-good target.
        Note: This is a slow test due to network dependency.
        """
        from erdos.core.sync.proofs import clone_repository

        # Clone a small known repo (we use depth=1 for speed)
        # Using batteries (formerly std4) which is smaller than Mathlib
        # See DEBT-098 for history on std4 -> batteries rename
        result = clone_repository(
            "https://github.com/leanprover-community/batteries",
            tmp_path / "batteries",
            timeout=120,
            depth=1,
        )

        # Clone should succeed
        assert result.success is True, f"Clone failed: {result.error}"
        assert result.commit is not None
        assert len(result.commit) == 40  # Full SHA

        # Verify the repo directory exists
        assert (tmp_path / "batteries").exists()
        # Batteries uses lakefile.toml (Lean 4 convention)
        assert (tmp_path / "batteries" / "lakefile.toml").exists()
