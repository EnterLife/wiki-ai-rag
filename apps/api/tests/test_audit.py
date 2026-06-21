from pathlib import Path

from fastapi.testclient import TestClient


def test_admin_actions_are_written_to_audit_log(client: TestClient, tmp_path: Path) -> None:
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

    client.patch(f"/api/v1/sources/{source_id}", json={"enabled": False})
    client.patch(f"/api/v1/sources/{source_id}", json={"enabled": True})
    client.post(f"/api/v1/sources/{source_id}/test")
    client.post("/api/v1/indexing/jobs", json={"source_id": source_id, "mode": "full"})
    client.delete(f"/api/v1/sources/{source_id}")

    audit_response = client.get("/api/v1/audit")

    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()]
    assert actions == [
        "source.create",
        "source.update",
        "source.update",
        "source.test",
        "indexing.run",
        "source.delete",
    ]
    assert all("password" not in str(event["details"]).lower() for event in audit_response.json())
