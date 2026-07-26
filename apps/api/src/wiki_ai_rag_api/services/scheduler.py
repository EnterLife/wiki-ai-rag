from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.indexing import IndexingService
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.factory import get_metadata_store


class IndexingScheduler:
    def __init__(self, store: MetadataStore | None = None) -> None:
        settings = get_settings()
        self.store = store or get_metadata_store()
        self.poll_seconds = settings.scheduler_poll_seconds
        self.scheduler: Any = None

    def start(self) -> None:
        from apscheduler.schedulers.background import BackgroundScheduler

        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.scheduler.add_job(
            self.run_due_sources,
            "interval",
            seconds=self.poll_seconds,
            id="wiki-ai-rag-indexing-scheduler",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()
        self.run_due_sources()

    def shutdown(self) -> None:
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)

    def run_due_sources(self) -> None:
        now = datetime.now(UTC)
        for source in self.store.list_sources():
            if not should_index_source(source, now):
                continue
            asyncio.run(IndexingService(store=self.store).create_job(source_id=source["id"], mode="full"))


def should_index_source(source: dict[str, Any], now: datetime) -> bool:
    if not source.get("enabled", True):
        return False

    schedule = source.get("schedule") or {}
    if schedule.get("mode") != "scheduled":
        return False

    interval_hours = schedule.get("interval_hours")
    if not interval_hours:
        return False

    last_indexed_at = source.get("last_indexed_at")
    if not last_indexed_at:
        return True

    last_indexed = _parse_datetime(last_indexed_at)
    return now - last_indexed >= timedelta(hours=int(interval_hours))


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
