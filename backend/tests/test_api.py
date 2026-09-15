from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_exposes_reproducibility_metadata() -> None:
    response = client.get("/api/version")
    body = response.json()
    assert response.status_code == 200
    assert body["app_version"] == "0.2.0"
    assert body["prompt_version"]
    assert body["rules_version"]
    assert body["dataset_version"]
    assert body["evaluated_at"]
