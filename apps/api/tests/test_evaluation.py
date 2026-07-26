from pathlib import Path

from fastapi.testclient import TestClient

from wiki_ai_rag_api.schemas.evaluation import RetrievalEvaluationItem
from wiki_ai_rag_api.services.evaluation import _ndcg_at_k, _recall_at_k
from wiki_ai_rag_api.services.retrieval import RetrievedChunk


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


def test_retrieval_metrics_count_each_expected_document_once() -> None:
    item = RetrievalEvaluationItem(
        question="Question",
        expected_document_ids=["doc-a", "doc-b"],
    )
    chunks = [
        RetrievedChunk(
            chunk_id=f"chunk-{index}",
            document_id="doc-a",
            text="text",
            source_id="source",
            title="title",
            score=1,
            metadata={},
        )
        for index in range(3)
    ]

    assert _recall_at_k(item, chunks, 5) == 0.5
    assert 0 <= _ndcg_at_k(item, chunks, 10) <= 1
