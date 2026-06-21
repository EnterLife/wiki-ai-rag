from pathlib import Path

from fastapi.testclient import TestClient


def test_metrics_endpoint_reports_ask_and_indexing_activity(
    client: TestClient,
    tmp_path: Path,
) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "product.md").write_text("Product X supports PostgreSQL imports.", encoding="utf-8")

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
    client.post("/api/v1/indexing/jobs", json={"source_id": source_id, "mode": "full"})
    client.post("/api/v1/ask", json={"question": "Что поддерживает Product X?"})

    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["counters"]["indexing.completed"] == 1
    assert payload["counters"]["ask.answered"] == 1
    assert payload["counters"]["retrieval.searches"] == 1
    assert payload["counters"]["retrieval.results"] >= 1
    assert payload["durations"]["indexing.run_ms"]["count"] == 1
    assert payload["durations"]["ask.retrieval_ms"]["count"] == 1
    assert payload["durations"]["ask.llm_ms"]["count"] == 1
