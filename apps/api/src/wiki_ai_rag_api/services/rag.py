import hashlib
import logging

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.core.logging import log_event
from wiki_ai_rag_api.schemas.ask import AskRequest, AskResponse, Citation
from wiki_ai_rag_api.services.llm import GroundedContext, LlmService
from wiki_ai_rag_api.services.metrics import metrics_registry
from wiki_ai_rag_api.services.policy import INSUFFICIENT_CONTEXT_MESSAGE
from wiki_ai_rag_api.services.retrieval import RetrievedChunk, RetrievalService

logger = logging.getLogger("wiki_ai_rag_api.rag")


class RagService:
    def __init__(
        self,
        retrieval: RetrievalService | None = None,
        llm: LlmService | None = None,
    ) -> None:
        self.retrieval = retrieval or RetrievalService()
        self.llm = llm or LlmService()

    async def answer(self, request: AskRequest) -> AskResponse:
        log_event(
            logger,
            "rag.question.received",
            **_question_log_fields(request),
        )
        with metrics_registry.time_block("ask.retrieval_ms"):
            chunks = await self.retrieval.search(
                query=request.question,
                top_k=request.top_k,
                source_ids=request.source_ids,
            )
        log_event(
            logger,
            "rag.retrieval.completed",
            question_hash=_question_hash(request.question),
            retrieved_count=len(chunks),
            source_ids=sorted({chunk.source_id for chunk in chunks}),
            max_score=round(max((chunk.score for chunk in chunks), default=0.0), 4),
        )
        if not chunks:
            metrics_registry.increment("ask.insufficient_context")
            log_event(
                logger,
                "rag.answer.insufficient_context",
                question_hash=_question_hash(request.question),
                reason="no_retrieved_context",
            )
            return AskResponse(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                citations=[],
                status="insufficient_context",
            )

        citations = [_citation_from_chunk(index, chunk) for index, chunk in enumerate(chunks, start=1)]
        with metrics_registry.time_block("ask.llm_ms"):
            answer = await self.llm.answer_with_context(
                question=request.question,
                context=[
                    GroundedContext(
                        citation_id=citation.id,
                        title=citation.title,
                        quote=citation.quote,
                        source_id=citation.source_id,
                        url=citation.url,
                    )
                    for citation in citations
                ],
            )
        if answer == INSUFFICIENT_CONTEXT_MESSAGE:
            metrics_registry.increment("ask.insufficient_context")
            log_event(
                logger,
                "rag.answer.insufficient_context",
                question_hash=_question_hash(request.question),
                reason="llm_refused_context",
            )
            return AskResponse(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                citations=[],
                status="insufficient_context",
            )

        metrics_registry.increment("ask.answered")
        log_event(
            logger,
            "rag.answer.completed",
            question_hash=_question_hash(request.question),
            citations_count=len(citations),
            source_ids=sorted({citation.source_id for citation in citations}),
        )
        return AskResponse(
            answer=answer,
            citations=citations,
            status="answered",
        )


def _citation_from_chunk(index: int, chunk: RetrievedChunk) -> Citation:
    return Citation(
        id=str(index),
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        source_id=chunk.source_id,
        title=chunk.title,
        section=chunk.metadata.get("section"),
        url=chunk.metadata.get("url") or chunk.metadata.get("path"),
        quote=_short_quote(chunk.text),
        timestamp=chunk.metadata.get("timestamp"),
        score=round(chunk.score, 4),
    )


def _short_quote(text: str, max_chars: int = 500) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return f"{compact[: max_chars - 1].rstrip()}..."


def _question_hash(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def _question_log_fields(request: AskRequest) -> dict:
    fields = {
        "question_hash": _question_hash(request.question),
        "question_length": len(request.question),
        "top_k": request.top_k,
        "source_filter_count": len(request.source_ids or []),
    }
    if get_settings().log_question_text:
        fields["question"] = request.question
    return fields
