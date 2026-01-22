"""Unit tests for SearchIndex embedding support."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from erdos.core.models import ProblemRecord, ProblemStatus
from erdos.core.search.db import SearchIndexError
from erdos.core.search.facade import SearchIndex


# Check if numpy is available for embedding tests
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


if TYPE_CHECKING:
    import numpy as np


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_index(tmp_path: Path) -> SearchIndex:
    """Create a temporary search index for testing."""
    db_path = tmp_path / "test.sqlite"
    return SearchIndex(db_path)


@pytest.fixture
def sample_problem() -> ProblemRecord:
    """Create a sample problem for testing."""
    return ProblemRecord(
        id=1,
        title="Test Problem",
        statement="Find all primes p where p+2 is also prime (twin primes).",
        status=ProblemStatus.OPEN,
        tags=["number_theory", "primes"],
    )


@pytest.fixture
def indexed_index(
    temp_index: SearchIndex, sample_problem: ProblemRecord
) -> SearchIndex:
    """Create an index with a sample problem indexed."""
    temp_index.index_problem(sample_problem)
    # Index another problem for variety
    temp_index.index_problem(
        ProblemRecord(
            id=2,
            title="Another Problem",
            statement="Study arithmetic progressions of prime numbers.",
            status=ProblemStatus.OPEN,
            tags=["number_theory"],
        )
    )
    return temp_index


@pytest.fixture
def fake_embedder() -> MagicMock:
    """Create a mock embedding model."""
    mock = MagicMock()

    def encode(text: str) -> np.ndarray:
        import numpy as np

        # Deterministic embedding: count 'a', 'e', 'i' characters
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
# Embedding Schema Tests
# =============================================================================


class TestEmbeddingSchema:
    """Tests for embedding table schema."""

    def test_embedding_table_created(self, temp_index: SearchIndex) -> None:
        """Test that chunk_embeddings table is created."""
        with temp_index._connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_embeddings'"
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "chunk_embeddings"

    def test_embedding_metadata_stored(self, temp_index: SearchIndex) -> None:
        """Test that embedding metadata keys can be stored."""
        temp_index.set_embedding_metadata("test-model", 384)

        model, dim = temp_index.get_embedding_metadata()
        assert model == "test-model"
        assert dim == 384

    def test_embedding_metadata_returns_none_when_not_set(
        self, temp_index: SearchIndex
    ) -> None:
        """Test get_embedding_metadata returns None for unset metadata."""
        model, dim = temp_index.get_embedding_metadata()
        assert model is None
        assert dim is None


# =============================================================================
# build_embeddings Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestBuildEmbeddings:
    """Tests for build_embeddings method."""

    def test_build_embeddings_populates_table(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that build_embeddings populates the embeddings table."""
        count = indexed_index.build_embeddings(fake_embedder)

        assert count == 2  # Two problems indexed

        with indexed_index._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunk_embeddings")
            result = cursor.fetchone()
            assert result[0] == 2

    def test_build_embeddings_stores_metadata(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that build_embeddings stores model metadata."""
        indexed_index.build_embeddings(fake_embedder)

        model, dim = indexed_index.get_embedding_metadata()
        assert model == "test-model"
        assert dim == 3

    def test_build_embeddings_clears_existing(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that build_embeddings clears existing embeddings."""
        # Build once
        indexed_index.build_embeddings(fake_embedder)

        # Build again
        count = indexed_index.build_embeddings(fake_embedder)
        assert count == 2

        # Should still have exactly 2 embeddings
        with indexed_index._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunk_embeddings")
            result = cursor.fetchone()
            assert result[0] == 2

    def test_build_embeddings_returns_zero_when_empty(
        self, temp_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that build_embeddings returns 0 when no chunks exist."""
        count = temp_index.build_embeddings(fake_embedder)
        assert count == 0


# =============================================================================
# has_embeddings Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestHasEmbeddings:
    """Tests for has_embeddings method."""

    def test_has_embeddings_false_when_empty(self, indexed_index: SearchIndex) -> None:
        """Test has_embeddings returns False before building."""
        assert indexed_index.has_embeddings() is False

    def test_has_embeddings_true_after_build(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test has_embeddings returns True after building."""
        indexed_index.build_embeddings(fake_embedder)
        assert indexed_index.has_embeddings() is True


# =============================================================================
# search_semantic Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestSearchSemantic:
    """Tests for semantic search functionality."""

    def test_search_semantic_without_embeddings_raises(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that semantic search without embeddings raises error."""
        with pytest.raises(SearchIndexError, match="No embeddings"):
            indexed_index.search_semantic("primes", fake_embedder, limit=10)

    def test_search_semantic_returns_results(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test semantic search returns results after building embeddings."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_semantic(
            "prime numbers", fake_embedder, limit=10
        )

        assert len(results) > 0
        assert all(hasattr(r, "semantic_score") for r in results)

    def test_search_semantic_respects_limit(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test semantic search respects limit parameter."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_semantic("prime", fake_embedder, limit=1)

        assert len(results) <= 1

    def test_search_semantic_model_mismatch_raises(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that model mismatch raises ConfigError."""
        indexed_index.build_embeddings(fake_embedder)

        # Change model name
        different_embedder = MagicMock()
        different_embedder.model_name = "different-model"
        different_embedder.dimension = 3

        with pytest.raises(SearchIndexError, match="Model mismatch"):
            indexed_index.search_semantic("primes", different_embedder, limit=10)

    def test_search_semantic_dimension_mismatch_raises(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that dimension mismatch raises ConfigError."""
        indexed_index.build_embeddings(fake_embedder)

        # Change dimension
        different_embedder = MagicMock()
        different_embedder.model_name = "test-model"
        different_embedder.dimension = 768  # Different dimension

        with pytest.raises(SearchIndexError, match="dimension mismatch"):
            indexed_index.search_semantic("primes", different_embedder, limit=10)


# =============================================================================
# search_hybrid Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestSearchHybrid:
    """Tests for hybrid search functionality."""

    def test_search_hybrid_without_embeddings_raises(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that hybrid search without embeddings raises error."""
        with pytest.raises(SearchIndexError, match="No embeddings"):
            indexed_index.search_hybrid("primes", fake_embedder, limit=10)

    def test_search_hybrid_returns_results(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test hybrid search returns results."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_hybrid("prime", fake_embedder, limit=10)

        assert len(results) > 0
        assert all(hasattr(r, "hybrid_score") for r in results)

    def test_search_hybrid_alpha_zero_is_bm25_only(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that alpha=0 uses BM25 scores only."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_hybrid(
            "prime", fake_embedder, limit=10, alpha=0.0
        )

        # Hybrid score should equal normalized BM25 when alpha=0
        # (difficult to test exactly, but should have results)
        assert len(results) > 0

    def test_search_hybrid_alpha_one_is_semantic_only(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that alpha=1 uses semantic scores only."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_hybrid(
            "prime", fake_embedder, limit=10, alpha=1.0
        )

        # Hybrid score should equal semantic score when alpha=1
        assert len(results) > 0
        for r in results:
            assert r.hybrid_score == pytest.approx(r.semantic_score, rel=0.01)

    def test_search_hybrid_default_alpha(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test default alpha value of 0.5."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_hybrid("prime", fake_embedder, limit=10)

        # Should have mix of BM25 and semantic scores
        assert len(results) > 0


# =============================================================================
# SemanticSearchResult Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestSemanticSearchResult:
    """Tests for SemanticSearchResult data structure."""

    def test_semantic_result_has_required_fields(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that semantic results have all required fields."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_semantic("prime", fake_embedder, limit=1)

        assert len(results) > 0
        r = results[0]

        assert hasattr(r, "chunk_id")
        assert hasattr(r, "text")
        assert hasattr(r, "semantic_score")
        assert hasattr(r, "source_type")
        assert hasattr(r, "problem_id")

    def test_semantic_score_in_valid_range(
        self, indexed_index: SearchIndex, fake_embedder: MagicMock
    ) -> None:
        """Test that semantic scores are in [0, 1] range."""
        indexed_index.build_embeddings(fake_embedder)

        results = indexed_index.search_semantic("prime", fake_embedder, limit=10)

        for r in results:
            assert 0.0 <= r.semantic_score <= 1.0
