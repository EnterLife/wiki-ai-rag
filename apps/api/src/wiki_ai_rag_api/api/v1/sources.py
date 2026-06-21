from fastapi import APIRouter, Depends, HTTPException, status

from wiki_ai_rag_api.api.dependencies import require_admin
from wiki_ai_rag_api.schemas.sources import SourceCreate, SourceRead, SourceTestResponse, SourceUpdate
from wiki_ai_rag_api.services.sources import SourceService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_model=list[SourceRead])
async def list_sources() -> list[SourceRead]:
    return SourceService().list_sources()


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreate) -> SourceRead:
    return SourceService().create_source(payload)


@router.post("/{source_id}/test", response_model=SourceTestResponse)
async def test_source(source_id: str) -> SourceTestResponse:
    result = await SourceService().test_source(source_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return result


@router.patch("/{source_id}", response_model=SourceRead)
async def update_source(source_id: str, payload: SourceUpdate) -> SourceRead:
    result = SourceService().update_source(source_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return result


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str) -> None:
    if not SourceService().delete_source(source_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return None
