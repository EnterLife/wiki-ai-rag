from __future__ import annotations

import logging

from wiki_ai_rag_api.core.logging import log_event
from wiki_ai_rag_api.schemas.agentic import AgenticAskRequest, AgenticAskResponse, ToolCallRead
from wiki_ai_rag_api.services.access import AccessContext, SYSTEM_ACCESS_CONTEXT
from wiki_ai_rag_api.services.llm import GroundedContext, LlmService, extract_citation_ids
from wiki_ai_rag_api.services.policy import INSUFFICIENT_CONTEXT_MESSAGE
from wiki_ai_rag_api.services.rag import _citation_from_chunk, _confidence_from_chunks
from wiki_ai_rag_api.services.tools import KnowledgeToolRegistry

logger = logging.getLogger("wiki_ai_rag_api.agentic")


class AgenticRagService:
    def __init__(
        self,
        tools: KnowledgeToolRegistry | None = None,
        llm: LlmService | None = None,
    ) -> None:
        self.tools = tools or KnowledgeToolRegistry()
        self.llm = llm or LlmService()

    async def answer(
        self,
        request: AgenticAskRequest,
        access_context: AccessContext = SYSTEM_ACCESS_CONTEXT,
    ) -> AgenticAskResponse:
        chunks, search_call = await self.tools.search_knowledge_base(
            query=request.question,
            top_k=request.top_k,
            source_ids=request.source_ids,
            access_context=access_context,
        )
        tool_calls = [ToolCallRead(**search_call.__dict__)]
        log_event(
            logger,
            "agentic.tool.completed",
            tool=search_call.name,
            status=search_call.status,
            summary=search_call.summary,
        )
        if not chunks:
            return AgenticAskResponse(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                citations=[],
                status="insufficient_context",
                tool_calls=tool_calls,
                insufficient_context_reason="no_retrieved_context",
            )

        citations = [_citation_from_chunk(index, chunk) for index, chunk in enumerate(chunks, start=1)]
        answer = await self.llm.answer_with_context(
            question=request.question,
            context=[
                GroundedContext(
                    citation_id=citation.id,
                    title=citation.title,
                    quote=chunk.text,
                    source_id=citation.source_id,
                    url=citation.url,
                )
                for citation, chunk in zip(citations, chunks)
            ],
        )
        if answer == INSUFFICIENT_CONTEXT_MESSAGE:
            return AgenticAskResponse(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                citations=[],
                status="insufficient_context",
                tool_calls=tool_calls,
                insufficient_context_reason="llm_refused_context",
            )

        cited_ids = extract_citation_ids(answer)
        citations = [citation for citation in citations if citation.id in cited_ids]
        return AgenticAskResponse(
            answer=answer,
            citations=citations,
            status="answered",
            tool_calls=tool_calls,
            confidence=_confidence_from_chunks(chunks),
        )
