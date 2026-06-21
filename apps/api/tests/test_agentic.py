from pathlib import Path

from fastapi.testclient import TestClient


def test_agentic_ask_is_disabled_by_default(client: TestClient) -> None:
    response = client.post("/api/v1/agentic/ask", json={"question": "What is Product X?"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Agentic RAG is disabled"


def test_agentic_ask_uses_search_tool_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIC_RAG_ENABLED", "true")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    from wiki_ai_rag_api.api.dependencies import reset_rate_limiter
    from wiki_ai_rag_api.core.config import get_settings
    from wiki_ai_rag_api.main import create_app
    from wiki_ai_rag_api.services.embeddings import get_embedding_provider
    from wiki_ai_rag_api.services.vector_store import get_vector_store

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    reset_rate_limiter()

    with TestClient(create_app()) as local_client:
        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "product.md").write_text("Product X supports agentic retrieval.", encoding="utf-8")
        source_response = local_client.post(
            "/api/v1/sources",
            json={
                "name": "Agent Wiki",
                "type": "filesystem",
                "config": {"path": str(wiki_dir)},
                "enabled": True,
                "schedule": {"mode": "manual"},
            },
        )
        source_id = source_response.json()["id"]
        local_client.post("/api/v1/indexing/jobs", json={"source_id": source_id, "mode": "full"})

        response = local_client.post(
            "/api/v1/agentic/ask",
            json={"question": "What does Product X support?", "source_ids": [source_id]},
        )

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    reset_rate_limiter()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["tool_calls"][0]["name"] == "search_knowledge_base"
    assert payload["citations"][0]["source_id"] == source_id
