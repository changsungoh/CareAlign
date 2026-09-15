import httpx
import pytest

from app.core.config import settings
from app.services.rxnorm import RxNormClient


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url: str) -> FakeResponse:
        if url.endswith("generic.json"):
            return FakeResponse({"minConceptGroup": {"minConcept": [{"rxcui": "860975"}]}})
        if url.endswith("properties.json"):
            return FakeResponse({"properties": {"name": "metoprolol succinate", "tty": "SCD"}})
        return FakeResponse({"idGroup": {"rxnormId": ["866429"]}})


@pytest.mark.asyncio
async def test_rxnorm_uses_generic_product_as_canonical(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rxnorm_enabled", True)
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    result = await RxNormClient().resolve("Toprol XL")
    assert result.normalized_id == "rxnorm:860975"
    assert result.rxcui == "866429"
    assert result.status == "resolved"


@pytest.mark.asyncio
async def test_rxnorm_disabled_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rxnorm_enabled", False)
    result = await RxNormClient().resolve("unknown")
    assert result.status == "disabled"
    assert result.normalized_id is None
