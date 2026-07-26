from fastapi import APIRouter, Depends, HTTPException, status

from wiki_ai_rag_api.api.dependencies import require_user_or_admin
from wiki_ai_rag_api.schemas.evidence import EvidenceChunk
from wiki_ai_rag_api.services.access import AccessContext
from wiki_ai_rag_api.services.evidence import EvidenceService

router = APIRouter()


@router.get("/chunks/{chunk_id}", response_model=EvidenceChunk)
async def get_chunk(
    chunk_id: str,
    principal: AccessContext = Depends(require_user_or_admin),
) -> EvidenceChunk:
    chunk = EvidenceService().get_chunk(chunk_id, access_context=principal)
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return chunk
