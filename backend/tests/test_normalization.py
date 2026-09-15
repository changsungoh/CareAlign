from decimal import Decimal

from app.services.normalization import normalize_mass_to_mg, normalize_route


def test_mass_conversion_preserves_decimal_precision() -> None:
    assert normalize_mass_to_mg("0.5", "g") == Decimal("500.0")
    assert normalize_mass_to_mg("500", "mcg") == Decimal("0.500")


def test_incompatible_unit_returns_none() -> None:
    assert normalize_mass_to_mg("5", "mL") is None


def test_route_aliases() -> None:
    assert normalize_route("P.O.") == "oral"
    assert normalize_route("by mouth") == "oral"
    assert normalize_route("unknown route") is None
