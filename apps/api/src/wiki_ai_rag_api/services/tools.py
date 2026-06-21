from __future__ import annotations

from dataclasses import dataclass

from wiki_ai_rag_api.services.evidence import EvidenceService
from wiki_ai_rag_api.services.retrieval import RetrievedChunk, RetrievalService
from wiki_ai_rag_api.services.sources import SourceService


@dataclass(frozen=True)
class ToolCall:
    name: str
    status: str
    summary: str


class KnowledgeToolRegistry:
    def __init__(
        self,
        retrieval: RetrievalService | None = None,
        evidence: EvidenceService | None = None,
        sources: SourceService | None = None,
    ) -> None:
        self.retrieval = retrieval or RetrievalService()
        self.evidence = evidence or EvidenceService()
        self.sources = sources or SourceService()

    async def search_knowledge_base(
        self,
        *,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> tuple[list[RetrievedChunk], ToolCall]:
        chunks = await self.retrieval.search(query=query, top_k=top_k, source_ids=source_ids)
        return chunks, ToolCall(
            name="search_knowledge_base",
            status="success",
            summary=f"retrieved {len(chunks)} chunks",
        )

    def get_chunk(self, chunk_id: str) -> ToolCall:
        chunk = self.evidence.get_chunk(chunk_id)
        return ToolCall(
            name="get_chunk",
            status="success" if chunk else "failed",
            summary="chunk found" if chunk else "chunk not found",
        )

    def list_sources(self) -> ToolCall:
        sources = self.sources.list_sources()
        return ToolCall(
            name="list_sources",
            status="success",
            summary=f"listed {len(sources)} sources",
        )
