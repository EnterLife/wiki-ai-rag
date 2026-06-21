from __future__ import annotations

import re
from functools import lru_cache
from typing import Protocol

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


@lru_cache
def get_reranker() -> Reranker:
    provider = get_settings().reranker_provider
    if provider == "none":
        return NoopReranker()
    if provider == "keyword":
        return KeywordReranker()
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
