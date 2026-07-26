import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.indexing import IndexingService


class FailingEmbeddingProvider:
    dimension = 256

    def embed(self, text: str) -> list[float]:
        raise AssertionError("unchanged chunks must reuse their existing embeddings")


def _create_indexed_source(client: TestClient, tmp_path: Path) -> str:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "policy.md").write_text(
        "VPN policy requires certificate authentication.",
        encoding="utf-8",
    )
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Policy",
            "type": "filesystem",
            "config": {"path": str(wiki_dir)},
        },
    ).json()
    client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source["id"], "mode": "full"},
    )
    return source["id"]


def test_incremental_indexing_reuses_unchanged_embeddings(
    client: TestClient,
    tmp_path: Path,
) -> None:
    source_id = _create_indexed_source(client, tmp_path)
    before = client.post(
        "/api/v1/ask",
        json={"question": "What authentication does the VPN require?"},
    ).json()
    service = IndexingService()
    service.embeddings = FailingEmbeddingProvider()

    job = asyncio.run(service.create_job(source_id=source_id, mode="incremental"))
    after = client.post(
        "/api/v1/ask",
        json={"question": "What authentication does the VPN require?"},
    ).json()

    assert job is not None and job.status == "completed"
    assert before["citations"][0]["chunk_id"] == after["citations"][0]["chunk_id"]


def test_celery_mode_queues_job_without_running_it_inline(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id = _create_indexed_source(client, tmp_path)
    dispatched: list[str] = []
    monkeypatch.setenv("INDEXING_EXECUTION_MODE", "celery")
    get_settings.cache_clear()
    monkeypatch.setattr(
        IndexingService,
        "_dispatch_job",
        staticmethod(dispatched.append),
    )

    response = client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source_id, "mode": "incremental"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert dispatched == [response.json()["job_id"]]
    get_settings.cache_clear()


def test_celery_dispatch_failure_marks_job_failed(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id = _create_indexed_source(client, tmp_path)
    monkeypatch.setenv("INDEXING_EXECUTION_MODE", "celery")
    get_settings.cache_clear()

    def fail_dispatch(job_id: str) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(
        IndexingService,
        "_dispatch_job",
        staticmethod(fail_dispatch),
    )

    response = client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source_id, "mode": "incremental"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert "Could not dispatch" in response.json()["error"]
    get_settings.cache_clear()


def test_failed_document_keeps_previous_chunks(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id = _create_indexed_source(client, tmp_path)
    before = client.post(
        "/api/v1/ask",
        json={"question": "What authentication does the VPN require?"},
    ).json()

    def fail_parser(path: Path):
        raise ValueError(f"cannot parse {path.name}")

    monkeypatch.setattr(
        "wiki_ai_rag_api.services.indexing.parse_file_segments",
        fail_parser,
    )
    indexing_response = client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source_id, "mode": "full"},
    )
    after = client.post(
        "/api/v1/ask",
        json={"question": "What authentication does the VPN require?"},
    ).json()

    assert indexing_response.status_code == 202
    assert indexing_response.json()["status"] == "completed_with_errors"
    assert indexing_response.json()["failed_documents"] == 1
    assert after["status"] == "answered"
    assert before["citations"][0]["chunk_id"] == after["citations"][0]["chunk_id"]
