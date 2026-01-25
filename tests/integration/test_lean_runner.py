"""Integration tests for Lean runner (requires Lean installed)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from erdos.core.constants import LAKE_UPDATE_TIMEOUT
from erdos.core.lean import LeanRunner


lean_available = shutil.which("lean") is not None


def _ensure_mathlib_cache(project_path: Path) -> None:
    """Ensure mathlib is available and precompiled for the given Lean project.

    The repo's `formal/lean` project depends on mathlib. On a fresh checkout,
    `lake build` can take 15-30 minutes and may exceed the default LeanRunner
    timeout (2 minutes), causing CI/local `make test-all` to fail.

    We prefer the official mathlib cache (`lake exe cache get`), which is much
    faster than building mathlib from source.
    """
    lake_path = shutil.which("lake")
    if lake_path is None:
        pytest.skip("`lake` executable not found on PATH")

    mathlib_dir = project_path / ".lake" / "packages" / "mathlib"
    mathlib_olean_dir = (
        mathlib_dir / ".lake" / "build" / "lib" / "lean" / "Mathlib"
    )  # populated when cache/build is present
    if mathlib_olean_dir.exists():
        return

    # Ensure dependencies are fetched (mathlib present under .lake/packages).
    try:
        update = subprocess.run(  # noqa: S603
            [lake_path, "update"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=LAKE_UPDATE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.skip(
            f"`lake update` timed out after {LAKE_UPDATE_TIMEOUT}s. "
            "Run `cd formal/lean && lake update && lake exe cache get`."
        )
    if update.returncode != 0:
        pytest.skip(
            "Unable to fetch Lean dependencies (mathlib). "
            "Run `cd formal/lean && lake update && lake exe cache get`.\n"
            f"stderr:\n{update.stderr}"
        )

    try:
        cache = subprocess.run(  # noqa: S603
            [lake_path, "exe", "cache", "get"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=LAKE_UPDATE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.skip(
            f"`lake exe cache get` timed out after {LAKE_UPDATE_TIMEOUT}s. "
            "Run `cd formal/lean && lake exe cache get`."
        )
    if cache.returncode != 0:
        pytest.skip(
            "Unable to fetch mathlib precompiled cache. "
            "Run `cd formal/lean && lake exe cache get`.\n"
            f"stderr:\n{cache.stderr}"
        )


@pytest.mark.skipif(not lean_available, reason="Lean not installed")
@pytest.mark.requires_lean
class TestLeanRunnerIntegration:
    def test_init_creates_project(self, tmp_path: Path) -> None:
        """init creates Lean project structure."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        assert (tmp_path / "lean-toolchain").exists()
        assert (tmp_path / "lakefile.lean").exists()
        assert (tmp_path / "Erdos" / "Basic.lean").exists()
        assert (tmp_path / "Erdos.lean").exists()

    def test_check_valid_file(self, tmp_path: Path) -> None:
        """check succeeds on valid Lean file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        test_file = tmp_path / "Erdos" / "Test.lean"
        test_file.write_text("theorem simple : 1 + 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file, timeout=300)

        assert result.file == "Erdos/Test.lean"
        assert result.success, f"Lean compile failed:\n{result}"

    @pytest.mark.slow
    def test_check_formal_project_compiles(self) -> None:
        """check succeeds on the repo's formal/lean project.

        Note: Requires mathlib to be built (~15-30 min first run).
        Run `cd formal/lean && lake exe cache get` to pre-build locally.
        CI has mathlib pre-cached so this passes there.
        """
        project_root = Path(__file__).resolve().parents[2]
        project_path = project_root / "formal" / "lean"

        _ensure_mathlib_cache(project_path)

        runner = LeanRunner(project_path)
        # When mathlib isn't already built, this can still take several minutes.
        # Use a larger timeout than the default 2 minutes to avoid flakiness.
        result = runner.check(project_path / "Erdos" / "Basic.lean", timeout=1800)

        assert result.success, f"Lean compile failed:\n{result}"

    def test_check_invalid_file(self, tmp_path: Path) -> None:
        """check captures errors from invalid file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        test_file = tmp_path / "Erdos" / "Bad.lean"
        test_file.write_text("theorem bad : 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file)

        assert not result.success
        assert len(result.errors) > 0
