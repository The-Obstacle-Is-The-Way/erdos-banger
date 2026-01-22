"""Integration tests for semantic/hybrid search CLI commands.

These tests validate CLI behavior without requiring actual embedding models.
They mock the embedding model to avoid slow downloads and focus on testing
the CLI flags, validation, and output formatting.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from erdos.cli import app


# Check if numpy is available
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


if TYPE_CHECKING:
    import numpy as np


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with sample problems."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    problems_yaml = """
- id: 1
  title: Twin Primes Problem
  statement: "Find all primes p where p+2 is also prime."
  status: open
  tags:
    - number_theory
    - primes

- id: 2
  title: Arithmetic Progressions
  statement: "Study arithmetic progressions of prime numbers and their density."
  status: open
  tags:
    - number_theory
"""
    (data_dir / "problems_enriched.yaml").write_text(problems_yaml)
    return data_dir


@pytest.fixture
def temp_index_path(tmp_path: Path) -> Path:
    """Create a temporary index path."""
    return tmp_path / "index" / "erdos.sqlite"


@pytest.fixture
def fake_embedder() -> MagicMock:
    """Create a mock embedding model."""
    mock = MagicMock()

    def encode(text: str) -> np.ndarray:
        import numpy as np

        t = text.lower()
        return np.array(
            [float(t.count("a")), float(t.count("e")), float(t.count("i"))],
            dtype=np.float32,
        )

    def encode_batch(texts: list[str]) -> list[np.ndarray]:
        return [encode(t) for t in texts]

    mock.encode = encode
    mock.encode_batch = encode_batch
    mock.dimension = 3
    mock.model_name = "test-model"

    def to_blob(arr: np.ndarray) -> bytes:
        import io

        import numpy as np

        buf = io.BytesIO()
        np.save(buf, arr)
        return buf.getvalue()

    def from_blob(blob: bytes) -> np.ndarray:
        import io

        import numpy as np

        buf = io.BytesIO(blob)
        return np.load(buf)  # type: ignore[no-any-return]

    mock.to_blob = to_blob
    mock.from_blob = from_blob

    return mock


# =============================================================================
# CLI Help Tests
# =============================================================================


class TestSearchCLIHelp:
    """Tests for search command help."""

    def test_search_help_shows_semantic_flag(self, strip_ansi) -> None:
        """Test that --semantic flag is documented in help."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--semantic" in output or "-s" in output

    def test_search_help_shows_hybrid_flag(self, strip_ansi) -> None:
        """Test that --hybrid flag is documented in help."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--hybrid" in strip_ansi(result.output)

    def test_search_help_shows_alpha_flag(self, strip_ansi) -> None:
        """Test that --alpha flag is documented in help."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--alpha" in strip_ansi(result.output)

    def test_search_help_shows_build_embeddings_flag(self, strip_ansi) -> None:
        """Test that --build-embeddings flag is documented in help."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--build-embeddings" in strip_ansi(result.output)


# =============================================================================
# Mode Selection Validation Tests
# =============================================================================


class TestModeValidation:
    """Tests for mutually exclusive mode flags."""

    def test_semantic_and_hybrid_mutually_exclusive(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test that --semantic and --hybrid cannot be used together."""
        result = runner.invoke(
            app,
            ["search", "prime", "--semantic", "--hybrid"],
            env={
                "ERDOS_DATA_PATH": str(temp_data_dir),
                "ERDOS_INDEX_PATH": str(temp_index_path),
            },
        )
        # Should fail with usage error
        assert result.exit_code != 0 or "mutually exclusive" in result.output.lower()

    def test_semantic_and_bm25_only_mutually_exclusive(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test that --semantic and --bm25-only cannot be used together."""
        result = runner.invoke(
            app,
            ["search", "prime", "--semantic", "--bm25-only"],
            env={
                "ERDOS_DATA_PATH": str(temp_data_dir),
                "ERDOS_INDEX_PATH": str(temp_index_path),
            },
        )
        assert result.exit_code != 0 or "mutually exclusive" in result.output.lower()

    def test_alpha_requires_hybrid(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test that --alpha requires --hybrid mode."""
        result = runner.invoke(
            app,
            ["search", "prime", "--alpha", "0.7", "--build-index"],
            env={
                "ERDOS_DATA_PATH": str(temp_data_dir),
                "ERDOS_INDEX_PATH": str(temp_index_path),
            },
        )
        # Should fail or warn about --alpha without --hybrid
        assert result.exit_code != 0 or "alpha" in result.output.lower()


# =============================================================================
# BM25-Only Mode Tests (should work without embeddings)
# =============================================================================


class TestBm25OnlyMode:
    """Tests for BM25-only search mode."""

    def test_bm25_only_works_without_embeddings(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test that --bm25-only works without embeddings built."""
        result = runner.invoke(
            app,
            ["search", "prime", "--bm25-only", "--build-index"],
            env={
                "ERDOS_DATA_PATH": str(temp_data_dir),
                "ERDOS_INDEX_PATH": str(temp_index_path),
            },
        )
        # Should succeed
        assert result.exit_code == 0

    def test_default_mode_is_bm25(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test that default search mode is BM25 (no embeddings required)."""
        result = runner.invoke(
            app,
            ["search", "prime", "--build-index"],
            env={
                "ERDOS_DATA_PATH": str(temp_data_dir),
                "ERDOS_INDEX_PATH": str(temp_index_path),
            },
        )
        # Should succeed with BM25
        assert result.exit_code == 0


# =============================================================================
# Embedding Dependency Tests
# =============================================================================


class TestEmbeddingDependency:
    """Tests for embedding dependency handling."""

    def test_semantic_without_embeddings_extra_shows_error(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test error message when embeddings deps not installed."""
        with patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", False):
            result = runner.invoke(
                app,
                ["search", "prime", "--semantic", "--build-index"],
                env={
                    "ERDOS_DATA_PATH": str(temp_data_dir),
                    "ERDOS_INDEX_PATH": str(temp_index_path),
                },
            )
            assert result.exit_code == 10
            assert "embeddings" in result.output.lower()
            normalized = " ".join(result.output.lower().split())
            assert "uv sync --extra embeddings" in normalized

    def test_build_embeddings_without_deps_shows_error(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test error when trying to build embeddings without deps."""
        with patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", False):
            result = runner.invoke(
                app,
                ["search", "prime", "--build-embeddings", "--build-index"],
                env={
                    "ERDOS_DATA_PATH": str(temp_data_dir),
                    "ERDOS_INDEX_PATH": str(temp_index_path),
                },
            )
            assert result.exit_code == 10
            assert "embeddings" in result.output.lower()
            normalized = " ".join(result.output.lower().split())
            assert "uv sync --extra embeddings" in normalized


# =============================================================================
# JSON Output Tests
# =============================================================================


class TestJsonOutput:
    """Tests for JSON output in different search modes."""

    def test_bm25_json_output_structure(
        self, temp_data_dir: Path, temp_index_path: Path
    ) -> None:
        """Test JSON output structure for BM25 search."""
        import json

        result = runner.invoke(
            app,
            ["--json", "search", "prime", "--build-index"],
            env={
                "ERDOS_DATA_PATH": str(temp_data_dir),
                "ERDOS_INDEX_PATH": str(temp_index_path),
            },
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        # The output may contain progress text before JSON
        # Find the JSON object (from first '{' to last '}')
        output_str = result.output
        json_start = output_str.find("{")
        json_end = output_str.rfind("}") + 1

        assert json_start >= 0, f"No JSON found in output: {output_str}"
        json_str = output_str[json_start:json_end]

        output = json.loads(json_str)
        assert output["success"] is True
        assert "data" in output
        assert "query" in output["data"]
        assert "results" in output["data"]

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
    def test_semantic_json_includes_semantic_score(
        self, temp_data_dir: Path, temp_index_path: Path, fake_embedder: MagicMock
    ) -> None:
        """Test that semantic search JSON includes semantic_score field."""
        import json

        with patch(
            "erdos.core.search.service.get_embedding_model",
            return_value=(fake_embedder, None),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "search",
                    "prime",
                    "--semantic",
                    "--build-index",
                    "--build-embeddings",
                ],
                env={
                    "ERDOS_DATA_PATH": str(temp_data_dir),
                    "ERDOS_INDEX_PATH": str(temp_index_path),
                },
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["data"]["mode"] == "semantic"
        assert output["data"]["results"]
        assert "semantic_score" in output["data"]["results"][0]

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
    def test_hybrid_json_includes_all_scores(
        self, temp_data_dir: Path, temp_index_path: Path, fake_embedder: MagicMock
    ) -> None:
        """Test that hybrid search JSON includes all score fields."""
        import json

        with patch(
            "erdos.core.search.service.get_embedding_model",
            return_value=(fake_embedder, None),
        ):
            result = runner.invoke(
                app,
                [
                    "--json",
                    "search",
                    "prime",
                    "--hybrid",
                    "--alpha",
                    "0.6",
                    "--build-index",
                    "--build-embeddings",
                ],
                env={
                    "ERDOS_DATA_PATH": str(temp_data_dir),
                    "ERDOS_INDEX_PATH": str(temp_index_path),
                },
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["data"]["mode"] == "hybrid"
        assert output["data"]["results"]
        first = output["data"]["results"][0]
        assert "score" in first
        assert "semantic_score" in first
        assert "hybrid_score" in first
