from fastapi import APIRouter, Depends

from wiki_ai_rag_api.api.dependencies import require_admin
from wiki_ai_rag_api.schemas.audit import AuditEvent
from wiki_ai_rag_api.services.audit import AuditService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/audit", response_model=list[AuditEvent])
async def list_audit_events(limit: int = 100) -> list[AuditEvent]:
    bounded_limit = min(max(limit, 1), 500)
    return [AuditEvent(**event) for event in AuditService().list_events(limit=bounded_limit)]

