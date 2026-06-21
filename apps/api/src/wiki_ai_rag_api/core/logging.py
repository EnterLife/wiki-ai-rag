from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from wiki_ai_rag_api.core.config import Settings

APP_LOGGER_NAME = "wiki_ai_rag_api"

_STANDARD_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_KEYS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(settings: Settings) -> None:
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False

    logger.handlers = [
        handler
        for handler in logger.handlers
        if not getattr(handler, "_wiki_ai_rag_json_handler", False)
    ]

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler._wiki_ai_rag_json_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    logger.info(event, extra={"event": event, **fields})
