from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine, delete, select, update
from sqlalchemy.engine import Engine, URL


class PostgresMetadataStore:
    def __init__(self, database_url: str | URL, engine: Engine | None = None) -> None:
        self.engine = engine or create_engine(database_url, pool_pre_ping=True)
        self.metadata = MetaData()
        self.sources = Table(
            "rag_sources",
            self.metadata,
            Column("id", String(64), primary_key=True),
            Column("payload", JSON, nullable=False),
        )
        self.jobs = Table(
            "rag_indexing_jobs",
            self.metadata,
            Column("job_id", String(64), primary_key=True),
            Column("source_id", String(64), nullable=False, index=True),
            Column("started_at", String(64), nullable=False, index=True),
            Column("payload", JSON, nullable=False),
        )
        self.audit_events = Table(
            "rag_audit_events",
            self.metadata,
            Column("id", String(64), primary_key=True),
            Column("created_at", String(64), nullable=False, index=True),
            Column("payload", JSON, nullable=False),
        )
        self.metadata.create_all(self.engine)

    def list_sources(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(self.sources.c.payload).order_by(self.sources.c.id))
            return [deepcopy(row.payload) for row in rows]

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            payload = connection.execute(
                select(self.sources.c.payload).where(self.sources.c.id == source_id)
            ).scalar_one_or_none()
            return deepcopy(payload) if payload is not None else None

    def save_source(self, source: dict[str, Any]) -> dict[str, Any]:
        with self.engine.begin() as connection:
            connection.execute(
                self.sources.insert().values(id=source["id"], payload=deepcopy(source))
            )
        return deepcopy(source)

    def update_source(
        self,
        source_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        with self.engine.begin() as connection:
            source = connection.execute(
                select(self.sources.c.payload)
                .where(self.sources.c.id == source_id)
                .with_for_update()
            ).scalar_one_or_none()
            if source is None:
                return None
            source = deepcopy(source)
            source.update(updates)
            connection.execute(
                update(self.sources)
                .where(self.sources.c.id == source_id)
                .values(payload=deepcopy(source))
            )
        return deepcopy(source)

    def delete_source(self, source_id: str) -> bool:
        with self.engine.begin() as connection:
            result = connection.execute(delete(self.sources).where(self.sources.c.id == source_id))
        return bool(result.rowcount)

    def save_job(self, job: dict[str, Any]) -> dict[str, Any]:
        with self.engine.begin() as connection:
            connection.execute(
                self.jobs.insert().values(
                    job_id=job["job_id"],
                    source_id=job["source_id"],
                    started_at=job["started_at"],
                    payload=deepcopy(job),
                )
            )
        return deepcopy(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            payload = connection.execute(
                select(self.jobs.c.payload).where(self.jobs.c.job_id == job_id)
            ).scalar_one_or_none()
            return deepcopy(payload) if payload is not None else None

    def list_jobs(
        self,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        statement = select(self.jobs.c.payload).order_by(self.jobs.c.started_at.desc()).limit(limit)
        if source_id:
            statement = statement.where(self.jobs.c.source_id == source_id)
        with self.engine.connect() as connection:
            rows = list(connection.execute(statement))
        rows.reverse()
        return [deepcopy(row.payload) for row in rows]

    def update_job(
        self,
        job_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        with self.engine.begin() as connection:
            job = connection.execute(
                select(self.jobs.c.payload)
                .where(self.jobs.c.job_id == job_id)
                .with_for_update()
            ).scalar_one_or_none()
            if job is None:
                return None
            job = deepcopy(job)
            job.update(updates)
            connection.execute(
                update(self.jobs)
                .where(self.jobs.c.job_id == job_id)
                .values(payload=deepcopy(job))
            )
        return deepcopy(job)

    def append_audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        with self.engine.begin() as connection:
            connection.execute(
                self.audit_events.insert().values(
                    id=event["id"],
                    created_at=event["created_at"],
                    payload=deepcopy(event),
                )
            )
        return deepcopy(event)

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        statement = (
            select(self.audit_events.c.payload)
            .order_by(self.audit_events.c.created_at.desc())
            .limit(limit)
        )
        with self.engine.connect() as connection:
            rows = list(connection.execute(statement))
        rows.reverse()
        return [deepcopy(row.payload) for row in rows]
