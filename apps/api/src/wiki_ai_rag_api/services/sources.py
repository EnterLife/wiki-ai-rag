from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wiki_ai_rag_api.connectors.filesystem import FilesystemConnector
from wiki_ai_rag_api.connectors.postgres import PostgresConnector
from wiki_ai_rag_api.connectors.sqlite import SQLiteConnector
from wiki_ai_rag_api.schemas.sources import SourceCreate, SourceRead, SourceTestResponse, SourceUpdate
from wiki_ai_rag_api.services.access import AccessContext, SYSTEM_ACCESS_CONTEXT
from wiki_ai_rag_api.services.audit import AuditService
from wiki_ai_rag_api.services.secrets import decrypt_config, encrypt_config
from wiki_ai_rag_api.services.vector_store import VectorStore, get_vector_store
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.factory import get_metadata_store


class SourceService:
    def __init__(
        self,
        store: MetadataStore | None = None,
        vector_store: VectorStore | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.store = store or get_metadata_store()
        self.vector_store = vector_store
        self.audit = audit or AuditService(self.store)

    def list_sources(
        self,
        access_context: AccessContext = SYSTEM_ACCESS_CONTEXT,
        *,
        include_disabled: bool = True,
    ) -> list[SourceRead]:
        return [
            self._to_read_model(source)
            for source in self.store.list_sources()
            if (include_disabled or source.get("enabled", True))
            and access_context.can_access_source(source)
        ]

    def create_source(self, payload: SourceCreate) -> SourceRead:
        now = datetime.now(UTC).isoformat()
        source = {
            "id": f"src_{uuid4().hex[:12]}",
            "name": payload.name,
            "type": payload.type,
            "config": encrypt_config(payload.config),
            "enabled": payload.enabled,
            "access_groups": sorted(set(payload.access_groups)),
            "schedule": payload.schedule.model_dump(),
            "document_count": 0,
            "last_indexed_at": None,
            "created_at": now,
            "updated_at": now,
        }
        saved_source = self.store.save_source(source)
        self.audit.record(
            action="source.create",
            target_type="source",
            target_id=saved_source["id"],
            details={"type": saved_source["type"], "name": saved_source["name"]},
        )
        return self._to_read_model(saved_source)

    def update_source(self, source_id: str, payload: SourceUpdate) -> SourceRead | None:
        updates = payload.model_dump(exclude_unset=True)
        if "schedule" in updates and updates["schedule"] is not None:
            schedule = payload.schedule
            if schedule is not None:
                updates["schedule"] = schedule.model_dump()
        if not updates:
            source = self.store.get_source(source_id)
            return self._to_read_model(source) if source else None

        updates["updated_at"] = datetime.now(UTC).isoformat()
        updated_source = self.store.update_source(source_id, updates)
        if updated_source is None:
            return None

        self.audit.record(
            action="source.update",
            target_type="source",
            target_id=source_id,
            details={key: value for key, value in updates.items() if key != "updated_at"},
        )
        return self._to_read_model(updated_source)

    async def test_source(self, source_id: str) -> SourceTestResponse | None:
        source = self.store.get_source(source_id)
        if source is None:
            return None

        if source["type"] == "filesystem":
            config = decrypt_config(source["config"])
            filesystem_connector = FilesystemConnector(
                source_id=source_id,
                root_path=config.get("path", ""),
            )
            ok = await filesystem_connector.test_connection()
            message = "Connection ok" if ok else "Filesystem path is unavailable"
            self.audit.record(
                action="source.test",
                target_type="source",
                target_id=source_id,
                status="success" if ok else "failed",
                details={"type": source["type"]},
            )
            return SourceTestResponse(source_id=source_id, ok=ok, message=message)

        if source["type"] == "postgresql":
            postgres_connector = PostgresConnector(
                source_id=source_id,
                config=decrypt_config(source["config"]),
            )
            ok = await postgres_connector.test_connection()
            message = "Connection ok" if ok else "PostgreSQL connection is unavailable"
            self.audit.record(
                action="source.test",
                target_type="source",
                target_id=source_id,
                status="success" if ok else "failed",
                details={"type": source["type"]},
            )
            return SourceTestResponse(source_id=source_id, ok=ok, message=message)

        if source["type"] == "sqlite":
            sqlite_connector = SQLiteConnector(
                source_id=source_id,
                config=decrypt_config(source["config"]),
            )
            ok = await sqlite_connector.test_connection()
            message = "Connection ok" if ok else "SQLite database is unavailable"
            self.audit.record(
                action="source.test",
                target_type="source",
                target_id=source_id,
                status="success" if ok else "failed",
                details={"type": source["type"]},
            )
            return SourceTestResponse(source_id=source_id, ok=ok, message=message)

        self.audit.record(
            action="source.test",
            target_type="source",
            target_id=source_id,
            status="failed",
            details={"type": source["type"]},
        )
        return SourceTestResponse(
            source_id=source_id,
            ok=False,
            message=f"Connector '{source['type']}' is not implemented yet",
        )

    def delete_source(self, source_id: str) -> bool:
        deleted = self.store.delete_source(source_id)
        if deleted:
            self._vector_store().delete_chunks_for_source(source_id)
            self.audit.record(
                action="source.delete",
                target_type="source",
                target_id=source_id,
            )
        return deleted

    def _vector_store(self) -> VectorStore:
        if self.vector_store is None:
            self.vector_store = get_vector_store()
        return self.vector_store

    @staticmethod
    def _to_read_model(source: dict) -> SourceRead:
        return SourceRead(
            id=source["id"],
            name=source["name"],
            type=source["type"],
            enabled=source["enabled"],
            access_groups=source.get("access_groups", []),
            document_count=source.get("document_count", 0),
            last_indexed_at=source.get("last_indexed_at"),
        )
