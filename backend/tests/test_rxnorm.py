from __future__ import annotations

from collections.abc import Callable

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
    responder: Callable[[str, dict | None], dict]
    calls: list[tuple[str, dict | None]]

    def __init__(self, *args, **kwargs) -> None:
        self.calls = FakeClient.calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url: str, params: dict | None = None) -> FakeResponse:
        self.calls.append((url, params))
        return FakeResponse(FakeClient.responder(url, params))


def install_fake(monkeypatch, responder: Callable[[str, dict | None], dict]) -> list:
    calls: list[tuple[str, dict | None]] = []
    FakeClient.responder = responder
    FakeClient.calls = calls
    monkeypatch.setattr(settings, "rxnorm_enabled", True)
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    return calls


def version_payload() -> dict:
    return {"version": {"version": "01-Sep-2026", "apiVersion": "3.1.0"}}


@pytest.mark.asyncio
async def test_exact_branded_product_uses_generic_product_as_canonical(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            assert params == {"name": "Toprol XL", "search": 0, "allsrc": 0}
            return {"idGroup": {"rxnormId": ["866429"]}}
        if url.endswith("/866429/properties.json"):
            return {"properties": {"name": "Toprol XL 25 MG", "tty": "SBD"}}
        if url.endswith("/866429/generic.json"):
            return {"minConceptGroup": {"minConcept": [{"rxcui": "860975"}]}}
        if url.endswith("/860975/properties.json"):
            return {"properties": {"name": "metoprolol succinate 25 MG", "tty": "SCD"}}
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve("Toprol XL")
    assert result.normalized_id == "rxnorm:860975"
    assert result.rxcui == "866429"
    assert result.canonical_rxcui == "860975"
    assert result.term_type == "SBD"
    assert result.canonical_term_type == "SCD"
    assert result.status == "resolved_exact_generic_product"
    assert result.dataset_version == "01-Sep-2026"


@pytest.mark.asyncio
async def test_exact_ingredient_does_not_call_generic_endpoint(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": ["6918"]}}
        if url.endswith("/6918/properties.json"):
            return {"properties": {"name": "metoprolol", "tty": "IN"}}
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    calls = install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve("metoprolol")
    assert result.normalized_id == "rxnorm:6918"
    assert result.status == "resolved_exact"
    assert not any(url.endswith("generic.json") for url, _ in calls)


@pytest.mark.asyncio
async def test_normalized_match_is_review_candidate_not_identity(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json") and params and params["search"] == 0:
            return {"idGroup": {}}
        if url.endswith("rxcui.json") and params and params["search"] == 1:
            return {"idGroup": {"rxnormId": ["6918"]}}
        if url.endswith("/6918/properties.json"):
            return {"properties": {"name": "metoprolol", "tty": "IN"}}
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve("metoprolol mystery form")
    assert result.normalized_id is None
    assert result.rxcui == "6918"
    assert result.match_strategy == "normalized"
    assert result.status == "normalized_candidate_needs_review"


@pytest.mark.asyncio
async def test_multiple_exact_matches_fail_closed(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        return {"idGroup": {"rxnormId": ["1", "2"]}}

    calls = install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve("ambiguous")
    assert result.normalized_id is None
    assert result.status == "ambiguous_exact"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_unsupported_component_term_type_is_not_identity(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": ["123"]}}
        if url.endswith("/123/properties.json"):
            return {"properties": {"name": "component only", "tty": "SCDC"}}
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve("component only")
    assert result.normalized_id is None
    assert result.status == "unsupported_term_type"


@pytest.mark.asyncio
async def test_version_is_cached_for_client_lifetime(monkeypatch) -> None:
    identifiers = iter(["1", "2"])

    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": [next(identifiers)]}}
        if url.endswith("/1/properties.json"):
            return {"properties": {"name": "first", "tty": "IN"}}
        if url.endswith("/2/properties.json"):
            return {"properties": {"name": "second", "tty": "PIN"}}
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    calls = install_fake(monkeypatch, responder)
    client = RxNormClient()
    await client.resolve("first")
    await client.resolve("second")
    assert sum(url.endswith("version.json") for url, _ in calls) == 1


@pytest.mark.asyncio
async def test_rxnorm_disabled_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rxnorm_enabled", False)
    result = await RxNormClient().resolve("unknown")
    assert result.status == "disabled"
    assert result.normalized_id is None
