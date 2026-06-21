from dataclasses import dataclass

from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.vector_store import VectorStore, get_vector_store


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    source_id: str
    title: str
    score: float
    metadata: dict


class RetrievalService:
    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.embeddings = get_embedding_provider()

    async def search(
        self,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        query_embedding = self.embeddings.embed(query)

        results = self.vector_store.search(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            source_ids=source_ids,
        )
        return [
            RetrievedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                text=result.text,
                source_id=result.source_id,
                title=result.title,
                score=result.score,
                metadata=result.metadata,
            )
            for result in results
        ]
