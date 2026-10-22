from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.schemas import CareDocument
from app.services import extraction
from app.services.provider_guard import provider_auth, provider_circuit

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state(monkeypatch) -> None:
    provider_auth.reset()
    provider_circuit.reset()
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "anthropic_api_key", "synthetic-test-key")
    monkeypatch.setattr(settings, "anthropic_api_key_expires_on", "")
    yield
    provider_auth.reset()
    provider_circuit.reset()


def in_days(days: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days)).isoformat()


def test_ready_when_key_is_healthy_and_not_near_expiry(monkeypatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key_expires_on", in_days(90))
    body = client.get("/api/readiness").json()
    assert body["status"] == "ready"
    assert body["key_expires_in_days"] == 90
    assert body["warnings"] == []


def test_expiry_within_two_weeks_warns_but_stays_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key_expires_on", in_days(5))
    response = client.get("/api/readiness")
    assert response.status_code == 200
    assert "expires in 5 day(s)" in response.json()["warnings"][0]


def test_expired_key_makes_readiness_degraded(monkeypatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key_expires_on", in_days(-1))
    response = client.get("/api/readiness")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert "passed its configured expiry" in response.json()["warnings"][0]


def test_malformed_expiry_date_is_ignored(monkeypatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key_expires_on", "next tuesday")
    body = client.get("/api/readiness").json()
    assert body["status"] == "ready"
    assert body["key_expires_in_days"] is None


class _Client:
    def __init__(self, status: int) -> None:
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, *_args, **_kwargs):
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        return httpx.Response(self.status, json={"error": "x"}, request=request)


def _document() -> CareDocument:
    return CareDocument(
        document_id="d1", document_type="note", document_date="2026-01-01", raw_text="text"
    )


@pytest.mark.parametrize("status", [401, 403])
def test_provider_rejecting_the_key_is_surfaced_by_readiness(monkeypatch, status) -> None:
    import asyncio

    monkeypatch.setattr(extraction.httpx, "AsyncClient", lambda **_k: _Client(status))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(extraction._call_anthropic(_document()))
    response = client.get("/api/readiness")
    assert response.status_code == 503
    assert response.json()["provider_auth"] == "failed"
    assert "rejected the configured API key" in response.json()["warnings"][0]


def test_other_provider_errors_do_not_look_like_a_bad_key(monkeypatch) -> None:
    import asyncio

    monkeypatch.setattr(extraction.httpx, "AsyncClient", lambda **_k: _Client(529))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(extraction._call_anthropic(_document()))
    assert provider_auth.state == "unknown"
