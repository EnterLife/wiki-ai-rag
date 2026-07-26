from fastapi.testclient import TestClient


def test_source_rejects_missing_connector_config(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "name": "Broken",
            "type": "filesystem",
            "config": {},
        },
    )

    assert response.status_code == 422


def test_source_rejects_scheduled_mode_without_interval(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "name": "Broken",
            "type": "filesystem",
            "config": {"path": "/data"},
            "schedule": {"mode": "scheduled"},
        },
    )

    assert response.status_code == 422
