from typing import Any, Protocol


class MetadataStore(Protocol):
    def list_sources(self) -> list[dict[str, Any]]: ...

    def get_source(self, source_id: str) -> dict[str, Any] | None: ...

    def save_source(self, source: dict[str, Any]) -> dict[str, Any]: ...

    def update_source(
        self,
        source_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None: ...

    def delete_source(self, source_id: str) -> bool: ...

    def save_job(self, job: dict[str, Any]) -> dict[str, Any]: ...

    def get_job(self, job_id: str) -> dict[str, Any] | None: ...

    def list_jobs(
        self,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def update_job(
        self,
        job_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None: ...

    def append_audit_event(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]: ...
