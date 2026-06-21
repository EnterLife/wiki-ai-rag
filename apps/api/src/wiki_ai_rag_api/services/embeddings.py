from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

import httpx

from wiki_ai_rag_api.core.config import get_settings


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class HashingEmbeddingProvider:
    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAiCompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        dimension: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.dimension = dimension
        self.client = client or httpx.Client(timeout=60)

    def embed(self, text: str) -> list[float]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = self.client.post(
            f"{self.base_url}/embeddings",
            headers=headers,
            json={"model": self.model, "input": text},
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload["data"][0]["embedding"]
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: got {len(embedding)}, expected {self.dimension}"
            )
        return [float(value) for value in embedding]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right))


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embeddings_provider
    if provider in {"hashing", "stub"}:
        return HashingEmbeddingProvider(dimension=settings.embedding_dimension)
    if provider == "openai_compatible":
        return OpenAiCompatibleEmbeddingProvider(
            base_url=settings.embeddings_base_url,
            model=settings.embeddings_model,
            api_key=settings.embeddings_api_key,
            dimension=settings.embedding_dimension,
        )
    raise ValueError(f"Embeddings provider '{provider}' is not implemented yet")


def _tokenize(text: str) -> list[str]:
    return [term for term in re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()) if len(term) > 2]
