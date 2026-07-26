from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wiki_ai_rag_api.services.access import current_access_context
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.factory import get_metadata_store


class AuditService:
    def __init__(self, store: MetadataStore | None = None) -> None:
        self.store = store or get_metadata_store()

    def record(
        self,
        *,
        action: str,
        target_type: str,
        target_id: str,
        status: str = "success",
        details: dict | None = None,
    ) -> dict:
        actor = current_access_context()
        event = {
            "id": f"audit_{uuid4().hex[:12]}",
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "status": status,
            "actor_subject": actor.subject,
            "actor_groups": sorted(actor.groups),
            "actor_is_admin": actor.is_admin,
            "details": details or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        return self.store.append_audit_event(event)

    def list_events(self, limit: int = 100) -> list[dict]:
        return self.store.list_audit_events(limit=limit)
