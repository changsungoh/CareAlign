import asyncio

from app.core.config import settings
from app.models.schemas import CareDocument
from app.services import extraction


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "stop_reason": "end_turn",
            "content": [{"text": '{"instructions": []}'}],
            "usage": {"input_tokens": 123, "output_tokens": 45},
        }


class FakeClient:
    def __init__(self) -> None:
        self.headers: dict[str, str] | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, *_args, **_kwargs) -> FakeResponse:
        self.headers = _kwargs["headers"]
        return FakeResponse()


def test_live_provider_usage_is_exposed_to_evaluator(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(
        settings,
        "anthropic_api_key",
        "  ANTHROPIC_API_KEY='synthetic-\r\ntest-key'  ",
    )
    monkeypatch.setattr(extraction.httpx, "AsyncClient", lambda **_kwargs: client)
    captured: list[dict] = []
    document = CareDocument(
        document_id="synthetic",
        document_type="test",
        document_date="2026-09-15",
        raw_text="No medication is present.",
    )
    result = asyncio.run(extraction._call_anthropic(document, captured.append))
    assert result == []
    assert captured == [{"input_tokens": 123, "output_tokens": 45}]
    assert client.headers is not None
    assert client.headers["x-api-key"] == "synthetic-test-key"
