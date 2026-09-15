from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class RxNormResolution:
    normalized_id: str | None
    rxcui: str | None
    concept_name: str | None
    term_type: str | None
    status: str


class RxNormClient:
    """Conservative NLM RxNorm resolver with no clinical inference."""

    async def resolve(self, raw_name: str) -> RxNormResolution:
        if not settings.rxnorm_enabled:
            return RxNormResolution(None, None, None, None, "disabled")
        try:
            async with httpx.AsyncClient(timeout=settings.rxnorm_timeout_seconds) as client:
                search = await client.get(
                    f"{settings.rxnorm_base_url}/rxcui.json?name={quote(raw_name)}&search=2"
                )
                search.raise_for_status()
                identifiers = search.json().get("idGroup", {}).get("rxnormId", [])
                if len(identifiers) != 1:
                    return RxNormResolution(None, None, None, None, "ambiguous_or_not_found")
                rxcui = str(identifiers[0])
                properties = await client.get(
                    f"{settings.rxnorm_base_url}/rxcui/{rxcui}/properties.json"
                )
                properties.raise_for_status()
                values = properties.json().get("properties") or {}
                generic = await client.get(f"{settings.rxnorm_base_url}/rxcui/{rxcui}/generic.json")
                generic.raise_for_status()
                generic_id = generic.json().get("minConceptGroup", {}).get("minConcept", [])
                canonical = str(generic_id[0]["rxcui"]) if len(generic_id) == 1 else rxcui
                return RxNormResolution(
                    normalized_id=f"rxnorm:{canonical}",
                    rxcui=rxcui,
                    concept_name=values.get("name"),
                    term_type=values.get("tty"),
                    status="resolved",
                )
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return RxNormResolution(None, None, None, None, "unavailable")


rxnorm_client = RxNormClient()
