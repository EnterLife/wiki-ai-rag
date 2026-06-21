from fastapi import APIRouter, Depends, HTTPException, status

from wiki_ai_rag_api.api.dependencies import require_admin
from wiki_ai_rag_api.schemas.indexing import IndexingJobCreate, IndexingJobRead
from wiki_ai_rag_api.services.indexing import IndexingService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/jobs", response_model=IndexingJobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_indexing_job(payload: IndexingJobCreate) -> IndexingJobRead:
    job = await IndexingService().create_job(source_id=payload.source_id, mode=payload.mode)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return job


@router.get("/jobs", response_model=list[IndexingJobRead])
async def list_indexing_jobs(source_id: str | None = None, limit: int = 50) -> list[IndexingJobRead]:
    bounded_limit = min(max(limit, 1), 200)
    return IndexingService().list_jobs(source_id=source_id, limit=bounded_limit)


@router.get("/jobs/{job_id}", response_model=IndexingJobRead)
async def get_indexing_job(job_id: str) -> IndexingJobRead:
    job = IndexingService().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
