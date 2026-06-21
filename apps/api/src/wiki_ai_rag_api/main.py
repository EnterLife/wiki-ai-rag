from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wiki_ai_rag_api.api.errors import install_error_handlers
from wiki_ai_rag_api.api.router import api_router
from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.core.logging import configure_logging
from wiki_ai_rag_api.services.scheduler import IndexingScheduler


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    scheduler: IndexingScheduler | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal scheduler
        if settings.enable_scheduler:
            scheduler = IndexingScheduler()
            scheduler.start()
        yield
        if scheduler is not None:
            scheduler.shutdown()

    app = FastAPI(title="Wiki AI RAG API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")
    install_error_handlers(app)
    return app


app = create_app()
