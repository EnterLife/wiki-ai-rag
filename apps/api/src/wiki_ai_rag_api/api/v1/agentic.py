from fastapi import APIRouter, Depends, HTTPException, status

from wiki_ai_rag_api.api.dependencies import require_user_or_admin
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.schemas.agentic import AgenticAskRequest, AgenticAskResponse
from wiki_ai_rag_api.services.agentic import AgenticRagService

router = APIRouter(dependencies=[Depends(require_user_or_admin)])


@router.post("/ask", response_model=AgenticAskResponse)
async def ask_agentic(payload: AgenticAskRequest) -> AgenticAskResponse:
    if not get_settings().agentic_rag_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agentic RAG is disabled",
        )
    return await AgenticRagService().answer(payload)
