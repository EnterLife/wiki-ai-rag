from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, model_validator
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_db: str = "wiki_ai_rag"
    postgres_user: str = "wiki_ai_rag"
    postgres_password: str = "wiki_ai_rag"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    app_env: str = "development"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "wiki_ai_rag_chunks"
    qdrant_trust_env: bool = False
    qdrant_use_alias: bool = False
    storage_path: Path = Path("storage/wiki_ai_rag_state.json")
    metadata_store_provider: str = "json"
    metadata_database_url: str | None = None
    vector_store_provider: str = "json"
    embedding_dimension: int = 256

    api_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    llm_provider: str = "extractive"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1"
    llm_api_key: str | None = None
    llm_require_structured_output: bool = False
    embeddings_provider: str = "hashing"
    embeddings_base_url: str = "http://localhost:1234/v1"
    embeddings_model: str = "text-embedding-3-small"
    embeddings_api_key: str | None = None
    enable_scheduler: bool = False
    scheduler_poll_seconds: int = 60
    indexing_execution_mode: str = "inline"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    auth_enabled: bool = False
    auth_provider: str = "api_key"
    user_api_key: str | None = None
    admin_api_key: str | None = None
    user_api_key_subject: str = "api-key-user"
    user_api_key_groups: Annotated[list[str], NoDecode] = Field(default_factory=list)
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_groups_claim: str = "groups"
    oidc_admin_group: str = "rag-admin"
    credentials_encryption_key: str | None = None
    rate_limit_enabled: bool = False
    question_rate_limit_per_minute: int = 60
    log_level: str = "INFO"
    log_question_text: bool = False
    retrieval_vector_weight: float = 0.65
    retrieval_keyword_weight: float = 0.35
    retrieval_keyword_candidate_limit: int = 200
    retrieval_candidates_top_k: int = 50
    retrieval_min_score: float = 0.15
    retrieval_min_vector_score: float = 0.3
    retrieval_min_keyword_score: float = 0.2
    reranker_provider: str = "none"
    reranker_base_url: str = "http://localhost:8080"
    reranker_model: str | None = None
    reranker_api_key: str | None = None
    conversation_memory_enabled: bool = False
    conversation_memory_max_turns: int = 6
    agentic_rag_enabled: bool = False
    agentic_max_steps: int = 3

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("user_api_key_groups", mode="before")
    @classmethod
    def split_user_groups(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [group.strip() for group in value.split(",") if group.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.app_env != "production":
            return self
        requirements = {
            "AUTH_ENABLED=true": self.auth_enabled,
            "AUTH_PROVIDER=oidc": self.auth_provider == "oidc",
            "OIDC_ISSUER": bool(self.oidc_issuer),
            "OIDC_JWKS_URL": bool(self.oidc_jwks_url),
            "CREDENTIALS_ENCRYPTION_KEY": bool(self.credentials_encryption_key),
            "METADATA_STORE_PROVIDER=postgres": self.metadata_store_provider == "postgres",
            "VECTOR_STORE_PROVIDER=qdrant": self.vector_store_provider == "qdrant",
            "QDRANT_USE_ALIAS=true": self.qdrant_use_alias,
            "INDEXING_EXECUTION_MODE=celery": self.indexing_execution_mode == "celery",
            "LLM_REQUIRE_STRUCTURED_OUTPUT=true": self.llm_require_structured_output,
            "RATE_LIMIT_ENABLED=true": self.rate_limit_enabled,
            "AGENTIC_RAG_ENABLED=false": not self.agentic_rag_enabled,
            "non-extractive LLM provider": self.llm_provider not in {"extractive", "stub"},
            "non-hashing embeddings provider": self.embeddings_provider not in {"hashing", "stub"},
        }
        missing = [name for name, satisfied in requirements.items() if not satisfied]
        if missing:
            raise ValueError(
                "Unsafe production configuration; required: " + ", ".join(missing)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
