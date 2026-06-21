from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wiki_ai_rag_api.api.dependencies import reset_rate_limiter
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.main import create_app
from wiki_ai_rag_api.services.conversation import reset_conversation_memory
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.metrics import metrics_registry
from wiki_ai_rag_api.services.vector_store import get_vector_store


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    reset_rate_limiter()
    reset_conversation_memory()
    metrics_registry.reset()

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    reset_rate_limiter()
    reset_conversation_memory()
    metrics_registry.reset()
