from decimal import Decimal

MASS_TO_MG = {
    "mcg": Decimal("0.001"),
    "ug": Decimal("0.001"),
    "mg": Decimal("1"),
    "g": Decimal("1000"),
}

ROUTE_ALIASES = {
    "oral": {"oral", "by mouth", "po", "p.o."},
    "sublingual": {"sublingual", "sl", "under the tongue"},
    "topical": {"topical", "apply to skin"},
    "inhaled": {"inhaled", "inhalation"},
    "intramuscular": {"intramuscular", "im"},
    "intravenous": {"intravenous", "iv"},
    "subcutaneous": {"subcutaneous", "sc", "sq"},
}


def normalize_mass_to_mg(value: str, unit: str) -> Decimal | None:
    factor = MASS_TO_MG.get(unit.casefold().strip())
    if factor is None:
        return None
    return Decimal(value) * factor


def normalize_route(raw_route: str) -> str | None:
    candidate = raw_route.casefold().strip()
    for normalized, aliases in ROUTE_ALIASES.items():
        if candidate in aliases:
            return normalized
    return None
