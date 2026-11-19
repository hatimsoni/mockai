"""Shared test setup: no network, no model downloads.

- Storage is disabled (no MinIO needed).
- Chroma writes to a temp folder.
- Embeddings are a deterministic fake (hash-based vectors) instead of MiniLM.
- The LLM is replaced per-test with a scripted fake via `fake_llm`.
"""
import os

import pytest

os.environ["STORAGE_ENABLED"] = "false"
os.environ["INTERNAL_API_KEY"] = ""


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    from langchain_core.embeddings import DeterministicFakeEmbedding

    from app import llm
    from app.config import get_settings
    from app.rag import store

    get_settings.cache_clear()
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    get_settings.cache_clear()
    store.set_embeddings_override(DeterministicFakeEmbedding(size=64))
    yield
    store.set_embeddings_override(None)
    llm.set_llm_override(None)
    get_settings.cache_clear()


@pytest.fixture
def fake_llm():
    """Usage: fake_llm(['reply 1', 'reply 2']) -> replies returned in order."""
    from langchain_core.language_models import FakeListChatModel

    from app import llm

    def _make(responses: list[str]):
        model = FakeListChatModel(responses=responses)
        llm.set_llm_override(model)
        return model

    return _make
