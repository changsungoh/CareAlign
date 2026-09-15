import re
import unicodedata
from dataclasses import dataclass
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
