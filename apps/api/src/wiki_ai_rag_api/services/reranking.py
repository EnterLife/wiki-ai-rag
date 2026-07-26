from __future__ import annotations

import re
from functools import lru_cache
from typing import Protocol

import httpx

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.vector_store import VectorSearchResult


class Reranker(Protocol):
    def rerank(
        self,
        *,
        query: str,
        candidates: list[VectorSearchResult],
        top_k: int,
    ) -> list[VectorSearchResult]:
        raise NotImplementedError


class NoopReranker:
    def rerank(
        self,
        *,
        query: str,
        candidates: list[VectorSearchResult],
        top_k: int,
    ) -> list[VectorSearchResult]:
        return candidates[:top_k]


class KeywordReranker:
    def rerank(
        self,
        *,
        query: str,
        candidates: list[VectorSearchResult],
        top_k: int,
    ) -> list[VectorSearchResult]:
        query_terms = _tokenize(query)
        reranked = [
            _with_rerank_score(candidate, _keyword_rerank_score(query_terms, candidate))
            for candidate in candidates
        ]
        return sorted(reranked, key=lambda candidate: candidate.metadata["retrieval"]["rerank_score"], reverse=True)[
            :top_k
        ]


class HttpReranker:
    def __init__(
        self,
        *,
        base_url: str,
        model: str | None = None,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30)

    def rerank(
        self,
        *,
        query: str,
        candidates: list[VectorSearchResult],
        top_k: int,
    ) -> list[VectorSearchResult]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload: dict = {
            "query": query,
            "documents": [f"{candidate.title}\n{candidate.text}" for candidate in candidates],
            "top_n": top_k,
        }
        if self.model:
            payload["model"] = self.model
        response = self.client.post(
            f"{self.base_url}/rerank",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        ranked: list[VectorSearchResult] = []
        for item in response.json().get("results", []):
            index = int(item["index"])
            if index < 0 or index >= len(candidates):
                continue
            score = float(item.get("relevance_score", item.get("score", 0.0)))
            ranked.append(_with_rerank_score(candidates[index], score))
        return ranked[:top_k]


@lru_cache
def get_reranker() -> Reranker:
    provider = get_settings().reranker_provider
    if provider == "none":
        return NoopReranker()
    if provider == "keyword":
        return KeywordReranker()
    if provider == "http":
        settings = get_settings()
        return HttpReranker(
            base_url=settings.reranker_base_url,
            model=settings.reranker_model,
            api_key=settings.reranker_api_key,
        )
    raise ValueError(f"Reranker provider '{provider}' is not implemented yet")


def _keyword_rerank_score(query_terms: set[str], candidate: VectorSearchResult) -> float:
    if not query_terms:
        return candidate.score
    text_terms = _tokenize(f"{candidate.title}\n{candidate.text}")
    if not text_terms:
        return 0.0
    return len(query_terms.intersection(text_terms)) / len(query_terms)


def _with_rerank_score(candidate: VectorSearchResult, rerank_score: float) -> VectorSearchResult:
    metadata = dict(candidate.metadata)
    retrieval_metadata = dict(metadata.get("retrieval", {}))
    retrieval_metadata["rerank_score"] = round(rerank_score, 6)
    metadata["retrieval"] = retrieval_metadata
    return VectorSearchResult(
        chunk_id=candidate.chunk_id,
        document_id=candidate.document_id,
        source_id=candidate.source_id,
        title=candidate.title,
        text=candidate.text,
        metadata=metadata,
        score=rerank_score,
        vector_score=candidate.vector_score,
        keyword_score=candidate.keyword_score,
        combined_score=candidate.combined_score,
    )


def _tokenize(text: str) -> set[str]:
    return {term for term in re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()) if len(term) > 2}
