from __future__ import annotations

import re
import math
from collections import Counter
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
    def healthcheck(self) -> bool:
        raise NotImplementedError

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

    def list_chunk_records_for_source(self, source_id: str) -> list[dict]:
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

    def healthcheck(self) -> bool:
        self.store.list_chunks()
        return True

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
        chunks = [
            chunk
            for chunk in self.store.list_chunks()
            if not allowed_sources or chunk["source_id"] in allowed_sources
        ]
        keyword_scores = _bm25_scores(query_terms, chunks)
        vector_candidates: list[VectorSearchResult] = []
        keyword_candidates: list[VectorSearchResult] = []
        for chunk, keyword_score in zip(chunks, keyword_scores):
            if allowed_sources and chunk["source_id"] not in allowed_sources:
                continue

            vector_score = cosine_similarity(query_embedding, chunk.get("embedding", []))
            result = VectorSearchResult(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                source_id=chunk["source_id"],
                title=chunk["title"],
                text=chunk["text"],
                metadata=chunk.get("metadata", {}),
                score=0.0,
                vector_score=vector_score,
                keyword_score=keyword_score,
            )
            if vector_score > 0:
                vector_candidates.append(result)
            if keyword_score > 0:
                keyword_candidates.append(result)

        return _fuse_rankings(
            vector_candidates=vector_candidates,
            keyword_candidates=keyword_candidates,
            vector_weight=self.vector_weight,
            keyword_weight=self.keyword_weight,
            top_k=top_k,
        )

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

    def list_chunk_records_for_source(self, source_id: str) -> list[dict]:
        return [
            chunk
            for chunk in self.store.list_chunks()
            if chunk["source_id"] == source_id
        ]


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
        use_alias: bool = False,
    ) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=url, trust_env=trust_env, check_compatibility=False)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.keyword_candidate_limit = keyword_candidate_limit
        self.use_alias = use_alias

    def healthcheck(self) -> bool:
        self.client.get_collections()
        return True

    def replace_chunks_for_source(self, source_id: str, chunks: list[dict]) -> None:
        self._ensure_collection()
        from qdrant_client.models import PointIdsList, PointStruct

        existing_ids = self._point_ids_for_source(source_id)
        next_ids = {
            str(uuid5(NAMESPACE_URL, chunk["chunk_id"]))
            for chunk in chunks
        }

        points = [
            PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk["chunk_id"])),
                vector=chunk["embedding"],
                payload={key: value for key, value in chunk.items() if key != "embedding"},
            )
            for chunk in chunks
        ]
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

        stale_ids = existing_ids - next_ids
        if stale_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=sorted(stale_ids)),
                wait=True,
            )

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
        query_terms = _tokenize(query)
        vector_candidates: list[VectorSearchResult] = []

        for point in response.result or []:
            if not point.payload:
                continue
            result = self._point_to_result(point)
            if result.vector_score > 0:
                vector_candidates.append(result)

        keyword_candidates = self._keyword_candidates(
            query_terms=query_terms,
            source_ids=source_ids,
        )
        return _fuse_rankings(
            vector_candidates=vector_candidates,
            keyword_candidates=keyword_candidates,
            vector_weight=self.vector_weight,
            keyword_weight=self.keyword_weight,
            top_k=top_k,
        )

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
        if payload is None:
            return None
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

    def list_chunk_records_for_source(self, source_id: str) -> list[dict]:
        records: list[dict] = []
        for point in self._scroll_source_points(source_id, with_vectors=True):
            if not point.payload:
                continue
            vector = point.vector
            if isinstance(vector, dict):
                vector = next(iter(vector.values()), [])
            records.append({**point.payload, "embedding": list(vector or [])})
        return records

    def _point_ids_for_source(self, source_id: str) -> set[str]:
        return {
            str(point.id)
            for point in self._scroll_source_points(source_id, with_vectors=False)
        }

    def _scroll_source_points(self, source_id: str, *, with_vectors: bool) -> list:
        self._ensure_collection()
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        points: list = []
        offset = None
        while True:
            page, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_id",
                            match=MatchValue(value=source_id),
                        )
                    ]
                ),
                limit=self.keyword_candidate_limit,
                offset=offset,
                with_payload=True,
                with_vectors=with_vectors,
            )
            points.extend(page)
            if offset is None:
                return points

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
        points: list = []
        offset = None
        while True:
            page, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=self.keyword_candidate_limit,
                offset=offset,
                with_payload=PayloadSelectorInclude(
                    include=["chunk_id", "document_id", "source_id", "title", "text", "metadata"]
                ),
                with_vectors=False,
            )
            points.extend(page)
            if offset is None:
                break

        payloads = [point.payload for point in points if point.payload]
        keyword_scores = _bm25_scores(query_terms, payloads)
        results: list[VectorSearchResult] = []
        for payload, keyword_score in zip(payloads, keyword_scores):
            result = self._payload_to_result(payload, score=0.0)
            if keyword_score <= 0:
                continue
            results.append(
                _replace_scores(
                    result,
                    vector_score=0.0,
                    keyword_score=keyword_score,
                    combined_score=0.0,
                )
            )
        return results

    def _ensure_collection(self) -> None:
        from qdrant_client.models import (
            CreateAlias,
            CreateAliasOperation,
            Distance,
            VectorParams,
        )

        collections = self.client.get_collections().collections
        if self.use_alias:
            aliases = self.client.get_aliases().aliases
            if any(alias.alias_name == self.collection_name for alias in aliases):
                return
            if any(collection.name == self.collection_name for collection in collections):
                raise RuntimeError(
                    f"Qdrant collection '{self.collection_name}' conflicts with the logical "
                    "alias name; configure QDRANT_COLLECTION to a new alias before migration"
                )
            physical_name = f"{self.collection_name}_v1"
            if not any(collection.name == physical_name for collection in collections):
                self.client.create_collection(
                    collection_name=physical_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
            self.client.update_collection_aliases(
                [
                    CreateAliasOperation(
                        create_alias=CreateAlias(
                            collection_name=physical_name,
                            alias_name=self.collection_name,
                        )
                    )
                ]
            )
            return
        if any(collection.name == self.collection_name for collection in collections):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    def ensure_collection(self) -> None:
        """Create the physical collection and alias when they do not exist."""
        self._ensure_collection()

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
            use_alias=settings.qdrant_use_alias,
        )
    raise ValueError(f"Vector store provider '{settings.vector_store_provider}' is not implemented yet")


def _tokenize(text: str) -> set[str]:
    return {term for term in re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()) if len(term) > 2}


def _bm25_scores(query_terms: set[str], chunks: list[dict]) -> list[float]:
    if not query_terms or not chunks:
        return [0.0] * len(chunks)
    documents = [
        _tokenize_terms(f"{chunk.get('title', '')}\n{chunk.get('text', '')}")
        for chunk in chunks
    ]
    average_length = sum(len(document) for document in documents) / len(documents)
    document_frequencies = {
        term: sum(1 for document in documents if term in set(document))
        for term in query_terms
    }
    scores: list[float] = []
    for document in documents:
        frequencies = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            document_frequency = document_frequencies[term]
            inverse_document_frequency = math.log(
                1 + (len(documents) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            length_normalization = 1 - 0.75 + (
                0.75 * len(document) / max(1.0, average_length)
            )
            score += inverse_document_frequency * (
                frequency * 2.5 / (frequency + 1.5 * length_normalization)
            )
        scores.append(score)
    max_score = max(scores, default=0.0)
    if max_score <= 0:
        return scores
    return [score / max_score for score in scores]


def _fuse_rankings(
    *,
    vector_candidates: list[VectorSearchResult],
    keyword_candidates: list[VectorSearchResult],
    vector_weight: float,
    keyword_weight: float,
    top_k: int,
) -> list[VectorSearchResult]:
    vector_candidates = sorted(
        vector_candidates,
        key=lambda candidate: candidate.vector_score,
        reverse=True,
    )
    keyword_candidates = sorted(
        keyword_candidates,
        key=lambda candidate: candidate.keyword_score,
        reverse=True,
    )
    candidates = {
        candidate.chunk_id: candidate
        for candidate in [*vector_candidates, *keyword_candidates]
    }
    vector_scores = {
        candidate.chunk_id: candidate.vector_score
        for candidate in vector_candidates
    }
    keyword_scores = {
        candidate.chunk_id: candidate.keyword_score
        for candidate in keyword_candidates
    }
    fused_scores: dict[str, float] = {}
    rrf_k = 60
    for ranking, weight in (
        (vector_candidates, vector_weight),
        (keyword_candidates, keyword_weight),
    ):
        for rank, candidate in enumerate(ranking, start=1):
            fused_scores[candidate.chunk_id] = fused_scores.get(candidate.chunk_id, 0.0) + (
                weight * (rrf_k + 1) / (rrf_k + rank)
            )

    results = [
        _replace_scores(
            candidate,
            vector_score=vector_scores.get(chunk_id, 0.0),
            keyword_score=keyword_scores.get(chunk_id, 0.0),
            combined_score=min(1.0, fused_scores[chunk_id]),
        )
        for chunk_id, candidate in candidates.items()
    ]
    return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]


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


def _tokenize_terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()) if len(term) > 2]
