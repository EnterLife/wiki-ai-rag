from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from wiki_ai_rag_api.connectors.filesystem import FilesystemConnector
from wiki_ai_rag_api.connectors.postgres import PostgresConnector
from wiki_ai_rag_api.connectors.sqlite import SQLiteConnector
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.core.logging import log_event
from wiki_ai_rag_api.schemas.indexing import IndexingJobRead
from wiki_ai_rag_api.services.audit import AuditService
from wiki_ai_rag_api.services.chunking import TextChunk, chunk_document
from wiki_ai_rag_api.services.embeddings import EmbeddingProvider, get_embedding_provider
from wiki_ai_rag_api.services.metrics import metrics_registry
from wiki_ai_rag_api.services.parsing import parse_file_segments
from wiki_ai_rag_api.services.secrets import decrypt_config
from wiki_ai_rag_api.services.vector_store import VectorStore, get_vector_store
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.factory import get_metadata_store

logger = logging.getLogger("wiki_ai_rag_api.indexing")


@dataclass
class IndexingRunResult:
    chunks: list[TextChunk] = field(default_factory=list)
    processed_documents: int = 0
    failed_documents: int = 0
    failed_document_ids: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 1800
    overlap_chars: int = 220


class IndexingService:
    def __init__(
        self,
        store: MetadataStore | None = None,
        vector_store: VectorStore | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.store = store or get_metadata_store()
        self.embeddings: EmbeddingProvider = get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()
        self.audit = audit or AuditService(self.store)

    async def create_job(self, source_id: str, mode: str = "full") -> IndexingJobRead | None:
        source = self.store.get_source(source_id)
        if source is None:
            return None
        if not source.get("enabled", True):
            now = datetime.now(UTC).isoformat()
            job: dict = {
                "job_id": f"job_{uuid4().hex[:12]}",
                "source_id": source_id,
                "mode": mode,
                "status": "failed",
                "processed_documents": 0,
                "failed_documents": 0,
                "started_at": now,
                "finished_at": now,
                "error": "Source is disabled",
            }
            self.store.save_job(job)
            log_event(
                logger,
                "indexing.job.failed",
                job_id=job["job_id"],
                source_id=source_id,
                mode=mode,
                reason="source_disabled",
            )
            self.audit.record(
                action="indexing.run",
                target_type="source",
                target_id=source_id,
                status="failed",
                details={"job_id": job["job_id"], "mode": mode, "error": "Source is disabled"},
            )
            metrics_registry.increment("indexing.failed")
            return self._to_read_model(job)

        now = datetime.now(UTC).isoformat()
        execution_mode = get_settings().indexing_execution_mode
        job = {
            "job_id": f"job_{uuid4().hex[:12]}",
            "source_id": source_id,
            "mode": mode,
            "status": "queued" if execution_mode == "celery" else "running",
            "processed_documents": 0,
            "failed_documents": 0,
            "started_at": now,
            "finished_at": None,
            "error": None,
        }
        self.store.save_job(job)
        if execution_mode == "celery":
            try:
                self._dispatch_job(job["job_id"])
                return self._to_read_model(job)
            except Exception as exc:
                failed_job = self.store.update_job(
                    job["job_id"],
                    {
                        "status": "failed",
                        "finished_at": datetime.now(UTC).isoformat(),
                        "error": f"Could not dispatch indexing job: {exc}",
                    },
                )
                metrics_registry.increment("indexing.failed")
                return self._to_read_model(failed_job or job)
        return await self._run_job(job=job, source=source)

    async def run_job(self, job_id: str) -> IndexingJobRead | None:
        job = self.store.get_job(job_id)
        if job is None:
            return None
        source = self.store.get_source(job["source_id"])
        if source is None or not source.get("enabled", True):
            error = "Source not found" if source is None else "Source is disabled"
            updated_job = self.store.update_job(
                job_id,
                {
                    "status": "failed",
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": error,
                },
            )
            return self._to_read_model(updated_job or job)
        job = self.store.update_job(job_id, {"status": "running"}) or job
        return await self._run_job(job=job, source=source)

    async def _run_job(self, *, job: dict, source: dict) -> IndexingJobRead:
        source_id = source["id"]
        mode = job.get("mode", "full")
        log_event(
            logger,
            "indexing.job.started",
            job_id=job["job_id"],
            source_id=source_id,
            source_type=source["type"],
            mode=mode,
        )

        try:
            with metrics_registry.time_block("indexing.run_ms"):
                result = await self._index_source(source)
            finished_at = datetime.now(UTC).isoformat()
            existing_records = (
                self.vector_store.list_chunk_records_for_source(source_id)
                if mode == "incremental" or result.failed_document_ids
                else []
            )
            existing_embeddings = (
                {
                    record["hash"]: record.get("embedding", [])
                    for record in existing_records
                    if record.get("hash")
                }
                if mode == "incremental"
                else {}
            )
            next_records = [
                self._chunk_to_dict(
                    chunk,
                    existing_embeddings=existing_embeddings,
                )
                for chunk in result.chunks
            ]
            next_records.extend(
                record
                for record in existing_records
                if record.get("document_id") in result.failed_document_ids
            )
            self.vector_store.replace_chunks_for_source(
                source_id,
                next_records,
            )
            self.store.update_source(
                source_id,
                {
                    "document_count": result.processed_documents,
                    "last_indexed_at": finished_at,
                    "updated_at": finished_at,
                },
            )
            updated_job = self.store.update_job(
                job["job_id"],
                {
                    "status": (
                        "completed_with_errors"
                        if result.failed_documents
                        else "completed"
                    ),
                    "processed_documents": result.processed_documents,
                    "failed_documents": result.failed_documents,
                    "finished_at": finished_at,
                    "error": "; ".join(result.errors) if result.errors else None,
                },
            )
            self.audit.record(
                action="indexing.run",
                target_type="source",
                target_id=source_id,
                details={
                    "job_id": job["job_id"],
                    "mode": mode,
                    "processed_documents": result.processed_documents,
                    "failed_documents": result.failed_documents,
                },
            )
            metrics_registry.increment("indexing.completed")
            log_event(
                logger,
                "indexing.job.completed",
                job_id=job["job_id"],
                source_id=source_id,
                mode=mode,
                processed_documents=result.processed_documents,
                failed_documents=result.failed_documents,
                chunks_count=len(result.chunks),
            )
            return self._to_read_model(updated_job or job)

        except Exception as exc:
            updated_job = self.store.update_job(
                job["job_id"],
                {
                    "status": "failed",
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": str(exc),
                },
            )
            self.audit.record(
                action="indexing.run",
                target_type="source",
                target_id=source_id,
                status="failed",
                details={"job_id": job["job_id"], "mode": mode, "error": str(exc)},
            )
            metrics_registry.increment("indexing.failed")
            log_event(
                logger,
                "indexing.job.failed",
                job_id=job["job_id"],
                source_id=source_id,
                mode=mode,
                reason=str(exc),
            )
            return self._to_read_model(updated_job or job)

    @staticmethod
    def _dispatch_job(job_id: str) -> None:
        from wiki_ai_rag_api.tasks import run_indexing_job

        run_indexing_job.delay(job_id)

    def get_job(self, job_id: str) -> IndexingJobRead | None:
        job = self.store.get_job(job_id)
        if job is None:
            return None
        return self._to_read_model(job)

    def list_jobs(self, source_id: str | None = None, limit: int = 100) -> list[IndexingJobRead]:
        return [
            self._to_read_model(job)
            for job in self.store.list_jobs(source_id=source_id, limit=limit)
        ]

    async def _index_source(self, source: dict) -> IndexingRunResult:
        source = {**source, "config": decrypt_config(source["config"])}
        if source["type"] == "filesystem":
            return await self._index_filesystem_source(source)
        if source["type"] == "postgresql":
            return await self._index_postgres_source(source)
        if source["type"] == "sqlite":
            return await self._index_sqlite_source(source)
        raise ValueError(f"Indexing for source type '{source['type']}' is not implemented yet")

    async def _index_filesystem_source(self, source: dict) -> IndexingRunResult:
        connector = FilesystemConnector(source_id=source["id"], root_path=source["config"].get("path", ""))
        if not await connector.test_connection():
            raise ValueError("Filesystem path is unavailable")

        result = IndexingRunResult()
        chunking_config = _chunking_config(source)
        async for document in connector.iter_documents():
            try:
                path = Path(document.metadata["path"])
                citation_metadata = {
                    key: value
                    for key, value in document.metadata.items()
                    if key != "path"
                }
                document_chunks: list[TextChunk] = []
                for segment in parse_file_segments(path):
                    document_chunks.extend(
                        chunk_document(
                            document_id=document.id,
                            source_id=document.source_id,
                            title=document.title,
                            text=segment.text,
                            metadata={**citation_metadata, **segment.metadata},
                            max_chars=chunking_config.max_chars,
                            overlap_chars=chunking_config.overlap_chars,
                        )
                    )
                result.chunks.extend(document_chunks)
                result.processed_documents += 1
            except Exception as exc:
                result.failed_documents += 1
                result.failed_document_ids.add(document.id)
                result.errors.append(f"{document.id}: {exc}")
        return result

    async def _index_postgres_source(self, source: dict) -> IndexingRunResult:
        connector = PostgresConnector(source_id=source["id"], config=source["config"])
        if not await connector.test_connection():
            raise ValueError("PostgreSQL connection is unavailable")

        result = IndexingRunResult()
        chunking_config = _chunking_config(source)
        async for document in connector.iter_documents():
            try:
                chunks = chunk_document(
                    document_id=document.id,
                    source_id=document.source_id,
                    title=document.title,
                    text=document.body,
                    metadata=document.metadata,
                    max_chars=chunking_config.max_chars,
                    overlap_chars=chunking_config.overlap_chars,
                )
                result.chunks.extend(chunks)
                result.processed_documents += 1
            except Exception as exc:
                result.failed_documents += 1
                result.failed_document_ids.add(document.id)
                result.errors.append(f"{document.id}: {exc}")
        return result

    async def _index_sqlite_source(self, source: dict) -> IndexingRunResult:
        connector = SQLiteConnector(source_id=source["id"], config=source["config"])
        if not await connector.test_connection():
            raise ValueError("SQLite database is unavailable")

        result = IndexingRunResult()
        chunking_config = _chunking_config(source)
        async for document in connector.iter_documents():
            try:
                chunks = chunk_document(
                    document_id=document.id,
                    source_id=document.source_id,
                    title=document.title,
                    text=document.body,
                    metadata=document.metadata,
                    max_chars=chunking_config.max_chars,
                    overlap_chars=chunking_config.overlap_chars,
                )
                result.chunks.extend(chunks)
                result.processed_documents += 1
            except Exception as exc:
                result.failed_documents += 1
                result.failed_document_ids.add(document.id)
                result.errors.append(f"{document.id}: {exc}")
        return result

    def _chunk_to_dict(
        self,
        chunk: TextChunk,
        *,
        existing_embeddings: dict[str, list[float]] | None = None,
    ) -> dict:
        embedding = (existing_embeddings or {}).get(chunk.hash)
        return {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "source_id": chunk.source_id,
            "title": chunk.title,
            "text": chunk.text,
            "embedding": embedding or self.embeddings.embed(chunk.text),
            "metadata": chunk.metadata,
            "hash": chunk.hash,
        }

    @staticmethod
    def _to_read_model(job: dict) -> IndexingJobRead:
        return IndexingJobRead(
            job_id=job["job_id"],
            source_id=job["source_id"],
            status=job["status"],
            processed_documents=job["processed_documents"],
            failed_documents=job["failed_documents"],
            started_at=job["started_at"],
            finished_at=job["finished_at"],
            error=job["error"],
        )


def _chunking_config(source: dict) -> ChunkingConfig:
    config = source.get("config", {})
    indexing_config = config.get("indexing", {}) if isinstance(config, dict) else {}
    max_chars = int(indexing_config.get("max_chars", ChunkingConfig.max_chars))
    overlap_chars = int(indexing_config.get("overlap_chars", ChunkingConfig.overlap_chars))
    if max_chars < 200:
        raise ValueError("indexing.max_chars must be at least 200")
    if overlap_chars < 0:
        raise ValueError("indexing.overlap_chars must be non-negative")
    if overlap_chars >= max_chars:
        raise ValueError("indexing.overlap_chars must be smaller than indexing.max_chars")
    return ChunkingConfig(max_chars=max_chars, overlap_chars=overlap_chars)
