from fastapi import APIRouter, Depends

from wiki_ai_rag_api.api.dependencies import enforce_question_rate_limit, require_user_or_admin
from wiki_ai_rag_api.schemas.ask import AskRequest, AskResponse
from wiki_ai_rag_api.services.rag import RagService

router = APIRouter(dependencies=[Depends(require_user_or_admin), Depends(enforce_question_rate_limit)])


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    return await RagService().answer(payload)
