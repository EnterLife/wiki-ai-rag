from typing import Literal

from pydantic import BaseModel, Field

from wiki_ai_rag_api.schemas.ask import Citation


class AgenticAskRequest(BaseModel):
    question: str = Field(min_length=1)
    source_ids: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=20)
    session_id: str | None = Field(default=None, min_length=1)


class ToolCallRead(BaseModel):
    name: str
    status: Literal["success", "failed"]
    summary: str


class AgenticAskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    status: Literal["answered", "insufficient_context", "error"]
    tool_calls: list[ToolCallRead]
    confidence: float | None = Field(default=None, ge=0, le=1)
    insufficient_context_reason: str | None = None
