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


# ---------------------------------------------------------------------------
# Contradiction checks for the remaining structured fields.
#
# Policy: only *contradictions* are acted on. A value the quote simply does not
# mention is left alone (the provider may legitimately normalise wording), but a
# value the quote visibly contradicts must never be auto-validated.
# ---------------------------------------------------------------------------

_WORD_COUNTS = {
    "once": 1, "twice": 2, "thrice": 3, "three times": 3, "four times": 4,
    "five times": 5, "six times": 6, "qd": 1, "bid": 2, "tid": 3, "qid": 4,
}  # fmt: skip
_COUNT_RE = re.compile(
    r"\b(once|twice|thrice|three times|four times|five times|six times)\b"
    r"|\b(\d{1,2})\s*(?:x|times)\s*(?:a|per|/)?\s*(?:day|daily)\b"
    r"|\b(q\.?d\.?|b\.?i\.?d\.?|t\.?i\.?d\.?|q\.?i\.?d\.?)(?=\W|$)"
)
_DAILY_RE = re.compile(r"\b(daily|nightly)\b")
# Distinct times of day: "morning and at bedtime" is two doses, "every night at bedtime" is one.
_TIME_PHRASE_RE = re.compile(
    r"\b(?:every|in the|each)\s+(?:morning|evening|night)\b|\bat\s+(?:bedtime|night)\b|\bnightly\b"
)
_TIME_WORD_RE = re.compile(r"\b(morning|evening|night|nightly|bedtime)\b")
_INTERVAL_RE = re.compile(r"\bevery\s+(\d{1,3})\s*(?:hours?|hrs?|h)\b|\bq\s*(\d{1,3})\s*h\b")
_NON_DAILY_RE = re.compile(
    r"\b(every other day|alternate days?|every (?:2|two|3|three|4|four) days"
    r"|once (?:a|per) week|once weekly|twice weekly|every week|\d+ times (?:a|per) week)\b"
)
# Bare "if needed" is ambiguous ("call your doctor if needed"), so it only counts as a
# dosing instruction when tied to a purpose ("if needed for pain").
_PRN_RE = re.compile(r"\b(as needed|prn|p\.r\.n\.?|when needed|if needed (?:for|to))\b")
_TAPER_RE = re.compile(r"\b(taper(?:ing)?|titrat\w+|wean\w*)\b")

_ACTION_WORDS = {
    "stop": {"stop", "discontinue", "cease", "do not take"},
    "hold": {"hold", "pause", "withhold"},
    "start": {"start", "begin", "initiate"},
    "continue": {"continue", "keep taking", "maintain"},
}


def _folded(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def _daily_counts(text: str) -> set[int]:
    counts: set[int] = set()
    for match in _COUNT_RE.finditer(text):
        word, number, abbreviation = match.groups()
        if word:
            counts.add(_WORD_COUNTS[word])
        elif number:
            counts.add(int(number))
        elif abbreviation:
            counts.add(_WORD_COUNTS[abbreviation.replace(".", "")])
    if not counts and (_DAILY_RE.search(text) or _TIME_PHRASE_RE.search(text)):
        moments = {
            "night" if word in {"night", "nightly", "bedtime"} else word
            for word in _TIME_WORD_RE.findall(text)
        }
        counts.add(max(1, len(moments)))
    return counts


def field_contradictions(
    evidence: str,
    *,
    pattern_type: str | None,
    times_per_day: int | None,
    interval_hours: int | None,
    route_raw: str | None,
    action: str | None,
) -> tuple[list[str], list[str]]:
    """Return ``(schedule_contradictions, value_contradictions)`` for one instruction.

    Schedule contradictions mean the *kind* of schedule is wrong (PRN/taper/
    non-daily labelled as a fixed schedule), so the instruction cannot be
    compared safely. Value contradictions mean a stated number or word differs
    from the quote and the item needs human review.
    """
    text = _folded(evidence)
    schedule: list[str] = []
    values: list[str] = []
    scheduled = pattern_type in {"fixed", "interval"}

    if scheduled and _PRN_RE.search(text):
        schedule.append("quote says as-needed but a fixed schedule was extracted")
    if scheduled and _TAPER_RE.search(text):
        schedule.append("quote describes a taper but a fixed schedule was extracted")
    if scheduled and _NON_DAILY_RE.search(text):
        schedule.append("quote is not a daily schedule but a daily schedule was extracted")

    counts = _daily_counts(text)
    intervals = {int(a or b) for a, b in _INTERVAL_RE.findall(text)}
    if times_per_day is not None and counts and times_per_day not in counts:
        derived = {24 // h for h in intervals if h and 24 % h == 0}
        if times_per_day not in derived:
            values.append(f"times_per_day={times_per_day} not in quote (found {sorted(counts)})")
    if interval_hours is not None and intervals and interval_hours not in intervals:
        values.append(f"interval_hours={interval_hours} not in quote (found {sorted(intervals)})")

    if route_raw:
        # The route must be traceable to the quote, either literally or via an alias of the
        # same normalised route ("oral" is accepted for "by mouth").
        from app.services.normalization import ROUTE_ALIASES, normalize_route

        normalized = normalize_route(route_raw)
        spellings = {_folded(route_raw)} | {_folded(a) for a in ROUTE_ALIASES.get(normalized, [])}
        if not any(re.search(rf"(?<![a-z]){re.escape(sp)}(?![a-z])", text) for sp in spellings):
            values.append("route text does not appear in the quote")

    if action:
        claimed = action.casefold().strip()
        if claimed in _ACTION_WORDS:
            present = {
                name
                for name, words in _ACTION_WORDS.items()
                if any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)
            }
            if present and claimed not in present:
                values.append(f"action '{claimed}' contradicts the quote (found {sorted(present)})")
    return schedule, values


# ---------------------------------------------------------------------------
# Language boundary.
#
# Every schedule/route/action safety net above reads English vocabulary. Wording in another
# script cannot be checked by it, so a PRN, taper or every-other-day instruction that a provider
# mislabelled as a fixed schedule would pass unnoticed. Until a language has its own reviewed
# vocabulary and evaluation set, an instruction whose evidence is not Latin-script text is never
# auto-validated.
# ---------------------------------------------------------------------------

# Greek letters that appear inside otherwise English dosing text: µg/μg and "β-blocker".
_ALLOWED_NON_LATIN = frozenset("μαβ")


def has_unsupported_script(text: str) -> bool:
    """True when ``text`` contains letters outside the Latin script (Hangul, Cyrillic, ...)."""
    for char in unicodedata.normalize("NFKC", text):
        if not char.isalpha() or char in _ALLOWED_NON_LATIN:
            continue
        if not unicodedata.name(char, "").startswith("LATIN"):
            return True
    return False
