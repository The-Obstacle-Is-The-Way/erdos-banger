"""Unit tests for embedding model and serialization.

Tests are designed to work without numpy/sentence-transformers installed by:
1. Mocking the embedding model for EmbeddingModel tests
2. Skipping tests that need numpy when the module isn't available
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from erdos.core.search.embeddings import (
    EMBEDDING_AVAILABLE,
    EmbeddingConfig,
    EmbeddingModel,
    EmbeddingNotAvailableError,
    get_embedding_model,
)


if TYPE_CHECKING:
    import numpy as np

# Check if numpy is available for tests that need it
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fake_embedding_model() -> MagicMock:
    """Create a mock embedding model that returns deterministic embeddings."""
    import numpy as np

    def encode(texts: list[str]) -> np.ndarray:
        # Create deterministic embedding based on simple char counting
        results = []
        for text in texts:
            t = text.lower()
            results.append(
                [float(t.count("a")), float(t.count("e")), float(t.count("i"))]
            )
        return np.array(results, dtype=np.float32)

    mock = MagicMock()
    mock.encode = encode
    mock.get_sentence_embedding_dimension.return_value = 3
    return mock


# =============================================================================
# EmbeddingConfig Tests
# =============================================================================


class TestEmbeddingConfig:
    """Tests for EmbeddingConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = EmbeddingConfig()
        assert config.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.dimension == 384

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = EmbeddingConfig(model_name="test-model", dimension=768)
        assert config.model_name == "test-model"
        assert config.dimension == 768

    def test_immutability(self) -> None:
        """Test that EmbeddingConfig is frozen."""
        config = EmbeddingConfig()
        with pytest.raises(AttributeError):
            config.model_name = "other"  # type: ignore[misc]


# =============================================================================
# Embedding Availability Tests
# =============================================================================


class TestEmbeddingAvailability:
    """Tests for embedding availability checks."""

    def test_embedding_available_is_bool(self) -> None:
        """Test that EMBEDDING_AVAILABLE is a boolean."""
        assert isinstance(EMBEDDING_AVAILABLE, bool)


# =============================================================================
# EmbeddingModel Tests
# =============================================================================


class TestEmbeddingModel:
    """Tests for EmbeddingModel class."""

    def test_init_when_unavailable(self) -> None:
        """Test that EmbeddingModel raises when sentence-transformers unavailable."""
        with patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", False):
            with pytest.raises(EmbeddingNotAvailableError) as exc_info:
                EmbeddingModel()
            assert "embeddings" in str(exc_info.value)

    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_init_loads_model(self, mock_st_class: MagicMock) -> None:
        """Test that init loads the sentence transformer model."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.return_value = mock_model

        em = EmbeddingModel()

        mock_st_class.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")
        assert em.dimension == 384
        assert em.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_init_custom_model(self, mock_st_class: MagicMock) -> None:
        """Test initialization with custom model name."""
        mock_model = MagicMock()
        # Model returns 768 but config expects 768
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_st_class.return_value = mock_model

        config = EmbeddingConfig(model_name="allenai/specter2", dimension=768)
        em = EmbeddingModel(config)

        mock_st_class.assert_called_once_with("allenai/specter2")
        assert em.dimension == 768

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_encode_single_text(
        self, mock_st_class: MagicMock, fake_embedding_model: MagicMock
    ) -> None:
        """Test encoding a single text."""
        mock_st_class.return_value = fake_embedding_model

        em = EmbeddingModel(EmbeddingConfig(dimension=3))
        result = em.encode("banana")

        # "banana" has 3 a's, 0 e's, 0 i's
        assert result.shape == (3,)
        assert result[0] == 3.0  # count of 'a'
        assert result[1] == 0.0  # count of 'e'
        assert result[2] == 0.0  # count of 'i'

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_encode_batch(
        self, mock_st_class: MagicMock, fake_embedding_model: MagicMock
    ) -> None:
        """Test encoding multiple texts at once."""
        mock_st_class.return_value = fake_embedding_model

        em = EmbeddingModel(EmbeddingConfig(dimension=3))
        results = em.encode_batch(["apple", "pie"])

        assert len(results) == 2
        # "apple" = 1 a, 1 e, 0 i
        assert results[0][0] == 1.0
        assert results[0][1] == 1.0
        assert results[0][2] == 0.0
        # "pie" = 0 a, 1 e, 1 i
        assert results[1][0] == 0.0
        assert results[1][1] == 1.0
        assert results[1][2] == 1.0

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_to_blob_and_from_blob_roundtrip(
        self, mock_st_class: MagicMock, fake_embedding_model: MagicMock
    ) -> None:
        """Test serialization roundtrip."""
        mock_st_class.return_value = fake_embedding_model

        em = EmbeddingModel(EmbeddingConfig(dimension=3))
        original = em.encode("test data")

        blob = em.to_blob(original)
        assert isinstance(blob, bytes)

        restored = em.from_blob(blob)
        assert restored.shape == original.shape
        # Use numpy comparison
        assert (original == restored).all()


# =============================================================================
# Cosine Similarity Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestCosineSimilarity:
    """Tests for cosine similarity computation."""

    def test_identical_vectors(self) -> None:
        """Test that identical vectors have similarity 1.0."""
        from erdos.core.search.embeddings import cosine_similarity

        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        """Test that orthogonal vectors have similarity 0.0."""
        from erdos.core.search.embeddings import cosine_similarity

        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(v1, v2) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        """Test that opposite vectors have similarity -1.0."""
        from erdos.core.search.embeddings import cosine_similarity

        v1 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        v2 = np.array([-1.0, -2.0, -3.0], dtype=np.float32)
        assert cosine_similarity(v1, v2) == pytest.approx(-1.0)

    def test_normalized_cosine(self) -> None:
        """Test semantic_score normalization (0..1 range)."""
        from erdos.core.search.embeddings import cosine_similarity

        v1 = np.array([1.0, 0.0], dtype=np.float32)
        v2 = np.array([-1.0, 0.0], dtype=np.float32)

        raw = cosine_similarity(v1, v2)  # -1.0
        semantic_score = (raw + 1) / 2
        assert semantic_score == pytest.approx(0.0)

        # Same direction: raw = 1.0, semantic = 1.0
        raw2 = cosine_similarity(v1, v1)
        semantic_score2 = (raw2 + 1) / 2
        assert semantic_score2 == pytest.approx(1.0)

    def test_zero_vector_handling(self) -> None:
        """Test that zero vector returns 0 similarity (no NaN)."""
        from erdos.core.search.embeddings import cosine_similarity

        v1 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        v2 = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        result = cosine_similarity(v1, v2)
        # Should return 0 (not NaN or raise error)
        assert result == pytest.approx(0.0)


# =============================================================================
# Blob Serialization Tests
# =============================================================================


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestBlobSerialization:
    """Tests for embedding_to_blob and embedding_from_blob functions."""

    def test_to_blob_returns_bytes(self) -> None:
        """Test that to_blob returns bytes."""
        from erdos.core.search.embeddings import embedding_to_blob

        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        blob = embedding_to_blob(v)
        assert isinstance(blob, bytes)

    def test_roundtrip_preserves_values(self) -> None:
        """Test that serialization roundtrip preserves values."""
        from erdos.core.search.embeddings import embedding_from_blob, embedding_to_blob

        original = np.array([1.5, -2.5, 3.14159], dtype=np.float32)
        blob = embedding_to_blob(original)
        restored = embedding_from_blob(blob)

        assert restored.dtype == np.float32
        assert restored.shape == original.shape
        assert (original == restored).all()

    def test_roundtrip_high_dimension(self) -> None:
        """Test roundtrip with realistic 384-dimension vector."""
        from erdos.core.search.embeddings import embedding_from_blob, embedding_to_blob

        original = np.random.rand(384).astype(np.float32)
        blob = embedding_to_blob(original)
        restored = embedding_from_blob(blob)

        assert restored.shape == (384,)
        assert np.allclose(original, restored)


# =============================================================================
# get_embedding_model Singleton Tests
# =============================================================================


class TestGetEmbeddingModel:
    """Tests for the singleton/cache function."""

    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", False)
    def test_returns_none_when_unavailable(self) -> None:
        """Test that get_embedding_model returns None when deps missing."""
        # Clear cache first
        get_embedding_model.cache_clear()
        result = get_embedding_model()
        assert result is None

    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_caches_model(self, mock_st_class: MagicMock) -> None:
        """Test that get_embedding_model caches the model instance."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.return_value = mock_model

        get_embedding_model.cache_clear()
        m1 = get_embedding_model()
        m2 = get_embedding_model()

        assert m1 is m2
        mock_st_class.assert_called_once()  # Only loaded once


# =============================================================================
# Dimension Validation Tests
# =============================================================================


class TestDimensionValidation:
    """Tests for embedding dimension validation."""

    @patch("erdos.core.search.embeddings.EMBEDDING_AVAILABLE", True)
    @patch("erdos.core.search.embeddings.SentenceTransformer")
    def test_dimension_mismatch_warning(self, mock_st_class: MagicMock) -> None:
        """Test that dimension mismatch raises ValueError."""
        mock_model = MagicMock()
        # Model returns 768 but config expects 384
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_st_class.return_value = mock_model

        config = EmbeddingConfig(dimension=384)  # Expect 384
        with pytest.raises(ValueError, match="dimension mismatch"):
            EmbeddingModel(config)
