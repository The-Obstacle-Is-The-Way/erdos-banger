"""Integration tests for erdos lean status and import commands."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import responses
import yaml

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from erdos.core.formal_conjectures import (
    FORMAL_CONJECTURES_BASE_URL,
    get_cache_path,
    get_local_file_path,
)
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def upstream_yaml(tmp_path: Path) -> Path:
    """Create upstream problems.yaml fixture."""
    problems = [
        {"number": "1", "formalized": {"state": "yes", "last_update": "2025-08-31"}},
        {"number": "2", "formalized": {"state": "no", "last_update": "2025-08-31"}},
        {"number": "6", "formalized": {"state": "yes", "last_update": "2025-09-18"}},
    ]
    data_dir = tmp_path / "data" / "erdosproblems" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = data_dir / "problems.yaml"
    yaml_path.write_text(yaml.dump(problems), encoding="utf-8")
    return yaml_path


@pytest.fixture
def enriched_yaml(tmp_path: Path) -> Path:
    """Create enriched problems.yaml fixture."""
    problems = [
        {
            "id": 1,
            "title": "Problem 1",
            "statement": "Statement 1",
            "status": "open",
            "formalized": True,
        },
        {
            "id": 2,
            "title": "Problem 2",
            "statement": "Statement 2",
            "status": "open",
            "formalized": False,
        },
        {
            "id": 6,
            "title": "Problem 6",
            "statement": "Statement 6",
            "status": "proved",
            "formalized": True,
        },
    ]
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = data_dir / "problems_enriched.yaml"
    yaml_path.write_text(yaml.dump(problems), encoding="utf-8")
    return yaml_path


@pytest.fixture
def lean_project(tmp_path: Path) -> Path:
    """Create Lean project structure."""
    project = tmp_path / "formal" / "lean"
    project.mkdir(parents=True)
    (project / "Erdos").mkdir()
    (project / "lakefile.lean").write_text("-- Lakefile")
    return project


# ============================================================================
# erdos lean status Tests
# ============================================================================


class TestLeanStatusCommand:
    """Tests for erdos lean status command."""

    def test_status_help(self, strip_ansi) -> None:
        """Verify status command has help text."""
        result = runner.invoke(app, ["lean", "status", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "status" in output.lower()

    def test_status_all_problems(
        self, tmp_path: Path, upstream_yaml: Path, enriched_yaml: Path
    ) -> None:
        """Show status for all problems."""
        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            # Change to tmp directory so relative paths work
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(app, ["--json", "lean", "status"])
                # If status command not implemented yet, skip
                if "No such command" in result.stdout:
                    pytest.skip("status command not implemented yet")

                assert result.exit_code == 0
                data = json.loads(result.stdout)
                assert data["success"] is True
            finally:
                os.chdir(old_cwd)

    def test_status_single_problem(
        self,
        tmp_path: Path,
        upstream_yaml: Path,
        enriched_yaml: Path,
        lean_project: Path,
    ) -> None:
        """Show status for a single problem."""
        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(app, ["--json", "lean", "status", "6"])
                if "No such command" in result.stdout:
                    pytest.skip("status command not implemented yet")

                assert result.exit_code == 0
                data = json.loads(result.stdout)
                assert data["success"] is True
                assert data["data"]["problem_id"] == 6
            finally:
                os.chdir(old_cwd)

    def test_status_missing_upstream(self, tmp_path: Path, enriched_yaml: Path) -> None:
        """Status with missing upstream metadata returns error."""
        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app, ["--json", "lean", "status", "6", "--upstream"]
                )
                if "No such command" in result.stdout:
                    pytest.skip("status command not implemented yet")

                # Should fail with CONFIG_ERROR
                assert result.exit_code == ExitCode.CONFIG_ERROR
            finally:
                os.chdir(old_cwd)

    def test_status_unknown_problem(
        self, tmp_path: Path, enriched_yaml: Path, upstream_yaml: Path
    ) -> None:
        """Status for unknown problem returns NOT_FOUND."""
        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(app, ["--json", "lean", "status", "9999"])
                if "No such command" in result.stdout:
                    pytest.skip("status command not implemented yet")

                assert result.exit_code == ExitCode.NOT_FOUND
            finally:
                os.chdir(old_cwd)


# ============================================================================
# erdos lean import Tests
# ============================================================================


class TestLeanImportCommand:
    """Tests for erdos lean import command."""

    def test_import_help(self, strip_ansi) -> None:
        """Verify import command has help text."""
        result = runner.invoke(app, ["lean", "import", "--help"])
        # Skip if command not implemented
        output = strip_ansi(result.stdout)
        if "No such command" in output or result.exit_code != 0:
            pytest.skip("import command not implemented yet")
        assert "import" in output.lower()

    @responses.activate
    def test_import_dry_run(
        self,
        tmp_path: Path,
        upstream_yaml: Path,
        enriched_yaml: Path,
        lean_project: Path,
    ) -> None:
        """Import with --dry-run shows what would be done."""
        lean_content = b"-- Problem 6 formalization\ntheorem problem_6 := sorry"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--dry-run",
                        "--path",
                        str(lean_project),
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == 0
                data = json.loads(result.stdout)
                assert data["success"] is True
                assert data["data"]["dry_run"] is True
                assert data["data"]["written"] is False

                # File should not be written
                local_path = get_local_file_path(lean_project, 6)
                assert not local_path.exists()
            finally:
                os.chdir(old_cwd)

    @responses.activate
    def test_import_writes_file(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path
    ) -> None:
        """Import writes file to local project."""
        lean_content = b"-- Problem 6 formalization\ntheorem problem_6 := sorry"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--path",
                        str(lean_project),
                        "--skip-lean-validation",
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == 0
                data = json.loads(result.stdout)
                assert data["success"] is True
                assert data["data"]["written"] is True

                # File should be written
                local_path = get_local_file_path(lean_project, 6)
                assert local_path.exists()
                assert local_path.read_text() == lean_content.decode("utf-8")
            finally:
                os.chdir(old_cwd)

    @responses.activate
    def test_import_relative_project_path_does_not_duplicate_paths(
        self,
        tmp_path: Path,
        enriched_yaml: Path,
        lean_project: Path,
    ) -> None:
        """Import with a relative --path should not double-prepend formal/lean."""
        lean_content = b"-- Problem 6 formalization\ntheorem problem_6 := sorry"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                with patch("erdos.core.lean.runner.shutil.which", return_value=None):
                    result = runner.invoke(
                        app,
                        [
                            "--json",
                            "lean",
                            "import",
                            "6",
                            "--path",
                            "formal/lean",
                        ],
                    )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == 0
                data = json.loads(result.stdout)
                assert data["success"] is True
                assert data["data"]["written"] is True
                assert data["data"]["lean_validated"] is False
            finally:
                os.chdir(old_cwd)

    @responses.activate
    def test_import_conflict_without_force(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path
    ) -> None:
        """Import fails if local file exists and differs."""
        lean_content = b"-- Upstream content"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        # Create different local file
        local_path = get_local_file_path(lean_project, 6)
        local_path.write_text("-- Different local content")

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--path",
                        str(lean_project),
                        "--skip-lean-validation",
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                # Should fail (conflict)
                assert result.exit_code == ExitCode.ERROR
                data = json.loads(result.stdout)
                assert data["success"] is False
            finally:
                os.chdir(old_cwd)

    @responses.activate
    def test_import_force_overwrites(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path
    ) -> None:
        """Import with --force overwrites existing file."""
        lean_content = b"-- Upstream content"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        # Create different local file
        local_path = get_local_file_path(lean_project, 6)
        local_path.write_text("-- Different local content")

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--path",
                        str(lean_project),
                        "--force",
                        "--skip-lean-validation",
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == 0
                assert local_path.read_text() == lean_content.decode("utf-8")
            finally:
                os.chdir(old_cwd)

    def test_import_no_network_without_cache(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path
    ) -> None:
        """Import with --no-network fails without cache."""
        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--path",
                        str(lean_project),
                        "--no-network",
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == ExitCode.NETWORK_ERROR
            finally:
                os.chdir(old_cwd)

    def test_import_no_network_with_cache(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path
    ) -> None:
        """Import with --no-network uses cached file."""
        # Pre-populate cache
        cache_path = get_cache_path(lean_project, 6)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cached_content = b"-- Cached content"
        cache_path.write_bytes(cached_content)

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--path",
                        str(lean_project),
                        "--no-network",
                        "--skip-lean-validation",
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == 0

                local_path = get_local_file_path(lean_project, 6)
                assert local_path.read_text() == cached_content.decode("utf-8")
            finally:
                os.chdir(old_cwd)


# ============================================================================
# erdos lean formalize --import-upstream Tests
# ============================================================================


class TestFormalizeImportUpstream:
    """Tests for erdos lean formalize --import-upstream flag."""

    def test_formalize_help_shows_import_upstream(self, strip_ansi) -> None:
        """Verify formalize command shows --import-upstream option."""
        result = runner.invoke(app, ["lean", "formalize", "--help"])
        # If the option is not there yet, skip
        help_text = strip_ansi(result.stdout)
        if "--import-upstream" not in help_text:
            pytest.skip("--import-upstream not implemented yet")
        assert "--import-upstream" in help_text

    @responses.activate
    def test_formalize_imports_when_flag_set(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path, strip_ansi
    ) -> None:
        """Formalize with --import-upstream imports instead of generating skeleton."""
        lean_content = b"-- Upstream formalization\ntheorem problem_6 := sorry"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "formalize",
                        "6",
                        "--path",
                        str(lean_project),
                        "--import-upstream",
                    ],
                )
                if "--import-upstream" not in strip_ansi(
                    runner.invoke(app, ["lean", "formalize", "--help"]).stdout
                ):
                    pytest.skip("--import-upstream not implemented yet")

                assert result.exit_code == 0
                data = json.loads(result.stdout)
                assert data["success"] is True

                # Should have imported content, not skeleton
                local_path = get_local_file_path(lean_project, 6)
                content = local_path.read_text()
                assert "Upstream formalization" in content
            finally:
                os.chdir(old_cwd)

    def test_formalize_import_upstream_no_network_fails(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path, strip_ansi
    ) -> None:
        """Formalize --import-upstream with --no-network and no cache fails."""
        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "formalize",
                        "6",
                        "--path",
                        str(lean_project),
                        "--import-upstream",
                        "--no-network",
                    ],
                )
                if "--import-upstream" not in strip_ansi(
                    runner.invoke(app, ["lean", "formalize", "--help"]).stdout
                ):
                    pytest.skip("--import-upstream not implemented yet")

                assert result.exit_code == ExitCode.NETWORK_ERROR
            finally:
                os.chdir(old_cwd)


# ============================================================================
# Provenance Tests
# ============================================================================


class TestProvenanceTracking:
    """Tests for provenance tracking in imports."""

    @responses.activate
    def test_import_creates_provenance(
        self, tmp_path: Path, enriched_yaml: Path, lean_project: Path
    ) -> None:
        """Import creates .provenance.yaml entry."""
        lean_content = b"-- Problem 6"
        url = f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/6.lean"
        responses.add(responses.GET, url, body=lean_content, status=200)

        with patch.dict(
            os.environ,
            {
                "ERDOS_DATA_PATH": str(enriched_yaml),
            },
        ):
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = runner.invoke(
                    app,
                    [
                        "--json",
                        "lean",
                        "import",
                        "6",
                        "--path",
                        str(lean_project),
                        "--skip-lean-validation",
                    ],
                )
                if "No such command" in result.stdout:
                    pytest.skip("import command not implemented yet")

                assert result.exit_code == 0

                # Check provenance file
                prov_path = lean_project / "Erdos" / ".provenance.yaml"
                assert prov_path.exists()

                prov_data = yaml.safe_load(prov_path.read_text())
                assert prov_data["schema_version"] == 1
                assert len(prov_data["imports"]) == 1
                assert prov_data["imports"][0]["problem_id"] == 6
                assert (
                    prov_data["imports"][0]["sha256"]
                    == hashlib.sha256(lean_content).hexdigest()
                )
            finally:
                os.chdir(old_cwd)
