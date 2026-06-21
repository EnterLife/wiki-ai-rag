from fastapi import APIRouter, HTTPException, status

from wiki_ai_rag_api.schemas.evidence import EvidenceChunk
from wiki_ai_rag_api.services.evidence import EvidenceService

router = APIRouter()


@router.get("/chunks/{chunk_id}", response_model=EvidenceChunk)
async def get_chunk(chunk_id: str) -> EvidenceChunk:
    chunk = EvidenceService().get_chunk(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return chunk

