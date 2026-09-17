from __future__ import annotations

from collections.abc import Callable
from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import settings
from app.models.schemas import CareDocument
from app.services import extraction
from app.services import rxnorm as rxnorm_module
from app.services.rxnorm import RxNormClient, RxNormResolution


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
    return {"version": "01-Sep-2026", "apiVersion": "3.1.0"}


def properties(name: str, tty: str, suppress: str = "N") -> dict:
    return {"properties": {"name": name, "tty": tty, "suppress": suppress}}


@pytest.mark.asyncio
async def test_exact_branded_product_uses_generic_product_as_canonical(monkeypatch) -> None:
    product_name = "Toprol XL 25 MG Extended Release Oral Tablet"

    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            assert params == {"name": product_name, "search": 0, "allsrc": 0}
            return {"idGroup": {"rxnormId": ["866429"]}}
        if url.endswith("/866429/properties.json"):
            return properties(product_name, "SBD")
        if url.endswith("/866429/generic.json"):
            return {"minConceptGroup": {"minConcept": [{"rxcui": "860975"}]}}
        if url.endswith("/860975/properties.json"):
            return properties("metoprolol succinate 25 MG Extended Release Oral Tablet", "SCD")
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve(product_name)
    assert result.normalized_id == "rxnorm:860975"
    assert result.rxcui == "866429"
    assert result.canonical_rxcui == "860975"
    assert result.term_type == "SBD"
    assert result.canonical_term_type == "SCD"
    assert result.source_suppress == "N"
    assert result.canonical_suppress == "N"
    assert result.status == "resolved_exact_generic_product"
    assert result.dataset_version == "01-Sep-2026"


@pytest.mark.asyncio
async def test_exact_ingredient_does_not_call_generic_endpoint(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": ["6918"]}}
        if url.endswith("/6918/properties.json"):
            return properties("metoprolol", "IN")
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
            return properties("metoprolol", "IN")
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
            return properties("component only", "SCDC")
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
            return properties("first", "IN")
        if url.endswith("/2/properties.json"):
            return properties("second", "PIN")
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    calls = install_fake(monkeypatch, responder)
    client = RxNormClient()
    await client.resolve("first")
    await client.resolve("second")
    assert sum(url.endswith("version.json") for url, _ in calls) == 1


@pytest.mark.asyncio
async def test_inactive_exact_concept_fails_closed(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": ["123"]}}
        if url.endswith("/123/properties.json"):
            return properties("inactive drug", "IN", suppress="O")
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    install_fake(monkeypatch, responder)
    result = await RxNormClient().resolve("inactive drug")
    assert result.normalized_id is None
    assert result.source_suppress == "O"
    assert result.status == "inactive_concept"


@pytest.mark.asyncio
async def test_resolution_cache_avoids_duplicate_external_calls(monkeypatch) -> None:
    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": ["6918"]}}
        if url.endswith("/6918/properties.json"):
            return properties("metoprolol", "IN")
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    calls = install_fake(monkeypatch, responder)
    client = RxNormClient()
    first = await client.resolve("  metoprolol ")
    second = await client.resolve("METOPROLOL")
    assert first == second
    assert sum(url.endswith("rxcui.json") for url, _ in calls) == 1


@pytest.mark.asyncio
async def test_transient_failure_is_not_cached(monkeypatch) -> None:
    attempts = 0

    def responder(url: str, params: dict | None) -> dict:
        nonlocal attempts
        if url.endswith("rxcui.json"):
            attempts += 1
            if attempts == 1:
                raise ValueError("synthetic malformed response")
            return {"idGroup": {"rxnormId": ["6918"]}}
        if url.endswith("/6918/properties.json"):
            return properties("metoprolol", "IN")
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    install_fake(monkeypatch, responder)
    client = RxNormClient()
    assert (await client.resolve("metoprolol")).status == "unavailable"
    assert (await client.resolve("metoprolol")).status == "resolved_exact"
    assert attempts == 2


@pytest.mark.asyncio
async def test_resolution_cache_expires_after_configured_ttl(monkeypatch) -> None:
    clock = 100.0

    def responder(url: str, params: dict | None) -> dict:
        if url.endswith("rxcui.json"):
            return {"idGroup": {"rxnormId": ["6918"]}}
        if url.endswith("/6918/properties.json"):
            return properties("metoprolol", "IN")
        if url.endswith("version.json"):
            return version_payload()
        raise AssertionError(url)

    calls = install_fake(monkeypatch, responder)
    monkeypatch.setattr(settings, "rxnorm_cache_ttl_seconds", 5.0)
    monkeypatch.setattr(rxnorm_module.time, "monotonic", lambda: clock)
    client = RxNormClient()
    await client.resolve("metoprolol")
    clock = 106.0
    await client.resolve("metoprolol")
    assert sum(url.endswith("rxcui.json") for url, _ in calls) == 2


@pytest.mark.asyncio
async def test_extraction_preserves_rxnorm_provenance(monkeypatch) -> None:
    source = "Continue mysterybrand 5 mg by mouth once a day."
    monkeypatch.setattr(
        extraction,
        "_demo_extract",
        lambda _document: [
            {
                "raw_name": "mysterybrand",
                "dose": "5",
                "unit": "mg",
                "pattern_type": "fixed",
                "times_per_day": 1,
                "interval_hours": None,
                "raw_frequency": "once a day",
                "timing": [],
                "route": "by mouth",
                "duration": None,
                "action": "continue",
                "warning": None,
                "evidence_span": source,
            }
        ],
    )
    monkeypatch.setattr(
        extraction.rxnorm_client,
        "resolve",
        AsyncMock(
            return_value=RxNormResolution(
                normalized_id="rxnorm:200",
                rxcui="100",
                concept_name="Mystery Brand 5 MG Oral Tablet",
                term_type="SBD",
                source_suppress="N",
                canonical_rxcui="200",
                canonical_name="mystery ingredient 5 MG Oral Tablet",
                canonical_term_type="SCD",
                canonical_suppress="N",
                match_strategy="exact",
                dataset_version="01-Sep-2026",
                api_version="3.1.0",
                status="resolved_exact_generic_product",
            )
        ),
    )
    instructions = await extraction.extract_document(
        CareDocument(
            document_id="doc-1",
            document_type="synthetic",
            document_date=date(2026, 9, 1),
            raw_text=source,
        ),
        demo_mode=True,
    )
    medication = instructions[0].medication
    assert medication.normalized_id == "rxnorm:200"
    assert medication.terminology == "rxnorm"
    assert medication.rxcui == "100"
    assert medication.canonical_rxcui == "200"
    assert medication.canonical_term_type == "SCD"
    assert medication.source_suppress == "N"
    assert medication.canonical_suppress == "N"
    assert medication.rxnorm_dataset_version == "01-Sep-2026"
    assert medication.lookup_status == "resolved_exact_generic_product"


@pytest.mark.asyncio
async def test_rxnorm_disabled_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rxnorm_enabled", False)
    result = await RxNormClient().resolve("unknown")
    assert result.status == "disabled"
    assert result.normalized_id is None
