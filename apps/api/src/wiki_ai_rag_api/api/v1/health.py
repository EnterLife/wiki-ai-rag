from fastapi import APIRouter, HTTPException, status

from wiki_ai_rag_api.services.vector_store import get_vector_store
from wiki_ai_rag_api.storage.factory import get_metadata_store

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "wiki-ai-rag-api"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    try:
        get_metadata_store().list_sources()
        get_vector_store().healthcheck()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependencies are unavailable",
        ) from exc
    return {"status": "ready", "service": "wiki-ai-rag-api"}
