from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    source_ids: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=20)


class Citation(BaseModel):
    id: str
    chunk_id: str
    document_id: str
    source_id: str
    title: str
    section: str | None = None
    url: str | None = None
    quote: str
    timestamp: str | None = None
    score: float | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    status: Literal["answered", "insufficient_context", "error"]
