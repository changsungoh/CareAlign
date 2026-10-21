import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher


@dataclass(frozen=True)
class EvidenceMatch:
    status: str
    similarity: float


def normalize_evidence(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.strip(" .,:;!?()[]{}\"'")


def verify_evidence(source: str, evidence: str, fuzzy_threshold: float = 0.95) -> EvidenceMatch:
    normalized_source = normalize_evidence(source)
    normalized_evidence = normalize_evidence(evidence)

    if not normalized_evidence:
        return EvidenceMatch(status="invalid_evidence", similarity=0.0)
    if normalized_evidence in normalized_source:
        return EvidenceMatch(status="validated", similarity=1.0)

    similarity = SequenceMatcher(None, normalized_source, normalized_evidence).ratio()
    if similarity >= fuzzy_threshold:
        return EvidenceMatch(status="needs_review", similarity=similarity)
    return EvidenceMatch(status="invalid_evidence", similarity=similarity)


_NUMBER = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?|\.\d+)(?![\d.]*\d)")
_UNIT_ALIASES = {"mcg": {"mcg", "ug", "µg", "μg"}, "ug": {"mcg", "ug", "µg", "μg"}}


def _numbers(text: str) -> set[Decimal]:
    cleaned = re.sub(r"(?<=\d),(?=\d{3}\b)", "", unicodedata.normalize("NFKC", text))
    return {Decimal(match) for match in _NUMBER.findall(cleaned)}


def dose_supported_by_evidence(evidence: str, value: str | None, unit: str | None) -> bool:
    """True when the structured dose is literally present in the quoted evidence.

    Verifying only that the *quote* exists in the document lets a provider return a
    correct quote with a wrong structured value ("500 mg" quoted, dose "50" returned).
    """
    if value is None:
        return True
    try:
        expected = Decimal(value)
    except InvalidOperation:
        return False
    if expected not in _numbers(evidence):
        return False
    if unit:
        folded = unicodedata.normalize("NFKC", evidence).casefold()
        accepted = _UNIT_ALIASES.get(unit.casefold().strip(), {unit.casefold().strip()})
        return any(re.search(rf"(?<![a-z]){re.escape(u)}(?![a-z])", folded) for u in accepted)
    return True
