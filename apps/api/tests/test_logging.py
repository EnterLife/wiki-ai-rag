import hashlib
import json
import logging

import pytest

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.core.logging import JsonLogFormatter
from wiki_ai_rag_api.schemas.ask import AskRequest
from wiki_ai_rag_api.services.rag import RagService


class EmptyRetrieval:
    async def search(
        self,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
        access_context=None,
    ) -> list:
        return []


class UnusedLlm:
    pass


class CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_json_log_formatter_outputs_structured_event() -> None:
    record = logging.LogRecord(
        name="wiki_ai_rag_api.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="rag.answer.completed",
        args=(),
        exc_info=None,
    )
    record.event = "rag.answer.completed"
    record.source_ids = ["src_1"]

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "wiki_ai_rag_api.test"
    assert payload["message"] == "rag.answer.completed"
    assert payload["event"] == "rag.answer.completed"
    assert payload["source_ids"] == ["src_1"]


@pytest.mark.asyncio
async def test_rag_logs_question_hash_without_text_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_QUESTION_TEXT", raising=False)
    get_settings.cache_clear()
    logger = logging.getLogger("wiki_ai_rag_api.rag")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        question = "Какие импорты поддерживает Product X?"
        await RagService(retrieval=EmptyRetrieval(), llm=UnusedLlm()).answer(
            AskRequest(question=question)
        )
    finally:
        logger.removeHandler(handler)
        get_settings.cache_clear()

    received = next(record for record in handler.records if record.event == "rag.question.received")
    assert received.question_hash == hashlib.sha256(question.encode("utf-8")).hexdigest()
    assert received.question_length == len(question)
    assert "question" not in received.__dict__
