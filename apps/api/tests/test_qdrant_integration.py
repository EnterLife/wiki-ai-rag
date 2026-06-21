import os
from uuid import uuid4

import pytest

from wiki_ai_rag_api.services.vector_store import QdrantVectorStore


@pytest.mark.skipif(
    os.getenv("RUN_QDRANT_TESTS") != "true",
    reason="Set RUN_QDRANT_TESTS=true to run Qdrant integration tests",
)
def test_qdrant_vector_store_round_trip() -> None:
    pytest.importorskip("qdrant_client")
    collection_name = f"wiki_ai_rag_test_{uuid4().hex}"
    store = QdrantVectorStore(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        collection_name=collection_name,
        vector_size=3,
        trust_env=os.getenv("QDRANT_TRUST_ENV") == "true",
    )

    try:
        store.replace_chunks_for_source(
            "src_qdrant",
            [
                {
                    "chunk_id": "chk_qdrant",
                    "document_id": "doc_qdrant",
                    "source_id": "src_qdrant",
                    "title": "Qdrant Test",
                    "text": "Product X supports Qdrant vector search.",
                    "embedding": [1.0, 0.0, 0.0],
                    "metadata": {"path": "/tmp/qdrant.md"},
                    "hash": "hash_qdrant",
                }
            ],
        )

        results = store.search(
            query="Qdrant vector search",
            query_embedding=[1.0, 0.0, 0.0],
            top_k=3,
        )
        chunk = store.get_chunk("chk_qdrant")

        assert [result.chunk_id for result in results] == ["chk_qdrant"]
        assert chunk is not None
        assert chunk.document_id == "doc_qdrant"
    finally:
        store.client.delete_collection(collection_name=collection_name)
