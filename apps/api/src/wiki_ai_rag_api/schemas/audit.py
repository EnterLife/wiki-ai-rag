from datetime import datetime

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: str
    status: str
    details: dict = Field(default_factory=dict)
    created_at: datetime

