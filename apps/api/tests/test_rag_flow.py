from pathlib import Path

from fastapi.testclient import TestClient


def test_filesystem_source_can_be_indexed_and_queried(client: TestClient, tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "product.md").write_text(
        "# Product X\n\nProduct X supports PostgreSQL and filesystem imports.",
        encoding="utf-8",
    )

    source_response = client.post(
        "/api/v1/sources",
        json={
            "name": "Local Wiki",
            "type": "filesystem",
            "config": {"path": str(wiki_dir)},
            "enabled": True,
            "schedule": {"mode": "manual"},
        },
    )
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    test_response = client.post(f"/api/v1/sources/{source_id}/test")
    assert test_response.status_code == 200
    assert test_response.json()["ok"] is True

    indexing_response = client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source_id, "mode": "full"},
    )
    assert indexing_response.status_code == 202
    assert indexing_response.json()["status"] == "completed"
    assert indexing_response.json()["processed_documents"] == 1

    jobs_response = client.get("/api/v1/indexing/jobs")
    assert jobs_response.status_code == 200
    assert jobs_response.json()[0]["job_id"] == indexing_response.json()["job_id"]

    ask_response = client.post(
        "/api/v1/ask",
        json={"question": "Какие импорты поддерживает Product X?", "top_k": 3},
    )
    assert ask_response.status_code == 200
    payload = ask_response.json()
    assert payload["status"] == "answered"
    assert payload["citations"][0]["source_id"] == source_id
    assert payload["citations"][0]["chunk_id"].startswith("chk_")
    assert payload["citations"][0]["document_id"] == "product.md"
    assert "PostgreSQL" in payload["citations"][0]["quote"]

    chunk_response = client.get(f"/api/v1/chunks/{payload['citations'][0]['chunk_id']}")
    assert chunk_response.status_code == 200
    assert chunk_response.json()["document_id"] == "product.md"
    assert "PostgreSQL" in chunk_response.json()["text"]

    sources_response = client.get("/api/v1/sources")
    assert sources_response.status_code == 200
    assert sources_response.json()[0]["document_count"] == 1


def test_ask_refuses_when_no_context_matches(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"question": "Что известно о несуществующем регламенте?", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "В базе знаний нет достаточной информации для ответа на этот вопрос.",
        "citations": [],
        "status": "insufficient_context",
    }


def test_filesystem_indexing_continues_when_one_document_fails(
    client: TestClient,
    tmp_path: Path,
) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "good.md").write_text("Product X supports filesystem imports.", encoding="utf-8")
    (wiki_dir / "broken.pdf").write_bytes(b"not a real pdf")

    source_response = client.post(
        "/api/v1/sources",
        json={
            "name": "Local Wiki",
            "type": "filesystem",
            "config": {"path": str(wiki_dir)},
            "enabled": True,
            "schedule": {"mode": "manual"},
        },
    )
    source_id = source_response.json()["id"]

    indexing_response = client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source_id, "mode": "full"},
    )

    assert indexing_response.status_code == 202
    payload = indexing_response.json()
    assert payload["status"] == "completed"
    assert payload["processed_documents"] == 1
    assert payload["failed_documents"] == 1
    assert "broken.pdf" in payload["error"]

    ask_response = client.post(
        "/api/v1/ask",
        json={"question": "Что поддерживает Product X?", "top_k": 3},
    )
    assert ask_response.json()["status"] == "answered"


def test_ask_can_be_filtered_by_source_ids(client: TestClient, tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    (first_dir / "product.md").write_text("Product X supports filesystem imports.", encoding="utf-8")
    (second_dir / "product.md").write_text("Product X supports PostgreSQL imports.", encoding="utf-8")

    source_ids: list[str] = []
    for name, path in [("Filesystem Wiki", first_dir), ("Database Wiki", second_dir)]:
        source_response = client.post(
            "/api/v1/sources",
            json={
                "name": name,
                "type": "filesystem",
                "config": {"path": str(path)},
                "enabled": True,
                "schedule": {"mode": "manual"},
            },
        )
        source_id = source_response.json()["id"]
        source_ids.append(source_id)
        client.post("/api/v1/indexing/jobs", json={"source_id": source_id, "mode": "full"})

    ask_response = client.post(
        "/api/v1/ask",
        json={
            "question": "Что поддерживает Product X?",
            "source_ids": [source_ids[1]],
            "top_k": 3,
        },
    )

    assert ask_response.status_code == 200
    payload = ask_response.json()
    assert payload["status"] == "answered"
    assert {citation["source_id"] for citation in payload["citations"]} == {source_ids[1]}
    assert "PostgreSQL" in payload["citations"][0]["quote"]
