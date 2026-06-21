from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.embeddings import cosine_similarity
from wiki_ai_rag_api.storage.json_store import JsonStore


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: str
    document_id: str
    source_id: str
    title: str
    text: str
    metadata: dict
    score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0


class VectorStore(Protocol):
    def replace_chunks_for_source(self, source_id: str, chunks: list[dict]) -> None:
        raise NotImplementedError

    def delete_chunks_for_source(self, source_id: str) -> None:
        raise NotImplementedError

    def search(
        self,
        *,
        query: str,
        query_embedding: list[float],
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        raise NotImplementedError

    def get_chunk(self, chunk_id: str) -> VectorSearchResult | None:
        raise NotImplementedError


class JsonVectorStore:
    def __init__(
        self,
        store: JsonStore,
        vector_weight: float = 0.65,
        keyword_weight: float = 0.35,
    ) -> None:
        self.store = store
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def replace_chunks_for_source(self, source_id: str, chunks: list[dict]) -> None:
        self.store.replace_chunks_for_source(source_id, chunks)

    def delete_chunks_for_source(self, source_id: str) -> None:
        self.store.replace_chunks_for_source(source_id, [])

    def search(
        self,
        *,
        query: str,
        query_embedding: list[float],
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        allowed_sources = set(source_ids or [])
        results: list[VectorSearchResult] = []
        for chunk in self.store.list_chunks():
            if allowed_sources and chunk["source_id"] not in allowed_sources:
                continue

            keyword_score = _keyword_score(query_terms, chunk["text"], chunk["title"])
            vector_score = cosine_similarity(query_embedding, chunk.get("embedding", []))
            score = _combined_score(
                vector_score=vector_score,
                keyword_score=keyword_score,
                vector_weight=self.vector_weight,
                keyword_weight=self.keyword_weight,
            )
            if score <= 0:
                continue

            metadata = _with_retrieval_metadata(
                chunk.get("metadata", {}),
                vector_score=vector_score,
                keyword_score=keyword_score,
                combined_score=score,
            )
            results.append(
                VectorSearchResult(
                    chunk_id=chunk["chunk_id"],
                    document_id=chunk["document_id"],
                    source_id=chunk["source_id"],
                    title=chunk["title"],
                    text=chunk["text"],
                    metadata=metadata,
                    score=score,
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    combined_score=score,
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

    def get_chunk(self, chunk_id: str) -> VectorSearchResult | None:
        for chunk in self.store.list_chunks():
            if chunk["chunk_id"] != chunk_id:
                continue
            return VectorSearchResult(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                source_id=chunk["source_id"],
                title=chunk["title"],
                text=chunk["text"],
                metadata=chunk.get("metadata", {}),
                score=1.0,
                vector_score=1.0,
                keyword_score=0.0,
                combined_score=1.0,
            )
        return None


class QdrantVectorStore:
    def __init__(
        self,
        url: str,
        collection_name: str,
        vector_size: int,
        trust_env: bool = False,
        vector_weight: float = 0.65,
        keyword_weight: float = 0.35,
        keyword_candidate_limit: int = 200,
    ) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=url, trust_env=trust_env, check_compatibility=False)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.keyword_candidate_limit = keyword_candidate_limit

    def replace_chunks_for_source(self, source_id: str, chunks: list[dict]) -> None:
        self._ensure_collection()
        self.delete_chunks_for_source(source_id)
        if not chunks:
            return

        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk["chunk_id"])),
                vector=chunk["embedding"],
                payload={key: value for key, value in chunk.items() if key != "embedding"},
            )
            for chunk in chunks
        ]
        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    def delete_chunks_for_source(self, source_id: str) -> None:
        self._ensure_collection()

        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_id",
                            match=MatchValue(value=source_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

    def search(
        self,
        *,
        query: str,
        query_embedding: list[float],
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        self._ensure_collection()

        query_filter = self._source_filter(source_ids)
        from qdrant_client.models import SearchRequest

        vector_limit = max(top_k, min(self.keyword_candidate_limit, top_k * 10))
        response = self.client.http.search_api.search_points(
            collection_name=self.collection_name,
            search_request=SearchRequest(
                vector=query_embedding,
                filter=query_filter,
                limit=vector_limit,
                with_payload=True,
            ),
        )
        candidates: dict[str, VectorSearchResult] = {}
        query_terms = _tokenize(query)

        for point in response.result:
            if not point.payload:
                continue
            result = self._point_to_result(point)
            keyword_score = _keyword_score(query_terms, result.text, result.title)
            score = _combined_score(
                vector_score=result.vector_score,
                keyword_score=keyword_score,
                vector_weight=self.vector_weight,
                keyword_weight=self.keyword_weight,
            )
            candidates[result.chunk_id] = _replace_scores(
                result,
                vector_score=result.vector_score,
                keyword_score=keyword_score,
                combined_score=score,
            )

        for result in self._keyword_candidates(query_terms=query_terms, source_ids=source_ids):
            existing = candidates.get(result.chunk_id)
            vector_score = existing.vector_score if existing else 0.0
            keyword_score = result.keyword_score
            score = _combined_score(
                vector_score=vector_score,
                keyword_score=keyword_score,
                vector_weight=self.vector_weight,
                keyword_weight=self.keyword_weight,
            )
            candidates[result.chunk_id] = _replace_scores(
                result,
                vector_score=vector_score,
                keyword_score=keyword_score,
                combined_score=score,
            )

        return sorted(candidates.values(), key=lambda result: result.score, reverse=True)[:top_k]

    def get_chunk(self, chunk_id: str) -> VectorSearchResult | None:
        self._ensure_collection()
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[str(uuid5(NAMESPACE_URL, chunk_id))],
            with_payload=True,
        )
        if not points or not points[0].payload:
            return None
        point = points[0]
        payload = point.payload
        return VectorSearchResult(
            chunk_id=payload["chunk_id"],
            document_id=payload["document_id"],
            source_id=payload["source_id"],
            title=payload["title"],
            text=payload["text"],
            metadata=payload.get("metadata", {}),
            score=1.0,
            vector_score=1.0,
            keyword_score=0.0,
            combined_score=1.0,
        )

    def _keyword_candidates(
        self,
        *,
        query_terms: set[str],
        source_ids: list[str] | None,
    ) -> list[VectorSearchResult]:
        if not query_terms:
            return []

        from qdrant_client.models import FieldCondition, Filter, MatchAny, PayloadSelectorInclude

        scroll_filter = None
        if source_ids:
            scroll_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchAny(any=source_ids),
                    )
                ]
            )
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=scroll_filter,
            limit=self.keyword_candidate_limit,
            with_payload=PayloadSelectorInclude(
                include=["chunk_id", "document_id", "source_id", "title", "text", "metadata"]
            ),
            with_vectors=False,
        )

        results: list[VectorSearchResult] = []
        for point in points:
            if not point.payload:
                continue
            result = self._payload_to_result(point.payload, score=0.0)
            keyword_score = _keyword_score(query_terms, result.text, result.title)
            if keyword_score <= 0:
                continue
            results.append(
                _replace_scores(
                    result,
                    vector_score=0.0,
                    keyword_score=keyword_score,
                    combined_score=keyword_score * self.keyword_weight,
                )
            )
        return results

    def _ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        collections = self.client.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    @staticmethod
    def _source_filter(source_ids: list[str] | None):
        if not source_ids:
            return None

        from qdrant_client.models import FieldCondition, Filter, MatchAny

        return Filter(
            must=[
                FieldCondition(
                    key="source_id",
                    match=MatchAny(any=source_ids),
                )
            ]
        )

    @staticmethod
    def _point_to_result(point) -> VectorSearchResult:
        payload = point.payload
        return QdrantVectorStore._payload_to_result(payload, score=float(point.score))

    @staticmethod
    def _payload_to_result(payload: dict, score: float) -> VectorSearchResult:
        return VectorSearchResult(
            chunk_id=payload["chunk_id"],
            document_id=payload["document_id"],
            source_id=payload["source_id"],
            title=payload["title"],
            text=payload["text"],
            metadata=payload.get("metadata", {}),
            score=score,
            vector_score=score,
            keyword_score=0.0,
            combined_score=score,
        )


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_store_provider == "json":
        return JsonVectorStore(
            JsonStore(settings.storage_path),
            vector_weight=settings.retrieval_vector_weight,
            keyword_weight=settings.retrieval_keyword_weight,
        )
    if settings.vector_store_provider == "qdrant":
        return QdrantVectorStore(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            vector_size=settings.embedding_dimension,
            trust_env=settings.qdrant_trust_env,
            vector_weight=settings.retrieval_vector_weight,
            keyword_weight=settings.retrieval_keyword_weight,
            keyword_candidate_limit=settings.retrieval_keyword_candidate_limit,
        )
    raise ValueError(f"Vector store provider '{settings.vector_store_provider}' is not implemented yet")


def _tokenize(text: str) -> set[str]:
    return {term for term in re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()) if len(term) > 2}


def _keyword_score(query_terms: set[str], text: str, title: str) -> float:
    text_terms = _tokenize(f"{title}\n{text}")
    if not text_terms:
        return 0
    matched_terms = query_terms.intersection(text_terms)
    return len(matched_terms) / len(query_terms)


def _combined_score(
    *,
    vector_score: float,
    keyword_score: float,
    vector_weight: float,
    keyword_weight: float,
) -> float:
    return (vector_weight * max(0.0, vector_score)) + (keyword_weight * max(0.0, keyword_score))


def _with_retrieval_metadata(
    metadata: dict,
    *,
    vector_score: float,
    keyword_score: float,
    combined_score: float,
) -> dict:
    return {
        **metadata,
        "retrieval": {
            "vector_score": round(vector_score, 6),
            "keyword_score": round(keyword_score, 6),
            "combined_score": round(combined_score, 6),
        },
    }


def _replace_scores(
    result: VectorSearchResult,
    *,
    vector_score: float,
    keyword_score: float,
    combined_score: float,
) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        source_id=result.source_id,
        title=result.title,
        text=result.text,
        metadata=_with_retrieval_metadata(
            result.metadata,
            vector_score=vector_score,
            keyword_score=keyword_score,
            combined_score=combined_score,
        ),
        score=combined_score,
        vector_score=vector_score,
        keyword_score=keyword_score,
        combined_score=combined_score,
    )
