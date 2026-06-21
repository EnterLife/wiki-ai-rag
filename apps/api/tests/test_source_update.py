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

