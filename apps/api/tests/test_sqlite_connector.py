import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from wiki_ai_rag_api.connectors.sqlite import build_select_query


def test_sqlite_build_select_query_quotes_identifiers() -> None:
    query = build_select_query(
        {
            "name": "pages",
            "id_field": "id",
            "title_field": "title",
            "text_fields": ["body"],
            "metadata_fields": ["url"],
            "limit": 10,
        }
    )

    assert query == 'SELECT "id" AS __id, "title" AS __title, "body", "url" FROM "pages" LIMIT 10'


def test_sqlite_source_can_be_indexed_and_queried(client: TestClient, tmp_path: Path) -> None:
    database_path = tmp_path / "knowledge.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE pages (id integer primary key, title text, body text, url text)")
        connection.execute(
            "INSERT INTO pages (id, title, body, url) VALUES (?, ?, ?, ?)",
            (
                1,
                "Product X",
                "Product X supports SQLite imports.",
                "https://wiki.example/product-x",
            ),
        )

    source_response = client.post(
        "/api/v1/sources",
        json={
            "name": "SQLite Wiki",
            "type": "sqlite",
            "config": {
                "database_path": str(database_path),
                "tables": [
                    {
                        "name": "pages",
                        "id_field": "id",
                        "title_field": "title",
                        "text_fields": ["body"],
                        "metadata_fields": ["url"],
                    }
                ],
            },
            "enabled": True,
            "schedule": {"mode": "manual"},
        },
    )
    source_id = source_response.json()["id"]

    test_response = client.post(f"/api/v1/sources/{source_id}/test")
    indexing_response = client.post("/api/v1/indexing/jobs", json={"source_id": source_id, "mode": "full"})
    ask_response = client.post("/api/v1/ask", json={"question": "Что поддерживает Product X?"})

    assert test_response.status_code == 200
    assert test_response.json()["ok"] is True
    assert indexing_response.json()["status"] == "completed"
    assert indexing_response.json()["processed_documents"] == 1
    assert ask_response.json()["status"] == "answered"
    assert "SQLite" in ask_response.json()["citations"][0]["quote"]

