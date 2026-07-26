import pytest
from pydantic import ValidationError

from wiki_ai_rag_api.core.config import Settings


def test_production_mode_rejects_development_providers() -> None:
    with pytest.raises(ValidationError, match="Unsafe production configuration"):
        Settings(app_env="production", _env_file=None)


def test_production_mode_accepts_required_safety_controls() -> None:
    settings = Settings(
        app_env="production",
        auth_enabled=True,
        auth_provider="oidc",
        oidc_issuer="https://identity.example.com/",
        oidc_jwks_url="https://identity.example.com/.well-known/jwks.json",
        credentials_encryption_key="configured-by-secret-manager",
        metadata_store_provider="postgres",
        vector_store_provider="qdrant",
        qdrant_use_alias=True,
        indexing_execution_mode="celery",
        llm_provider="openai_compatible",
        embeddings_provider="openai_compatible",
        llm_require_structured_output=True,
        rate_limit_enabled=True,
        _env_file=None,
    )

    assert settings.app_env == "production"
