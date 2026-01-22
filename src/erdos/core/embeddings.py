"""Backward-compatible shim for embeddings.

This module has been moved to erdos.core.search.embeddings.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.search.embeddings import (
    DEFAULT_DIMENSION,
    DEFAULT_MODEL_NAME,
    EMBEDDING_AVAILABLE,
    EmbeddingConfig,
    EmbeddingModel,
    EmbeddingNotAvailableError,
    cosine_similarity,
    embedding_from_blob,
    embedding_to_blob,
    get_embedding_model,
)


__all__ = [
    "DEFAULT_DIMENSION",
    "DEFAULT_MODEL_NAME",
    "EMBEDDING_AVAILABLE",
    "EmbeddingConfig",
    "EmbeddingModel",
    "EmbeddingNotAvailableError",
    "cosine_similarity",
    "embedding_from_blob",
    "embedding_to_blob",
    "get_embedding_model",
]
