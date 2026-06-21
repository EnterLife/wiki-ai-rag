from dataclasses import dataclass

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.metrics import metrics_registry
from wiki_ai_rag_api.services.reranking import Reranker, get_reranker
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
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.embeddings = get_embedding_provider()
        self.reranker = reranker or get_reranker()

    async def search(
        self,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        query_embedding = self.embeddings.embed(query)
        settings = get_settings()
        candidate_top_k = (
            max(top_k, settings.retrieval_candidates_top_k)
            if settings.reranker_provider != "none"
            else top_k
        )

        results = self.vector_store.search(
            query=query,
            query_embedding=query_embedding,
            top_k=candidate_top_k,
            source_ids=source_ids,
        )
        if settings.reranker_provider != "none":
            with metrics_registry.time_block("retrieval.rerank_ms"):
                results = self.reranker.rerank(query=query, candidates=results, top_k=top_k)
            metrics_registry.increment("retrieval.reranked")
        else:
            results = results[:top_k]
        metrics_registry.increment("retrieval.searches")
        metrics_registry.increment("retrieval.results", len(results))
        if any(result.keyword_score > 0 for result in results):
            metrics_registry.increment("retrieval.keyword_hits")
        if any(result.vector_score > 0 for result in results):
            metrics_registry.increment("retrieval.vector_hits")
        return [
            RetrievedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                text=result.text,
                source_id=result.source_id,
                title=result.title,
                score=result.score,
                metadata=result.metadata,
                vector_score=result.vector_score,
                keyword_score=result.keyword_score,
                combined_score=result.combined_score,
            )
            for result in results
        ]
