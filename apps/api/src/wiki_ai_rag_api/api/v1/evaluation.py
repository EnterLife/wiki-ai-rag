from fastapi import APIRouter, Depends

from wiki_ai_rag_api.api.dependencies import require_admin
from wiki_ai_rag_api.schemas.evaluation import (
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
)
from wiki_ai_rag_api.services.evaluation import RetrievalEvaluationService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/retrieval", response_model=RetrievalEvaluationResponse)
async def run_retrieval_evaluation(
    payload: RetrievalEvaluationRequest,
) -> RetrievalEvaluationResponse:
    return await RetrievalEvaluationService().run(payload)
