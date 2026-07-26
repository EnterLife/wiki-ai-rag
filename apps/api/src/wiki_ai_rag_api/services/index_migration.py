from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.indexing import IndexingService
from wiki_ai_rag_api.services.vector_store import QdrantVectorStore
from wiki_ai_rag_api.storage.factory import get_metadata_store


async def rebuild_qdrant_collection() -> str:
    settings = get_settings()
    if settings.vector_store_provider != "qdrant" or not settings.qdrant_use_alias:
        raise ValueError("Qdrant alias mode must be enabled for versioned rebuilds")

    version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    target_collection = f"{settings.qdrant_collection}_v_{version}"
    staging_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=target_collection,
        vector_size=settings.embedding_dimension,
        trust_env=settings.qdrant_trust_env,
        vector_weight=settings.retrieval_vector_weight,
        keyword_weight=settings.retrieval_keyword_weight,
        keyword_candidate_limit=settings.retrieval_keyword_candidate_limit,
    )
    service = IndexingService(vector_store=staging_store)
    sources = [
        source
        for source in get_metadata_store().list_sources()
        if source.get("enabled", True)
    ]
    if not sources:
        raise RuntimeError("Versioned rebuild requires at least one enabled source")
    for source in sources:
        result = await service._index_source(source)
        if result.failed_documents:
            raise RuntimeError(
                f"Versioned rebuild stopped: source {source['id']} has failed documents"
            )
        staging_store.replace_chunks_for_source(
            source["id"],
            [service._chunk_to_dict(chunk) for chunk in result.chunks],
        )

    _promote_alias(
        staging_store,
        alias_name=settings.qdrant_collection,
        collection_name=target_collection,
    )
    return target_collection


def _promote_alias(
    vector_store: QdrantVectorStore,
    *,
    alias_name: str,
    collection_name: str,
) -> None:
    from qdrant_client.models import (
        CreateAlias,
        CreateAliasOperation,
        DeleteAlias,
        DeleteAliasOperation,
    )

    aliases = vector_store.client.get_aliases().aliases
    operations: list[DeleteAliasOperation | CreateAliasOperation] = []
    if any(alias.alias_name == alias_name for alias in aliases):
        operations.append(
            DeleteAliasOperation(delete_alias=DeleteAlias(alias_name=alias_name))
        )
    operations.append(
        CreateAliasOperation(
            create_alias=CreateAlias(
                collection_name=collection_name,
                alias_name=alias_name,
            )
        )
    )
    vector_store.client.update_collection_aliases(operations)


def main() -> None:
    collection_name = asyncio.run(rebuild_qdrant_collection())
    print(f"Promoted Qdrant collection: {collection_name}")


if __name__ == "__main__":
    main()
