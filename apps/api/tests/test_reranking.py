import pytest

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.embeddings import get_embedding_provider
from wiki_ai_rag_api.services.reranking import KeywordReranker, get_reranker
from wiki_ai_rag_api.services.retrieval import RetrievalService
from wiki_ai_rag_api.services.vector_store import VectorSearchResult


class CapturingVectorStore:
    def __init__(self) -> None:
        self.requested_top_k: int | None = None

    def search(self, *, query: str, query_embedding: list[float], top_k: int, source_ids=None):
        self.requested_top_k = top_k
        return [
            VectorSearchResult(
                chunk_id="chk_noise",
                document_id="noise.md",
                source_id="src",
                title="Noise",
                text="General unrelated text.",
                metadata={"retrieval": {"combined_score": 0.9}},
                score=0.9,
                combined_score=0.9,
            ),
            VectorSearchResult(
                chunk_id="chk_vpn",
                document_id="vpn.md",
                source_id="src",
                title="VPN",
                text="OpenVPN routing setup guide.",
                metadata={"retrieval": {"combined_score": 0.2}},
                score=0.2,
                combined_score=0.2,
            ),
        ]

    def replace_chunks_for_source(self, source_id: str, chunks: list[dict]) -> None:
        raise NotImplementedError

    def delete_chunks_for_source(self, source_id: str) -> None:
        raise NotImplementedError

    def get_chunk(self, chunk_id: str):
        raise NotImplementedError


def test_keyword_reranker_promotes_keyword_match() -> None:
    reranked = KeywordReranker().rerank(
        query="OpenVPN routing",
        candidates=CapturingVectorStore().search(query="", query_embedding=[], top_k=2),
        top_k=1,
    )

    assert reranked[0].chunk_id == "chk_vpn"
    assert reranked[0].metadata["retrieval"]["rerank_score"] == 1


@pytest.mark.asyncio
async def test_retrieval_service_uses_candidate_top_k_when_reranker_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RERANKER_PROVIDER", "keyword")
    monkeypatch.setenv("RETRIEVAL_CANDIDATES_TOP_K", "25")
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_reranker.cache_clear()
    vector_store = CapturingVectorStore()

    try:
        results = await RetrievalService(vector_store=vector_store).search(
            query="OpenVPN routing",
            top_k=1,
        )
    finally:
        get_settings.cache_clear()
        get_embedding_provider.cache_clear()
        get_reranker.cache_clear()

    assert vector_store.requested_top_k == 25
    assert [result.chunk_id for result in results] == ["chk_vpn"]
