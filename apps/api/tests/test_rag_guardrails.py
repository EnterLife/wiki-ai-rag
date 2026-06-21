import asyncio

from wiki_ai_rag_api.schemas.ask import AskRequest
from wiki_ai_rag_api.services.policy import INSUFFICIENT_CONTEXT_MESSAGE
from wiki_ai_rag_api.services.rag import RagService
from wiki_ai_rag_api.services.retrieval import RetrievedChunk


class FakeRetrieval:
    async def search(self, query: str, top_k: int, source_ids: list[str] | None = None):
        return [
            RetrievedChunk(
                chunk_id="chk_1",
                document_id="doc_1",
                text="Product X supports PostgreSQL imports.",
                source_id="src_1",
                title="Product X",
                score=0.9,
                metadata={"path": "/wiki/product.md"},
            )
        ]


class RefusingLlm:
    async def answer_with_context(self, question: str, context):
        return INSUFFICIENT_CONTEXT_MESSAGE


def test_rag_drops_citations_when_llm_refuses() -> None:
    service = RagService(retrieval=FakeRetrieval(), llm=RefusingLlm())

    response = asyncio.run(service.answer(AskRequest(question="Что поддерживает Product X?")))

    assert response.status == "insufficient_context"
    assert response.answer == INSUFFICIENT_CONTEXT_MESSAGE
    assert response.citations == []
