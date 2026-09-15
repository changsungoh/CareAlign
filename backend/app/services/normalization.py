import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

MASS_TO_MG = {
    "mcg": Decimal("0.001"),
    "ug": Decimal("0.001"),
    "mg": Decimal("1"),
    "g": Decimal("1000"),
}

RULES_DIR = Path(__file__).resolve().parents[1] / "rules"
ROUTE_ALIASES = json.loads((RULES_DIR / "route_aliases.json").read_text())
MEDICATION_ALIASES = json.loads((RULES_DIR / "medication_aliases.json").read_text())


def normalize_mass_to_mg(value: str, unit: str) -> Decimal | None:
    factor = MASS_TO_MG.get(unit.casefold().strip())
    if factor is None:
        return None
    try:
        return Decimal(value) * factor
    except InvalidOperation:
        return None


def normalize_route(raw_route: str) -> str | None:
    candidate = raw_route.casefold().strip()
    for normalized, aliases in ROUTE_ALIASES.items():
        if candidate in aliases:
            return normalized
    return None


def normalize_medication(raw_name: str) -> dict[str, str | None]:
    candidate = raw_name.casefold().strip()
    for normalized_id, data in MEDICATION_ALIASES.items():
        if candidate in {alias.casefold() for alias in data["aliases"]}:
            return {
                "normalized_id": normalized_id,
                "ingredient": data.get("ingredient"),
                "salt": data.get("salt"),
                "form": data.get("form"),
            }
    return {"normalized_id": None, "ingredient": None, "salt": None, "form": None}
