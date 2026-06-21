from pathlib import Path

from fastapi.testclient import TestClient

from wiki_ai_rag_api.api.dependencies import reset_rate_limiter
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.main import create_app
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.vector_store import get_vector_store


def test_question_rate_limit_is_disabled_by_default(client: TestClient) -> None:
    first = client.post("/api/v1/ask", json={"question": "Есть ли данные?"})
    second = client.post("/api/v1/ask", json={"question": "Есть ли данные?"})

    assert first.status_code == 200
    assert second.status_code == 200


def test_question_rate_limit_can_be_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("QUESTION_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    reset_rate_limiter()

    client = TestClient(create_app())

    first = client.post("/api/v1/ask", json={"question": "Есть ли данные?"})
    second = client.post("/api/v1/ask", json={"question": "Есть ли данные?"})

    assert first.status_code == 200
    assert second.status_code == 429

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    reset_rate_limiter()

