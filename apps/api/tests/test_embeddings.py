import pytest
import httpx

from wiki_ai_rag_api.services.embeddings import (
    HashingEmbeddingProvider,
    OpenAiCompatibleEmbeddingProvider,
    cosine_similarity,
)


def test_hashing_embeddings_are_deterministic_and_normalized() -> None:
    provider = HashingEmbeddingProvider(dimension=32)

    first = provider.embed("Product X supports PostgreSQL imports")
    second = provider.embed("Product X supports PostgreSQL imports")

    assert first == second
    assert len(first) == 32
    assert cosine_similarity(first, first) == pytest.approx(1.0)


def test_empty_embedding_has_zero_similarity() -> None:
    provider = HashingEmbeddingProvider(dimension=32)

    assert cosine_similarity(provider.embed(""), provider.embed("anything")) == 0.0


def test_openai_compatible_embeddings_provider_posts_expected_request() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
        )

    provider = OpenAiCompatibleEmbeddingProvider(
        base_url="http://embeddings.local/v1",
        model="bge-m3",
        api_key="secret",
        dimension=3,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    embedding = provider.embed("Product X")

    assert embedding == [0.1, 0.2, 0.3]
    assert captured_request is not None
    assert str(captured_request.url) == "http://embeddings.local/v1/embeddings"
    assert captured_request.headers["Authorization"] == "Bearer secret"
    assert captured_request.read() == b'{"model":"bge-m3","input":"Product X"}'


def test_openai_compatible_embeddings_provider_validates_dimension() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})

    provider = OpenAiCompatibleEmbeddingProvider(
        base_url="http://embeddings.local/v1",
        model="bge-m3",
        api_key=None,
        dimension=3,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        provider.embed("Product X")
