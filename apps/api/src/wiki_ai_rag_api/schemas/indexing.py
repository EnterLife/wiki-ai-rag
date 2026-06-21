from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class IndexingJobCreate(BaseModel):
    source_id: str
    mode: Literal["full", "incremental"] = "full"


class IndexingJobRead(BaseModel):
    job_id: str
    source_id: str
    status: str
    processed_documents: int
    failed_documents: int
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None

