from pathlib import Path

from fastapi.testclient import TestClient


def test_retrieval_evaluation_reports_recall_and_mrr(
    client: TestClient,
    tmp_path: Path,
) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "vpn.md").write_text("OpenVPN setup uses certificate authentication.", encoding="utf-8")
    (wiki_dir / "hr.md").write_text("Vacation requests use the HR portal.", encoding="utf-8")

    source_response = client.post(
        "/api/v1/sources",
        json={
            "name": "Eval Wiki",
            "type": "filesystem",
            "config": {"path": str(wiki_dir)},
            "enabled": True,
            "schedule": {"mode": "manual"},
        },
    )
    source_id = source_response.json()["id"]
    client.post("/api/v1/indexing/jobs", json={"source_id": source_id, "mode": "full"})

    response = client.post(
        "/api/v1/evaluation/retrieval",
        json={
            "top_k": 10,
            "items": [
                {
                    "question": "How is OpenVPN setup authenticated?",
                    "expected_document_ids": ["vpn.md"],
                    "source_ids": [source_id],
                },
                {
                    "question": "Where are vacation requests created?",
                    "expected_document_ids": ["hr.md"],
                    "source_ids": [source_id],
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["cases"] == 2
    assert payload["metrics"]["recall_at_5"] == 1
    assert payload["metrics"]["recall_at_10"] == 1
    assert payload["metrics"]["mrr"] == 1
    assert payload["metrics"]["ndcg_at_10"] == 1
    assert all(result["found"] for result in payload["results"])


def test_retrieval_evaluation_reports_missing_expected_document(client: TestClient) -> None:
    response = client.post(
        "/api/v1/evaluation/retrieval",
        json={
            "items": [
                {
                    "question": "Unknown policy",
                    "expected_document_ids": ["missing.md"],
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["recall_at_5"] == 0
    assert payload["metrics"]["mrr"] == 0
    assert payload["results"][0]["found"] is False
