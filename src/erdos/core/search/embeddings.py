"""Embedding model for semantic search.

This module provides embedding generation for text chunks, enabling semantic
search via vector similarity. Requires the 'embeddings' optional dependency:

    uv sync --extra embeddings

The module gracefully handles missing dependencies, allowing the rest of the
codebase to import it without requiring sentence-transformers to be installed.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any


logger = logging.getLogger(__name__)


# =============================================================================
# Conditional Imports (optional deps)
# =============================================================================

# Try importing sentence-transformers and numpy
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    # Type stubs for when deps are unavailable
    np = None  # type: ignore[assignment]
    SentenceTransformer = None


if TYPE_CHECKING:
    from numpy.typing import NDArray


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIMENSION = 384


# =============================================================================
# Exceptions
# =============================================================================


class EmbeddingNotAvailableError(Exception):
    """Raised when embedding functionality is requested but deps not installed."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                "Embedding functionality requires the 'embeddings' extra. "
                "Install with: uv sync --extra embeddings"
            )
        )


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuration for the embedding model.

    Attributes:
        model_name: Name of the sentence-transformers model
        dimension: Expected embedding dimension (validated at load time)
    """

    model_name: str = DEFAULT_MODEL_NAME
    dimension: int = DEFAULT_DIMENSION


# =============================================================================
# EmbeddingModel
# =============================================================================


class EmbeddingModel:
    """Wrapper around sentence-transformers for generating embeddings.

    Usage:
        model = EmbeddingModel()
        embedding = model.encode("prime arithmetic progression")
        similarity = cosine_similarity(embedding1, embedding2)

    The model is loaded lazily on first use and cached.
    """

    def __init__(self, config: EmbeddingConfig | None = None) -> None:
        """Initialize the embedding model.

        Args:
            config: Configuration for the model. Uses defaults if not provided.

        Raises:
            EmbeddingNotAvailableError: If sentence-transformers not installed.
            ValueError: If actual model dimension doesn't match config.
        """
        if not EMBEDDING_AVAILABLE:
            raise EmbeddingNotAvailableError()

        self._config = config or EmbeddingConfig()
        self._model_name = self._config.model_name

        # Load the model
        logger.debug("Loading embedding model: %s", self._model_name)
        self._model: SentenceTransformer = SentenceTransformer(self._model_name)

        # Validate dimension
        actual_dim = self._model.get_sentence_embedding_dimension()
        if actual_dim != self._config.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: model {self._model_name} produces "
                f"{actual_dim}-dim embeddings, but config expects {self._config.dimension}"
            )

        self._dimension = actual_dim
        logger.debug("Loaded model with dimension %d", self._dimension)

    @property
    def model_name(self) -> str:
        """Name of the loaded model."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Dimension of the embedding vectors."""
        return int(self._dimension)

    def encode(self, text: str) -> NDArray[Any]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as numpy array.
        """
        result = self._model.encode([text])
        return result[0]  # type: ignore[no-any-return]

    def encode_batch(self, texts: list[str]) -> list[NDArray[Any]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        results = self._model.encode(texts)
        return list(results)

    def to_blob(self, embedding: NDArray[Any]) -> bytes:
        """Serialize embedding to bytes for SQLite storage.

        Args:
            embedding: Numpy array to serialize.

        Returns:
            Bytes representation suitable for BLOB storage.
        """
        return embedding_to_blob(embedding)

    def from_blob(self, blob: bytes) -> NDArray[Any]:
        """Deserialize embedding from SQLite BLOB.

        Args:
            blob: Bytes from SQLite BLOB column.

        Returns:
            Numpy array.
        """
        return embedding_from_blob(blob)


# =============================================================================
# Serialization Helpers
# =============================================================================


def embedding_to_blob(embedding: NDArray[Any]) -> bytes:
    """Serialize numpy array to bytes.

    Args:
        embedding: Numpy array to serialize.

    Returns:
        Bytes for SQLite BLOB storage.
    """
    import numpy as _np  # noqa: PLC0415

    buffer = io.BytesIO()
    _np.save(buffer, embedding)
    return buffer.getvalue()


def embedding_from_blob(blob: bytes) -> NDArray[Any]:
    """Deserialize numpy array from bytes.

    Args:
        blob: Bytes from SQLite BLOB.

    Returns:
        Numpy array.
    """
    import numpy as _np  # noqa: PLC0415

    buffer = io.BytesIO(blob)
    return _np.load(buffer)  # type: ignore[no-any-return]


# =============================================================================
# Similarity Functions
# =============================================================================


def cosine_similarity(v1: NDArray[Any], v2: NDArray[Any]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        v1: First vector.
        v2: Second vector.

    Returns:
        Cosine similarity in range [-1, 1].
        Returns 0.0 if either vector is zero.
    """
    import numpy as _np  # noqa: PLC0415

    norm1 = _np.linalg.norm(v1)
    norm2 = _np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    dot = _np.dot(v1, v2)
    return float(dot / (norm1 * norm2))


# =============================================================================
# Singleton / Cached Model
# =============================================================================


@lru_cache(maxsize=1)
def get_embedding_model(
    model_name: str = DEFAULT_MODEL_NAME,
) -> EmbeddingModel | None:
    """Get a cached embedding model instance.

    Returns None if sentence-transformers is not available.

    Args:
        model_name: Name of the model to load.

    Returns:
        EmbeddingModel instance or None if unavailable.
    """
    if not EMBEDDING_AVAILABLE:
        return None

    # Determine dimension based on model name
    if "MiniLM" in model_name:
        dim = 384
    elif "specter" in model_name.lower():
        dim = 768
    else:
        dim = 384  # default

    config = EmbeddingConfig(model_name=model_name, dimension=dim)
    return EmbeddingModel(config)
