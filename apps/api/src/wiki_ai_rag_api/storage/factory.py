from functools import lru_cache

from sqlalchemy import URL

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.json_store import JsonStore
from wiki_ai_rag_api.storage.postgres_store import PostgresMetadataStore


@lru_cache
def get_metadata_store() -> MetadataStore:
    settings = get_settings()
    if settings.metadata_store_provider == "json":
        return JsonStore(settings.storage_path)
    if settings.metadata_store_provider == "postgres":
        database_url = settings.metadata_database_url or URL.create(
            "postgresql+psycopg",
            username=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
        )
        return PostgresMetadataStore(database_url)
    raise ValueError(
        f"Metadata store provider '{settings.metadata_store_provider}' is not implemented yet"
    )
