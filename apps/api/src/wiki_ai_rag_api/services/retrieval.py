from dataclasses import dataclass

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.access import AccessContext, SYSTEM_ACCESS_CONTEXT
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.metrics import metrics_registry
from wiki_ai_rag_api.services.reranking import Reranker, get_reranker
from wiki_ai_rag_api.services.vector_store import VectorStore, get_vector_store
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.factory import get_metadata_store


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
        metadata_store: MetadataStore | None = None,
    ) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.embeddings = get_embedding_provider()
        self.reranker = reranker or get_reranker()
        self.metadata_store = metadata_store or get_metadata_store()

    async def search(
        self,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
        access_context: AccessContext = SYSTEM_ACCESS_CONTEXT,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        source_ids = self._allowed_source_ids(source_ids, access_context)
        if not source_ids:
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
        results = [
            result
            for result in results
            if result.score >= settings.retrieval_min_score
            and (
                settings.reranker_provider != "none"
                or result.vector_score >= settings.retrieval_min_vector_score
                or result.keyword_score >= settings.retrieval_min_keyword_score
            )
        ]
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

    def _allowed_source_ids(
        self,
        requested_source_ids: list[str] | None,
        access_context: AccessContext,
    ) -> list[str]:
        sources = self.metadata_store.list_sources()
        enabled_source_ids = {
            source["id"]
            for source in sources
            if source.get("enabled", True) and access_context.can_access_source(source)
        }
        if requested_source_ids is None:
            return sorted(enabled_source_ids)
        return [
            source_id
            for source_id in requested_source_ids
            if source_id in enabled_source_ids
        ]
