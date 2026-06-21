from fastapi import APIRouter

from wiki_ai_rag_api.api.v1 import ask, audit, evidence, health, indexing, metrics, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(ask.router, tags=["ask"])
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(indexing.router, prefix="/indexing", tags=["indexing"])
