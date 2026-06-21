from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from wiki_ai_rag_api.services.metrics import metrics_registry


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        metrics_registry.increment(f"api.http_error.{exc.status_code}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        metrics_registry.increment("api.validation_error")
        return JSONResponse(
            status_code=422,
            content={"status": "error", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        metrics_registry.increment("api.internal_error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "detail": "Internal server error"},
        )
