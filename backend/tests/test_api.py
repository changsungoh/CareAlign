import json
import logging

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_valid_request_id_is_echoed() -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "judge-demo-001"})
    assert response.headers["X-Request-ID"] == "judge-demo-001"


def test_invalid_request_id_is_replaced() -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "contains spaces"})
    assert response.headers["X-Request-ID"] != "contains spaces"


def test_structured_request_log_excludes_query_values(caplog) -> None:
    caplog.set_level(logging.INFO, logger="carealign.operations")
    response = client.get(
        "/api/health?patient=synthetic-secret",
        headers={"X-Request-ID": "safe-correlation-id"},
    )
    assert response.status_code == 200
    records = [json.loads(record.message) for record in caplog.records]
    completed = next(item for item in records if item["event"] == "http_request_completed")
    assert completed["request_id"] == "safe-correlation-id"
    assert completed["path"] == "/api/health"
    assert "synthetic-secret" not in json.dumps(completed)


def test_readiness_is_explicit_when_provider_is_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    response = client.get("/api/readiness")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["provider_mode"] == "unconfigured"


def test_version_exposes_reproducibility_metadata() -> None:
    response = client.get("/api/version")
    body = response.json()
    assert response.status_code == 200
    assert body["app_version"] == "0.4.0"
    assert body["prompt_version"]
    assert body["rules_version"]
    assert body["terminology_policy_version"] == "rxnorm-policy-v2"
    assert body["dataset_version"]
    assert body["evaluated_at"]
    assert body["release_sha"]
    assert body["provider_mode"]
