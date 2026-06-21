from fastapi import APIRouter

from wiki_ai_rag_api.schemas.metrics import MetricsSnapshot
from wiki_ai_rag_api.services.metrics import metrics_registry

router = APIRouter()


@router.get("/metrics", response_model=MetricsSnapshot)
async def get_metrics() -> MetricsSnapshot:
    return MetricsSnapshot(**metrics_registry.snapshot())

