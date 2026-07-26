from datetime import datetime

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: str
    status: str
    actor_subject: str = "system"
    actor_groups: list[str] = Field(default_factory=list)
    actor_is_admin: bool = False
    details: dict = Field(default_factory=dict)
    created_at: datetime
