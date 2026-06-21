from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    title: str
    text: str
    metadata: dict
    score: float | None = None

