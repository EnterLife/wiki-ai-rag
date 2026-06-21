from pathlib import Path

from fastapi.testclient import TestClient

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.main import create_app
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.vector_store import get_vector_store


def test_admin_endpoints_are_open_when_auth_is_disabled(client: TestClient) -> None:
    response = client.get("/api/v1/sources")

    assert response.status_code == 200


def test_admin_endpoint_requires_key_when_auth_is_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/sources", headers={"X-Admin-API-Key": "secret"})

    assert response.status_code == 200

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/sources")

    assert response.status_code == 401

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()


def test_admin_endpoint_accepts_valid_key_when_auth_is_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()


def test_ask_requires_user_key_when_auth_is_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("USER_API_KEY", "user-secret")
    monkeypatch.setenv("ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()

    client = TestClient(create_app())

    response = client.post("/api/v1/ask", json={"question": "Есть ли данные?"})

    assert response.status_code == 401

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()


def test_ask_accepts_user_or_admin_key_when_auth_is_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("USER_API_KEY", "user-secret")
    monkeypatch.setenv("ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()

    client = TestClient(create_app())

    user_response = client.post(
        "/api/v1/ask",
        json={"question": "Есть ли данные?"},
        headers={"X-User-API-Key": "user-secret"},
    )
    admin_response = client.post(
        "/api/v1/ask",
        json={"question": "Есть ли данные?"},
        headers={"X-Admin-API-Key": "admin-secret"},
    )

    assert user_response.status_code == 200
    assert admin_response.status_code == 200

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()


def test_admin_endpoint_rejects_user_key_when_auth_is_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("USER_API_KEY", "user-secret")
    monkeypatch.setenv("ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/sources", headers={"X-User-API-Key": "user-secret"})

    assert response.status_code == 401

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
