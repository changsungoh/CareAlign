from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


# Complete ingredient or product concepts that preserve a usable identity.
# Component/group TTYs are excluded because they can omit strength or dose form.
SUPPORTED_EXACT_TERM_TYPES = frozenset({"IN", "PIN", "MIN", "SCD", "SBD", "GPCK", "BPCK"})
PRODUCT_TERM_TYPES = frozenset({"SCD", "SBD", "GPCK", "BPCK"})


@dataclass(frozen=True)
class RxNormResolution:
    normalized_id: str | None = None
    rxcui: str | None = None
    concept_name: str | None = None
    term_type: str | None = None
    canonical_rxcui: str | None = None
    canonical_name: str | None = None
    canonical_term_type: str | None = None
    match_strategy: str | None = None
    dataset_version: str | None = None
    api_version: str | None = None
    status: str = "not_requested"


class RxNormClient:
    """Safety-first NLM RxNorm resolver with no therapeutic inference.

    Only a unique active exact match can become a comparison identity. A
    normalized match is retained as a review candidate because RxNorm's
    normalized search can ignore salt/form words. Branded products may be
    mapped to one unbranded product through the documented generic endpoint;
    ingredient concepts and unsupported TTYs are never sent to that endpoint.
    """

    def __init__(self) -> None:
        self._version_cache: tuple[str | None, str | None] | None = None

    async def resolve(self, raw_name: str) -> RxNormResolution:
        if not settings.rxnorm_enabled:
            return RxNormResolution(status="disabled")
        query = " ".join(raw_name.split())
        if not query:
            return RxNormResolution(status="not_found")

        try:
            async with httpx.AsyncClient(timeout=settings.rxnorm_timeout_seconds) as client:
                exact_ids = await self._search(client, query, search=0)
                if len(exact_ids) > 1:
                    return RxNormResolution(match_strategy="exact", status="ambiguous_exact")
                if not exact_ids:
                    return await self._normalized_candidate(client, query)

                rxcui = exact_ids[0]
                properties = await self._properties(client, rxcui)
                if properties is None:
                    return RxNormResolution(
                        rxcui=rxcui,
                        match_strategy="exact",
                        status="malformed_response",
                    )

                name, term_type = properties
                dataset_version, api_version = await self._version(client)
                common = {
                    "rxcui": rxcui,
                    "concept_name": name,
                    "term_type": term_type,
                    "match_strategy": "exact",
                    "dataset_version": dataset_version,
                    "api_version": api_version,
                }
                if term_type not in SUPPORTED_EXACT_TERM_TYPES:
                    return RxNormResolution(**common, status="unsupported_term_type")

                canonical_rxcui = rxcui
                canonical_name = name
                canonical_term_type = term_type
                status = "resolved_exact"
                if term_type in PRODUCT_TERM_TYPES:
                    generic_ids = await self._generic_product_ids(client, rxcui)
                    if len(generic_ids) != 1:
                        return RxNormResolution(**common, status="generic_mapping_ambiguous")
                    canonical_rxcui = generic_ids[0]
                    canonical_properties = await self._properties(client, canonical_rxcui)
                    if canonical_properties is None:
                        return RxNormResolution(**common, status="malformed_generic_response")
                    canonical_name, canonical_term_type = canonical_properties
                    if canonical_term_type not in {"SCD", "GPCK"}:
                        return RxNormResolution(
                            **common,
                            canonical_rxcui=canonical_rxcui,
                            canonical_name=canonical_name,
                            canonical_term_type=canonical_term_type,
                            status="unsupported_generic_term_type",
                        )
                    status = "resolved_exact_generic_product"

                return RxNormResolution(
                    normalized_id=f"rxnorm:{canonical_rxcui}",
                    **common,
                    canonical_rxcui=canonical_rxcui,
                    canonical_name=canonical_name,
                    canonical_term_type=canonical_term_type,
                    status=status,
                )
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return RxNormResolution(status="unavailable")

    async def _normalized_candidate(
        self, client: httpx.AsyncClient, query: str
    ) -> RxNormResolution:
        identifiers = await self._search(client, query, search=1)
        if len(identifiers) > 1:
            return RxNormResolution(match_strategy="normalized", status="ambiguous_normalized")
        if not identifiers:
            return RxNormResolution(match_strategy="normalized", status="not_found")
        rxcui = identifiers[0]
        properties = await self._properties(client, rxcui)
        if properties is None:
            return RxNormResolution(
                rxcui=rxcui,
                match_strategy="normalized",
                status="malformed_response",
            )
        dataset_version, api_version = await self._version(client)
        return RxNormResolution(
            rxcui=rxcui,
            concept_name=properties[0],
            term_type=properties[1],
            match_strategy="normalized",
            dataset_version=dataset_version,
            api_version=api_version,
            status="normalized_candidate_needs_review",
        )

    async def _search(self, client: httpx.AsyncClient, query: str, search: int) -> list[str]:
        response = await client.get(
            f"{settings.rxnorm_base_url}/rxcui.json",
            params={"name": query, "search": search, "allsrc": 0},
        )
        response.raise_for_status()
        values = response.json().get("idGroup", {}).get("rxnormId") or []
        return [str(value) for value in values]

    async def _properties(
        self, client: httpx.AsyncClient, rxcui: str
    ) -> tuple[str, str] | None:
        response = await client.get(
            f"{settings.rxnorm_base_url}/rxcui/{rxcui}/properties.json"
        )
        response.raise_for_status()
        values = response.json().get("properties") or {}
        name = values.get("name")
        term_type = values.get("tty")
        if not isinstance(name, str) or not name or not isinstance(term_type, str) or not term_type:
            return None
        return name, term_type

    async def _generic_product_ids(
        self, client: httpx.AsyncClient, rxcui: str
    ) -> list[str]:
        response = await client.get(f"{settings.rxnorm_base_url}/rxcui/{rxcui}/generic.json")
        response.raise_for_status()
        values = response.json().get("minConceptGroup", {}).get("minConcept") or []
        return [
            str(value["rxcui"])
            for value in values
            if isinstance(value, dict) and value.get("rxcui")
        ]

    async def _version(self, client: httpx.AsyncClient) -> tuple[str | None, str | None]:
        if self._version_cache is not None:
            return self._version_cache
        try:
            response = await client.get(f"{settings.rxnorm_base_url}/version.json")
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            values = payload.get("version") if isinstance(payload.get("version"), dict) else payload
            dataset = values.get("version") or values.get("rxnormVersion")
            api = values.get("apiVersion")
            self._version_cache = (
                str(dataset) if dataset else None,
                str(api) if api else None,
            )
        except (httpx.HTTPError, TypeError, ValueError):
            self._version_cache = (None, None)
        return self._version_cache


rxnorm_client = RxNormClient()
