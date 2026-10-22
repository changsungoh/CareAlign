import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import routes
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


@pytest.mark.parametrize(
    "provider_error",
    [
        httpx.TimeoutException("provider timed out"),
        json.JSONDecodeError("invalid provider JSON", "", 0),
        RuntimeError("provider refused structured output"),
    ],
)
def test_provider_failures_return_generic_unavailable(
    monkeypatch, provider_error: Exception
) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)

    async def fail_extraction(*_args, **_kwargs):
        raise provider_error

    monkeypatch.setattr(routes, "extract_document", fail_extraction)
    response = client.post("/api/analyze", json=DOCUMENTS)
    assert response.status_code == 503
    assert response.json()["detail"] == ("Analysis unavailable. No safety conclusion was produced.")
    assert str(provider_error) not in response.text


def test_malformed_provider_dose_degrades_one_instruction_not_the_analysis(monkeypatch) -> None:
    import asyncio

    from app.models.schemas import CareDocument, ValidationStatus
    from app.services import extraction

    text = "Take metformin 1/2 tablet twice a day"

    async def fake_provider(document, usage_callback=None):
        return [
            {
                "raw_name": "metformin",
                "dose": "1/2",
                "unit": "tablet",
                "pattern_type": "fixed",
                "times_per_day": 0,
                "interval_hours": None,
                "raw_frequency": "twice a day",
                "timing": [],
                "route": None,
                "duration": None,
                "action": None,
                "warning": None,
                "evidence_span": text,
            }
        ]

    monkeypatch.setattr(extraction, "_call_anthropic", fake_provider)
    document = CareDocument(
        document_id="d1", document_type="note", document_date="2026-01-01", raw_text=text
    )
    result = asyncio.run(extraction.extract_document(document, False))
    assert len(result) == 1
    assert result[0].validation_status == ValidationStatus.INSUFFICIENT_INFORMATION
    assert result[0].dose is None


def test_expired_api_key_is_reported_by_readiness(monkeypatch) -> None:
    from app.services import extraction
    from app.services.provider_guard import provider_auth

    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "anthropic_api_key", "synthetic-expired-key")

    class Rejected:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def post(self, *args, **kwargs):
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            return httpx.Response(401, request=request, json={"error": "invalid x-api-key"})

    monkeypatch.setattr(extraction.httpx, "AsyncClient", Rejected)
    assert client.get("/api/readiness").json()["provider_auth"] == "unknown"
    body = {
        "documents": [
            {"document_id": "a", "document_type": "n", "document_date": "2026-01-01",
             "raw_text": "Take lisinopril 10 mg once a day."},
            {"document_id": "b", "document_type": "n", "document_date": "2026-02-01",
             "raw_text": "Take lisinopril 10 mg once a day."},
        ]
    }  # fmt: skip
    assert client.post("/api/analyze", json=body).status_code == 503
    assert provider_auth.snapshot() == "failed"
    ready = client.get("/api/readiness")
    assert ready.status_code == 503
    assert ready.json()["provider_auth"] == "failed"
