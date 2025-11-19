"""Embedding provider utilities for UltimateSkillOS.

Provides a light abstraction over different embedding backends so memory
components can request vectors without caring about the underlying vendor.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Protocol, Optional, Sequence

try:  # Python 3.11+
    from typing import runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import runtime_checkable  # type: ignore

from config import MemoryConfig

logger = logging.getLogger(__name__)


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol describing a minimal embedding provider."""

    name: str
    dimension: int

    def embed(self, text: str) -> Sequence[float]:  # pragma: no cover - Protocol
        ...


@dataclass
class DummyEmbeddingProvider:
    """Fallback provider that returns zero vectors."""

    dimension: int = 384
    name: str = "dummy"

    def embed(self, text: str) -> Sequence[float]:
        return [0.0] * self.dimension


class SentenceTransformerEmbeddingProvider:
    """Local embedding provider backed by sentence-transformers."""

    name = "sentence-transformer"

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "sentence-transformers is not installed. Install it or switch to the OpenAI provider."
            ) from exc

        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, text: str) -> Sequence[float]:
        return self._model.encode(text, show_progress_bar=False).tolist()


class OpenAIEmbeddingProvider:
    """Embedding provider that calls OpenAI's embeddings endpoint."""

    name = "openai"

    def __init__(self, model: str, api_key: Optional[str] = None):
        from openai import OpenAI  # lazy import to keep startup light

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI embedding provider")

        self._client = OpenAI(api_key=api_key)
        self._model = model
        # text-embedding-3-small has 1536 dims; OpenAI exposes the dimension in metadata.
        self.dimension = 1536 if "3-small" in model else 3072 if "large" in model else 1536

    def embed(self, text: str) -> Sequence[float]:
        response = self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding


class EmbeddingProviderFactory:
    """Factory for constructing providers based on configuration/env."""

    @staticmethod
    def create(config: Optional[MemoryConfig] = None) -> EmbeddingProvider:
        provider_name = (config.provider if config else "auto").lower()

        if provider_name == "auto":
            return EmbeddingProviderFactory._auto(config)
        if provider_name in ("sentence_transformer", "sentence-transformer"):
            return EmbeddingProviderFactory._sentence_transformer(config)
        if provider_name == "openai":
            return EmbeddingProviderFactory._openai(config)
        if provider_name == "dummy":
            return DummyEmbeddingProvider(dimension=config.embedding_dim if config else 384)

        logger.warning("Unknown embedding provider '%s', falling back to auto", provider_name)
        return EmbeddingProviderFactory._auto(config)

    @staticmethod
    def _auto(config: Optional[MemoryConfig]) -> EmbeddingProvider:
        # Prefer local models if dependency is installed.
        try:
            return EmbeddingProviderFactory._sentence_transformer(config)
        except Exception:
            pass

        try:
            return EmbeddingProviderFactory._openai(config)
        except Exception as exc:
            logger.warning("OpenAI embedding provider unavailable: %s", exc)

        return DummyEmbeddingProvider(dimension=config.embedding_dim if config else 384)

    @staticmethod
    def _sentence_transformer(config: Optional[MemoryConfig]) -> EmbeddingProvider:
        model_name = config.model_name if config else "sentence-transformers/all-MiniLM-L6-v2"
        provider = SentenceTransformerEmbeddingProvider(model_name)
        if config and config.embedding_dim != provider.dimension:
            logger.info(
                "Updating memory embedding dimension from %s to %s based on SentenceTransformer %s",
                config.embedding_dim,
                provider.dimension,
                model_name,
            )
            config.embedding_dim = provider.dimension
        return provider

    @staticmethod
    def _openai(config: Optional[MemoryConfig]) -> EmbeddingProvider:
        api_key = os.getenv("OPENAI_API_KEY")
        model = (
            config.openai_embedding_model
            if config and getattr(config, "openai_embedding_model", None)
            else os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        )
        provider = OpenAIEmbeddingProvider(model=model, api_key=api_key)
        if config:
            config.embedding_dim = provider.dimension
        return provider