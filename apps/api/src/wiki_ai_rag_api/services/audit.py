from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.storage.json_store import JsonStore


class AuditService:
    def __init__(self, store: JsonStore | None = None) -> None:
        self.store = store or JsonStore(get_settings().storage_path)

    def record(
        self,
        *,
        action: str,
        target_type: str,
        target_id: str,
        status: str = "success",
        details: dict | None = None,
    ) -> dict:
        event = {
            "id": f"audit_{uuid4().hex[:12]}",
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "status": status,
            "details": details or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        return self.store.append_audit_event(event)

    def list_events(self, limit: int = 100) -> list[dict]:
        return self.store.list_audit_events(limit=limit)

