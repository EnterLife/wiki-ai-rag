from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["filesystem", "postgresql", "mysql", "sqlite", "wiki", "transcript"]


class SourceSchedule(BaseModel):
    mode: Literal["manual", "scheduled"] = "manual"
    interval_hours: int | None = Field(default=None, ge=1)


class SourceCreate(BaseModel):
    name: str = Field(min_length=1)
    type: SourceType
    config: dict[str, Any]
    enabled: bool = True
    schedule: SourceSchedule = Field(default_factory=SourceSchedule)


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    schedule: SourceSchedule | None = None


class SourceRead(BaseModel):
    id: str
    name: str
    type: SourceType
    enabled: bool
    document_count: int
    last_indexed_at: datetime | None


class SourceTestResponse(BaseModel):
    source_id: str
    ok: bool
    message: str
