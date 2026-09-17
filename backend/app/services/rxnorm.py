from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
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
    source_suppress: str | None = None
    canonical_rxcui: str | None = None
    canonical_name: str | None = None
    canonical_term_type: str | None = None
    canonical_suppress: str | None = None
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
        self._version_cache: tuple[float, str | None, str | None] | None = None
        self._resolution_cache: OrderedDict[str, tuple[float, RxNormResolution]] = OrderedDict()
        self._cache_lock = Lock()

    async def resolve(self, raw_name: str) -> RxNormResolution:
        if not settings.rxnorm_enabled:
            return RxNormResolution(status="disabled")
        query = " ".join(raw_name.split())
        if not query:
            return RxNormResolution(status="not_found")
        cache_key = query.casefold()
        cached = self._cached_resolution(cache_key)
        if cached is not None:
            return cached

        result = await self._resolve_uncached(query)
        if result.status != "unavailable":
            self._store_resolution(cache_key, result)
        return result

    async def _resolve_uncached(self, query: str) -> RxNormResolution:

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

                name, term_type, suppress = properties
                dataset_version, api_version = await self._version(client)
                common = {
                    "rxcui": rxcui,
                    "concept_name": name,
                    "term_type": term_type,
                    "source_suppress": suppress,
                    "match_strategy": "exact",
                    "dataset_version": dataset_version,
                    "api_version": api_version,
                }
                if term_type not in SUPPORTED_EXACT_TERM_TYPES:
                    return RxNormResolution(**common, status="unsupported_term_type")
                if suppress != "N":
                    return RxNormResolution(**common, status="inactive_concept")

                canonical_rxcui = rxcui
                canonical_name = name
                canonical_term_type = term_type
                canonical_suppress = suppress
                status = "resolved_exact"
                if term_type in PRODUCT_TERM_TYPES:
                    generic_ids = await self._generic_product_ids(client, rxcui)
                    if len(generic_ids) != 1:
                        return RxNormResolution(**common, status="generic_mapping_ambiguous")
                    canonical_rxcui = generic_ids[0]
                    canonical_properties = await self._properties(client, canonical_rxcui)
                    if canonical_properties is None:
                        return RxNormResolution(**common, status="malformed_generic_response")
                    canonical_name, canonical_term_type, canonical_suppress = canonical_properties
                    if canonical_term_type not in {"SCD", "GPCK"}:
                        return RxNormResolution(
                            **common,
                            canonical_rxcui=canonical_rxcui,
                            canonical_name=canonical_name,
                            canonical_term_type=canonical_term_type,
                            canonical_suppress=canonical_suppress,
                            status="unsupported_generic_term_type",
                        )
                    if canonical_suppress != "N":
                        return RxNormResolution(
                            **common,
                            canonical_rxcui=canonical_rxcui,
                            canonical_name=canonical_name,
                            canonical_term_type=canonical_term_type,
                            canonical_suppress=canonical_suppress,
                            status="inactive_generic_concept",
                        )
                    status = "resolved_exact_generic_product"

                return RxNormResolution(
                    normalized_id=f"rxnorm:{canonical_rxcui}",
                    **common,
                    canonical_rxcui=canonical_rxcui,
                    canonical_name=canonical_name,
                    canonical_term_type=canonical_term_type,
                    canonical_suppress=canonical_suppress,
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
            source_suppress=properties[2],
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
    ) -> tuple[str, str, str] | None:
        response = await client.get(f"{settings.rxnorm_base_url}/rxcui/{rxcui}/properties.json")
        response.raise_for_status()
        values = response.json().get("properties") or {}
        name = values.get("name")
        term_type = values.get("tty")
        suppress = values.get("suppress")
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(term_type, str)
            or not term_type
            or not isinstance(suppress, str)
            or not suppress
        ):
            return None
        return name, term_type, suppress

    async def _generic_product_ids(self, client: httpx.AsyncClient, rxcui: str) -> list[str]:
        response = await client.get(f"{settings.rxnorm_base_url}/rxcui/{rxcui}/generic.json")
        response.raise_for_status()
        values = response.json().get("minConceptGroup", {}).get("minConcept") or []
        return [
            str(value["rxcui"])
            for value in values
            if isinstance(value, dict) and value.get("rxcui")
        ]

    async def _version(self, client: httpx.AsyncClient) -> tuple[str | None, str | None]:
        now = time.monotonic()
        if self._version_cache is not None:
            cached_at, dataset, api = self._version_cache
            if now - cached_at < settings.rxnorm_cache_ttl_seconds:
                return dataset, api
        try:
            response = await client.get(f"{settings.rxnorm_base_url}/version.json")
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            values = payload.get("version") if isinstance(payload.get("version"), dict) else payload
            dataset = values.get("version") or values.get("rxnormVersion")
            api = values.get("apiVersion")
            dataset_value = str(dataset) if dataset else None
            api_value = str(api) if api else None
            if dataset_value or api_value:
                self._version_cache = (now, dataset_value, api_value)
            return dataset_value, api_value
        except (httpx.HTTPError, TypeError, ValueError):
            return None, None

    def _cached_resolution(self, key: str) -> RxNormResolution | None:
        now = time.monotonic()
        with self._cache_lock:
            cached = self._resolution_cache.get(key)
            if cached is None:
                return None
            cached_at, result = cached
            if now - cached_at >= settings.rxnorm_cache_ttl_seconds:
                del self._resolution_cache[key]
                return None
            self._resolution_cache.move_to_end(key)
            return result

    def _store_resolution(self, key: str, result: RxNormResolution) -> None:
        with self._cache_lock:
            self._resolution_cache[key] = (time.monotonic(), result)
            self._resolution_cache.move_to_end(key)
            while len(self._resolution_cache) > settings.rxnorm_cache_max_entries:
                self._resolution_cache.popitem(last=False)

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._resolution_cache.clear()
        self._version_cache = None


rxnorm_client = RxNormClient()
