from pathlib import Path

from wiki_ai_rag_api.services.embeddings import HashingEmbeddingProvider
from wiki_ai_rag_api.services.vector_store import JsonVectorStore
from wiki_ai_rag_api.storage.json_store import JsonStore


def test_json_vector_store_searches_and_filters_sources(tmp_path: Path) -> None:
    provider = HashingEmbeddingProvider(dimension=32)
    store = JsonStore(tmp_path / "state.json")
    vector_store = JsonVectorStore(store)
    vector_store.replace_chunks_for_source(
        "src_a",
        [
            {
                "chunk_id": "chk_a",
                "document_id": "doc_a",
                "source_id": "src_a",
                "title": "Product X",
                "text": "Product X supports PostgreSQL imports.",
                "embedding": provider.embed("Product X supports PostgreSQL imports."),
                "metadata": {"path": "/wiki/product.md"},
                "hash": "hash_a",
            }
        ],
    )
    vector_store.replace_chunks_for_source(
        "src_b",
        [
            {
                "chunk_id": "chk_b",
                "document_id": "doc_b",
                "source_id": "src_b",
                "title": "Other",
                "text": "Unrelated policy text.",
                "embedding": provider.embed("Unrelated policy text."),
                "metadata": {},
                "hash": "hash_b",
            }
        ],
    )

    results = vector_store.search(
        query="PostgreSQL imports",
        query_embedding=provider.embed("PostgreSQL imports"),
        top_k=5,
        source_ids=["src_a"],
    )

    assert [result.chunk_id for result in results] == ["chk_a"]

    chunk = vector_store.get_chunk("chk_a")
    assert chunk is not None
    assert chunk.document_id == "doc_a"
    assert "PostgreSQL" in chunk.text
