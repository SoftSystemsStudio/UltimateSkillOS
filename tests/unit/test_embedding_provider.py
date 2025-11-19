import sys
import types

import pytest

from core.embedding_provider import DummyEmbeddingProvider, EmbeddingProviderFactory
from config import MemoryConfig


def test_dummy_provider_respects_config_dimension():
    config = MemoryConfig(provider="dummy", embedding_dim=42)

    provider = EmbeddingProviderFactory.create(config)

    assert isinstance(provider, DummyEmbeddingProvider)
    assert provider.dimension == 42
    assert provider.embed("hello world") == [0.0] * 42


def test_auto_falls_back_to_dummy_when_providers_unavailable(monkeypatch):
    config = MemoryConfig(provider="auto", embedding_dim=16)

    def raise_sentence_transformer(_):  # pragma: no cover - forced failure
        raise RuntimeError("sentence transformers unavailable")

    def raise_openai(_):  # pragma: no cover - forced failure
        raise RuntimeError("openai unavailable")

    monkeypatch.setattr(
        EmbeddingProviderFactory,
        "_sentence_transformer",
        raise_sentence_transformer,
    )
    monkeypatch.setattr(
        EmbeddingProviderFactory,
        "_openai",
        raise_openai,
    )

    provider = EmbeddingProviderFactory.create(config)

    assert isinstance(provider, DummyEmbeddingProvider)
    assert provider.dimension == 16


class _FakeEmbeddingsClient:
    def create(self, model: str, input: str):  # pragma: no cover - simple stub
        return types.SimpleNamespace(
            data=[types.SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
        )


class _FakeOpenAI:
    def __init__(self, api_key: str):  # pragma: no cover - simple stub
        self.api_key = api_key
        self.embeddings = _FakeEmbeddingsClient()


@pytest.fixture(autouse=True)
def _reset_openai_module(monkeypatch):
    # Ensure we don't leak fake modules between tests
    if "openai" in sys.modules:
        monkeypatch.delitem(sys.modules, "openai", raising=False)
    yield


def test_openai_provider_requires_api_key(monkeypatch):
    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    config = MemoryConfig(provider="openai", openai_embedding_model="text-embedding-3-small")

    provider = EmbeddingProviderFactory.create(config)

    assert provider.name == "openai"
    assert config.embedding_dim == 1536  # auto-set based on model name
    assert provider.embed("hi") == [0.1, 0.2, 0.3]