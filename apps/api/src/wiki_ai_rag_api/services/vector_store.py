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
    def __init__(self, store: JsonStore) -> None:
        self.store = store

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

            lexical_score = _lexical_score(query_terms, chunk["text"], chunk["title"])
            vector_score = cosine_similarity(query_embedding, chunk.get("embedding", []))
            score = max(lexical_score, vector_score)
            if score <= 0:
                continue

            results.append(
                VectorSearchResult(
                    chunk_id=chunk["chunk_id"],
                    document_id=chunk["document_id"],
                    source_id=chunk["source_id"],
                    title=chunk["title"],
                    text=chunk["text"],
                    metadata=chunk.get("metadata", {}),
                    score=score,
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
            )
        return None


class QdrantVectorStore:
    def __init__(self, url: str, collection_name: str, vector_size: int) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.vector_size = vector_size

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
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
            points = response.points
        else:
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )

        return [self._point_to_result(point) for point in points if point.payload]

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
        )

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
        return VectorSearchResult(
            chunk_id=payload["chunk_id"],
            document_id=payload["document_id"],
            source_id=payload["source_id"],
            title=payload["title"],
            text=payload["text"],
            metadata=payload.get("metadata", {}),
            score=float(point.score),
        )


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_store_provider == "json":
        return JsonVectorStore(JsonStore(settings.storage_path))
    if settings.vector_store_provider == "qdrant":
        return QdrantVectorStore(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            vector_size=settings.embedding_dimension,
        )
    raise ValueError(f"Vector store provider '{settings.vector_store_provider}' is not implemented yet")


def _tokenize(text: str) -> set[str]:
    return {term for term in re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()) if len(term) > 2}


def _lexical_score(query_terms: set[str], text: str, title: str) -> float:
    text_terms = _tokenize(f"{title}\n{text}")
    if not text_terms:
        return 0
    matched_terms = query_terms.intersection(text_terms)
    return len(matched_terms) / len(query_terms)
