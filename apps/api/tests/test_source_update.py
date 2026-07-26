from fastapi.testclient import TestClient


def test_source_can_be_disabled_and_reenabled(client: TestClient, tmp_path) -> None:
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

    disabled_response = client.patch(f"/api/v1/sources/{source_id}", json={"enabled": False})
    failed_job_response = client.post(
        "/api/v1/indexing/jobs",
        json={"source_id": source_id, "mode": "full"},
    )
    enabled_response = client.patch(f"/api/v1/sources/{source_id}", json={"enabled": True})

    assert disabled_response.status_code == 200
    assert disabled_response.json()["enabled"] is False
    assert failed_job_response.status_code == 202
    assert failed_job_response.json()["status"] == "failed"
    assert failed_job_response.json()["error"] == "Source is disabled"
    assert enabled_response.json()["enabled"] is True


def test_disabled_source_is_excluded_from_answers_and_evidence(client: TestClient, tmp_path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "policy.md").write_text(
        "Код запуска проекта ALPHA-7788.",
        encoding="utf-8",
    )
    source_response = client.post(
        "/api/v1/sources",
        json={
            "name": "Policy",
            "type": "filesystem",
            "config": {"path": str(wiki_dir)},
        },
    )
    source_id = source_response.json()["id"]
    client.post("/api/v1/indexing/jobs", json={"source_id": source_id})
    before_disable = client.post(
        "/api/v1/ask",
        json={"question": "Какой код запуска проекта?"},
    ).json()
    chunk_id = before_disable["citations"][0]["chunk_id"]

    client.patch(f"/api/v1/sources/{source_id}", json={"enabled": False})

    after_disable = client.post(
        "/api/v1/ask",
        json={"question": "Какой код запуска проекта?"},
    )
    evidence_response = client.get(f"/api/v1/chunks/{chunk_id}")

    assert after_disable.json()["status"] == "insufficient_context"
    assert evidence_response.status_code == 404
