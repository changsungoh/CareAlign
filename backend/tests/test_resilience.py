from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

DOCUMENTS = {
    "documents": [
        {
            "document_id": "a",
            "document_type": "synthetic",
            "document_date": "2026-08-01",
            "raw_text": "Continue lisinopril 10 mg once a day.",
        },
        {
            "document_id": "b",
            "document_type": "synthetic",
            "document_date": "2026-09-01",
            "raw_text": "Continue lisinopril 10 mg once a day.",
        },
    ]
}


def test_missing_provider_key_never_returns_no_conflict(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    response = client.post("/api/analyze", json=DOCUMENTS)
    assert response.status_code == 503
    assert response.json()["detail"] == "Analysis unavailable. No safety conclusion was produced."


def test_missing_extraction_is_insufficient_not_reassuring(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", True)
    payload = {"documents": [dict(item) for item in DOCUMENTS["documents"]]}
    payload["documents"][0]["raw_text"] = "No medication content is present."
    payload["documents"][1]["raw_text"] = "No medication content is present."
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_information"
    assert response.json()["conflicts"] == []


def test_unsupported_schedule_is_insufficient_not_completed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", True)
    payload = {"documents": [dict(item) for item in DOCUMENTS["documents"]]}
    payload["documents"][0]["raw_text"] = "Continue lisinopril 10 mg as needed."
    payload["documents"][1]["raw_text"] = "Continue lisinopril 10 mg as needed."
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_information"
