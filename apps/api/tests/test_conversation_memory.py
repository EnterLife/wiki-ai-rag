import pytest

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.schemas.ask import AskRequest
from wiki_ai_rag_api.services.access import AccessContext
from wiki_ai_rag_api.services.conversation import reset_conversation_memory
from wiki_ai_rag_api.services.rag import RagService
from wiki_ai_rag_api.services.retrieval import RetrievedChunk


class CapturingRetrieval:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(
        self,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
        access_context=None,
    ):
        self.queries.append(query)
        return [
            RetrievedChunk(
                chunk_id="chk_1",
                document_id="vpn.md",
                text="OpenVPN routing is configured in the client profile.",
                source_id="src_1",
                title="OpenVPN",
                score=0.9,
                metadata={"path": "/wiki/vpn.md"},
            )
        ]


class CitingLlm:
    async def answer_with_context(self, question: str, context):
        return "OpenVPN routing is configured in the client profile [1]."


@pytest.mark.asyncio
async def test_conversation_memory_expands_follow_up_retrieval_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONVERSATION_MEMORY_ENABLED", "true")
    monkeypatch.setenv("CONVERSATION_MEMORY_MAX_TURNS", "3")
    get_settings.cache_clear()
    reset_conversation_memory()
    retrieval = CapturingRetrieval()

    try:
        service = RagService(retrieval=retrieval, llm=CitingLlm())
        await service.answer(AskRequest(question="Расскажи про OpenVPN", session_id="session-1"))
        await service.answer(AskRequest(question="А маршрутизация?", session_id="session-1"))
    finally:
        get_settings.cache_clear()
        reset_conversation_memory()

    assert retrieval.queries[0] == "Расскажи про OpenVPN"
    assert retrieval.queries[1] == "Расскажи про OpenVPN\nА маршрутизация?"


@pytest.mark.asyncio
async def test_conversation_memory_is_isolated_by_authenticated_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONVERSATION_MEMORY_ENABLED", "true")
    get_settings.cache_clear()
    reset_conversation_memory()
    retrieval = CapturingRetrieval()

    try:
        service = RagService(retrieval=retrieval, llm=CitingLlm())
        await service.answer(
            AskRequest(question="Private finance question", session_id="shared-session"),
            access_context=AccessContext(subject="finance-user"),
        )
        await service.answer(
            AskRequest(question="Follow up", session_id="shared-session"),
            access_context=AccessContext(subject="engineering-user"),
        )
    finally:
        get_settings.cache_clear()
        reset_conversation_memory()

    assert retrieval.queries == ["Private finance question", "Follow up"]
