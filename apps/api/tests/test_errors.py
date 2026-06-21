from fastapi.testclient import TestClient


def test_http_errors_use_json_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/indexing/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"status": "error", "detail": "Job not found"}


def test_validation_errors_use_json_error_shape(client: TestClient) -> None:
    response = client.post("/api/v1/ask", json={"question": "", "top_k": 0})

    assert response.status_code == 422
    assert response.json()["status"] == "error"
    assert isinstance(response.json()["detail"], list)

