from fastapi import APIRouter, Depends, HTTPException, status

from wiki_ai_rag_api.api.dependencies import enforce_question_rate_limit, require_user_or_admin
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.schemas.agentic import AgenticAskRequest, AgenticAskResponse
from wiki_ai_rag_api.services.access import AccessContext
from wiki_ai_rag_api.services.agentic import AgenticRagService

router = APIRouter(dependencies=[Depends(enforce_question_rate_limit)])


@router.post("/ask", response_model=AgenticAskResponse)
async def ask_agentic(
    payload: AgenticAskRequest,
    principal: AccessContext = Depends(require_user_or_admin),
) -> AgenticAskResponse:
    if not get_settings().agentic_rag_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agentic RAG is disabled",
        )
    return await AgenticRagService().answer(payload, access_context=principal)
