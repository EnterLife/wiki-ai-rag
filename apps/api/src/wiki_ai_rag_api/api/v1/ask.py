from fastapi import APIRouter, Depends

from wiki_ai_rag_api.api.dependencies import enforce_question_rate_limit, require_user_or_admin
from wiki_ai_rag_api.schemas.ask import AskRequest, AskResponse
from wiki_ai_rag_api.services.access import AccessContext
from wiki_ai_rag_api.services.rag import RagService

router = APIRouter(dependencies=[Depends(enforce_question_rate_limit)])


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    principal: AccessContext = Depends(require_user_or_admin),
) -> AskResponse:
    return await RagService().answer(payload, access_context=principal)
