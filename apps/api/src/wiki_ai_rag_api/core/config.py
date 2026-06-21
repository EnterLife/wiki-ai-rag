from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "wiki_ai_rag_chunks"
    qdrant_trust_env: bool = False
    storage_path: Path = Path("storage/wiki_ai_rag_state.json")
    vector_store_provider: str = "json"
    embedding_dimension: int = 256

    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    llm_provider: str = "extractive"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1"
    llm_api_key: str | None = None
    embeddings_provider: str = "hashing"
    embeddings_base_url: str = "http://localhost:1234/v1"
    embeddings_model: str = "text-embedding-3-small"
    embeddings_api_key: str | None = None
    enable_scheduler: bool = False
    scheduler_poll_seconds: int = 60
    auth_enabled: bool = False
    user_api_key: str | None = None
    admin_api_key: str | None = None
    credentials_encryption_key: str | None = None
    rate_limit_enabled: bool = False
    question_rate_limit_per_minute: int = 60
    log_level: str = "INFO"
    log_question_text: bool = False
    retrieval_vector_weight: float = 0.65
    retrieval_keyword_weight: float = 0.35
    retrieval_keyword_candidate_limit: int = 200
    retrieval_candidates_top_k: int = 50
    reranker_provider: str = "none"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
