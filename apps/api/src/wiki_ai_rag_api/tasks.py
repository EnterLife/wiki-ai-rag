import asyncio

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.indexing import IndexingService


def _create_celery_app():
    from celery import Celery

    settings = get_settings()
    return Celery(
        "wiki_ai_rag",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )


celery_app = _create_celery_app()


@celery_app.task(name="wiki_ai_rag.run_indexing_job")
def run_indexing_job(job_id: str) -> None:
    asyncio.run(IndexingService().run_job(job_id))
