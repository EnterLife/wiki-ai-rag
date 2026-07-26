from pathlib import Path
from types import SimpleNamespace

import jwt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa

from wiki_ai_rag_api.api import dependencies
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.main import create_app
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.vector_store import get_vector_store
from wiki_ai_rag_api.storage.factory import get_metadata_store


def test_oidc_principal_uses_subject_and_groups(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": "https://identity.example.com/",
            "aud": "wiki-ai-rag",
            "groups": ["engineering", "rag-admin"],
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test"},
    )
    monkeypatch.setenv("OIDC_ISSUER", "https://identity.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "wiki-ai-rag")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://identity.example.com/jwks")
    get_settings.cache_clear()
    monkeypatch.setattr(
        dependencies,
        "_jwks_client",
        lambda url: SimpleNamespace(
            get_signing_key_from_jwt=lambda value: SimpleNamespace(key=private_key.public_key())
        ),
    )

    principal = dependencies._oidc_principal(f"Bearer {token}")

    assert principal.subject == "user-123"
    assert principal.groups == frozenset({"engineering", "rag-admin"})
    assert principal.is_admin is True
    get_settings.cache_clear()


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
    get_metadata_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/sources", headers={"X-Admin-API-Key": "secret"})

    assert response.status_code == 200

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_metadata_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/sources")

    assert response.status_code == 401

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_metadata_store.cache_clear()


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
    get_metadata_store.cache_clear()


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
    get_metadata_store.cache_clear()

    client = TestClient(create_app())

    response = client.post("/api/v1/ask", json={"question": "Есть ли данные?"})

    assert response.status_code == 401

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_metadata_store.cache_clear()


def test_evidence_requires_user_key_when_auth_is_enabled(
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
    get_metadata_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/chunks/chk_unknown")

    assert response.status_code == 401

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_metadata_store.cache_clear()


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
    get_metadata_store.cache_clear()

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
    get_metadata_store.cache_clear()


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
    get_metadata_store.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/sources", headers={"X-User-API-Key": "user-secret"})

    assert response.status_code == 403

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_metadata_store.cache_clear()


def test_source_acl_filters_answers_and_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "finance.md").write_text(
        "Finance approval code is FIN-7788.",
        encoding="utf-8",
    )
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("USER_API_KEY", "user-secret")
    monkeypatch.setenv("ADMIN_API_KEY", "admin-secret")
    monkeypatch.setenv("USER_API_KEY_GROUPS", "hr")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "state.json"))
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_metadata_store.cache_clear()
    client = TestClient(create_app())
    admin_headers = {"X-Admin-API-Key": "admin-secret"}
    user_headers = {"X-User-API-Key": "user-secret"}
    source = client.post(
        "/api/v1/sources",
        headers=admin_headers,
        json={
            "name": "Finance",
            "type": "filesystem",
            "config": {"path": str(wiki_dir)},
            "access_groups": ["finance"],
        },
    ).json()
    client.post(
        "/api/v1/indexing/jobs",
        headers=admin_headers,
        json={"source_id": source["id"]},
    )
    admin_answer = client.post(
        "/api/v1/ask",
        headers=admin_headers,
        json={"question": "What is the finance approval code?"},
    ).json()
    chunk_id = admin_answer["citations"][0]["chunk_id"]

    denied_answer = client.post(
        "/api/v1/ask",
        headers=user_headers,
        json={"question": "What is the finance approval code?"},
    )
    denied_evidence = client.get(
        f"/api/v1/chunks/{chunk_id}",
        headers=user_headers,
    )
    denied_sources = client.get(
        "/api/v1/sources/available",
        headers=user_headers,
    )

    assert denied_answer.json()["status"] == "insufficient_context"
    assert denied_evidence.status_code == 404
    assert denied_sources.json() == []

    monkeypatch.setenv("USER_API_KEY_GROUPS", "finance")
    get_settings.cache_clear()
    allowed_answer = client.post(
        "/api/v1/ask",
        headers=user_headers,
        json={"question": "What is the finance approval code?"},
    )
    allowed_sources = client.get(
        "/api/v1/sources/available",
        headers=user_headers,
    )

    assert allowed_answer.json()["status"] == "answered"
    assert [item["id"] for item in allowed_sources.json()] == [source["id"]]
    get_settings.cache_clear()
    get_metadata_store.cache_clear()
