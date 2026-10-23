import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import count

from app.core.config import settings
from app.models.schemas import Conflict, ConflictType, Instruction, ValidationStatus
from app.services.normalization import normalize_mass_to_mg


@dataclass
class Finding:
    kind: ConflictType
    medication_name: str
    items: list[Instruction] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    confidence: float = 0.96


def _question(name: str, detail: str) -> str:
    return (
        f"My records show different instructions for {name} ({detail}). "
        "Which instruction should I follow?"
    )


def _append_unique(target: list[Instruction], additions: list[Instruction]) -> None:
    known = {item.instruction_id for item in target}
    target.extend(item for item in additions if item.instruction_id not in known)


def _canonical_frequency(item: Instruction) -> tuple[str, int] | None:
    """Return the safest deterministic representation available for comparison.

    Structured extraction may redundantly encode a daily instruction as both
    ``times_per_day=1`` and ``interval_hours=24``. Prefer the explicit daily
    count so that harmless provider variation cannot create a false flag.
    Exact sub-day intervals are converted to the same daily-count form.
    """
    frequency = item.frequency
    if frequency is None:
        return None
    if frequency.times_per_day is not None:
        return ("times_per_day", frequency.times_per_day)
    if frequency.interval_hours is None:
        return None
    if frequency.interval_hours <= 24 and 24 % frequency.interval_hours == 0:
        return ("times_per_day", 24 // frequency.interval_hours)
    return ("interval_hours", frequency.interval_hours)


_TIMING_CANONICAL = {
    "morning": {"morning", "am", "in the morning", "every morning", "a.m."},
    "evening": {"evening", "in the evening", "every evening"},
    "bedtime": {
        "bedtime",
        "at bedtime",
        "night",
        "at night",
        "nightly",
        "before bed",
        "every night",
    },
    "with_meals": {"with meals", "with food", "with a meal", "with breakfast and dinner"},
}
_TIMING_LOOKUP = {alias: name for name, aliases in _TIMING_CANONICAL.items() for alias in aliases}


def _timing_values(entries: list[Instruction]) -> tuple[set[str], bool]:
    """Return the normalised timing values and whether every one is a recognised spelling."""
    values: set[str] = set()
    recognised = True
    for item in entries:
        for raw in item.timing.values if item.timing else []:
            folded = " ".join(raw.casefold().split())
            if not folded:
                continue
            if folded in _TIMING_LOOKUP:
                values.add(_TIMING_LOOKUP[folded])
            else:
                values.add(folded)
                recognised = False
    return values, recognised


def _schedule_kinds(entries: list[Instruction]) -> set[str]:
    """Schedule families present in a document; unsupported/unknown patterns are left out.

    A model that could not classify a schedule says nothing about whether the schedule changed, so
    it must not be reported as a change. Fixed and interval schedules form one comparable family.
    """
    kinds: set[str] = set()
    for item in entries:
        if not item.frequency:
            continue
        pattern = item.frequency.pattern_type.value
        if pattern in {"fixed", "interval"}:
            kinds.add("scheduled")
        elif pattern != "unsupported":
            kinds.add(pattern)
    return kinds


_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fourteen": 14,
}  # fmt: skip
_DAY_FACTORS = {"day": 1, "week": 7, "wk": 7, "month": 30}
_DURATION_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve"
    r"|fourteen)\s*-?\s*(day|week|wk|month)s?\b"
)
# "once a week" or "every 2 days" describe how often, not how long.
_FREQUENCY_PHRASE_RE = re.compile(
    r"\b(?:once|twice|every|each|per)\s+(?:a\s+|an\s+)?(?:\d+\s*)?(?:day|week|wk|month)s?\b"
)
_OPEN_ENDED_RE = re.compile(
    r"\b(ongoing|indefinite(?:ly)?|long[- ]term|life[- ]?long|until further notice|permanently)\b"
)


def _duration_profile(entries: list[Instruction]) -> tuple[list[int], bool, bool]:
    """Return ``(course lengths in days, open-ended, uses months)`` stated in one document."""
    lengths: set[int] = set()
    open_ended = uses_months = False
    for item in entries:
        if not item.duration:
            continue
        text = " ".join(item.duration.casefold().split())
        text = re.sub(r"\bx\s*(?=\d)", "", text)
        if _OPEN_ENDED_RE.search(text):
            open_ended = True
        text = _FREQUENCY_PHRASE_RE.sub(" ", text)
        for amount, unit in _DURATION_RE.findall(text):
            value = float(amount) if amount.replace(".", "", 1).isdigit() else _NUMBER_WORDS[amount]
            lengths.add(round(value * _DAY_FACTORS[unit]))
            uses_months = uses_months or unit == "month"
    return sorted(lengths), open_ended, uses_months


def _same_course(left: list[int], right: list[int], tolerance: int) -> bool:
    return len(left) == len(right) and all(
        abs(a - b) <= tolerance for a, b in zip(left, right, strict=True)
    )


def _describe_duration(lengths: list[int], open_ended: bool) -> str:
    parts = [f"{days} days" for days in lengths] + (["ongoing"] if open_ended else [])
    return " + ".join(parts)


def detect_conflicts(
    instructions: list[Instruction], ordered_document_ids: list[str]
) -> list[Conflict]:
    """Compare every longitudinal transition and collapse duplicate alert types."""
    order = {document_id: index for index, document_id in enumerate(ordered_document_ids)}
    groups: dict[str, list[Instruction]] = defaultdict(list)
    uncertain: list[Instruction] = []
    for item in instructions:
        key = item.medication.normalized_id
        (groups[key].append(item) if key else uncertain.append(item))

    findings: dict[tuple[str, ConflictType], Finding] = {}

    def collect(
        key: str,
        kind: ConflictType,
        items: list[Instruction],
        detail: str,
        confidence: float = 0.96,
    ) -> None:
        finding_key = (key, kind)
        if finding_key not in findings:
            findings[finding_key] = Finding(
                kind=kind,
                medication_name=items[0].medication.raw_name,
                confidence=confidence,
            )
        finding = findings[finding_key]
        _append_unique(finding.items, items)
        if detail not in finding.details:
            finding.details.append(detail)
        finding.confidence = min(finding.confidence, confidence)

    for item in uncertain:
        collect(
            item.instruction_id,
            ConflictType.IDENTITY,
            [item],
            "the medication identity could not be safely matched",
            0.4,
        )

    for medication_id, raw_items in groups.items():
        items = sorted(raw_items, key=lambda item: order[item.document_id])
        present = {item.document_id for item in items}
        explicit_action = any((item.action or "").casefold() in {"stop", "hold"} for item in items)
        missing = [
            document_id for document_id in ordered_document_ids if document_id not in present
        ]
        if missing and not explicit_action:
            collect(
                medication_id,
                ConflictType.OMISSION,
                items,
                "the medication is absent from "
                f"{len(missing)} of {len(ordered_document_ids)} records; intent is unknown",
                0.9,
            )

        # One medication may legitimately appear several times in a single document
        # (e.g. 500 mg morning + 1000 mg evening). Compare consecutive *documents*,
        # never entries of the same document with each other.
        per_document: list[list[Instruction]] = []
        for document_id in ordered_document_ids:
            entries = [item for item in items if item.document_id == document_id]
            if entries:
                per_document.append(entries)
        for left_entries, right_entries in zip(per_document, per_document[1:], strict=False):
            both = left_entries + right_entries
            transition = f"{left_entries[0].document_id} → {right_entries[0].document_id}"

            def dose_signature(entries: list[Instruction]) -> list[tuple[str, str]]:
                return [
                    (item.dose.raw_value, item.dose.raw_unit)
                    for item in entries
                    if item.dose and item.dose.raw_value and item.dose.raw_unit
                ]

            def show(signature: list[tuple[str, str]]) -> str:
                return " + ".join(f"{value} {unit}" for value, unit in signature)

            left_doses, right_doses = dose_signature(left_entries), dose_signature(right_entries)
            if left_doses and right_doses:
                left_mass = [normalize_mass_to_mg(v, u) for v, u in left_doses]
                right_mass = [normalize_mass_to_mg(v, u) for v, u in right_doses]
                if None in left_mass or None in right_mass:
                    # Non-mass units (tablet, mL, …) are only comparable when written identically.
                    same_text = sorted(
                        (Decimal(v), u.casefold().strip()) for v, u in left_doses
                    ) == sorted((Decimal(v), u.casefold().strip()) for v, u in right_doses)
                    if not same_text:
                        collect(
                            medication_id,
                            ConflictType.DOSE,
                            both,
                            f"{transition}: units cannot be safely compared",
                            0.4,
                        )
                elif sorted(left_mass) != sorted(right_mass):
                    collect(
                        medication_id,
                        ConflictType.DOSE,
                        both,
                        f"{transition}: {show(left_doses)} → {show(right_doses)}",
                    )
            elif bool(left_doses) != bool(right_doses):
                # A dose that appears or disappears must never end as "no conflict".
                collect(
                    medication_id,
                    ConflictType.DOSE,
                    both,
                    f"{transition}: a dose is stated in only one of the two records",
                    0.9,
                )

            comparable = {"fixed", "interval"}
            left_freqs = [i for i in left_entries if i.frequency]
            right_freqs = [i for i in right_entries if i.frequency]
            if (
                left_freqs
                and right_freqs
                and all(
                    i.frequency.pattern_type.value in comparable for i in left_freqs + right_freqs
                )
            ):
                left_values = [_canonical_frequency(i) for i in left_freqs]
                right_values = [_canonical_frequency(i) for i in right_freqs]
                if (
                    None not in left_values
                    and None not in right_values
                    and sorted(left_values) != sorted(right_values)
                ):
                    collect(
                        medication_id,
                        ConflictType.FREQUENCY,
                        both,
                        f"{transition}: "
                        + " + ".join(f"'{i.frequency.raw_expression}'" for i in left_freqs)
                        + " → "
                        + " + ".join(f"'{i.frequency.raw_expression}'" for i in right_freqs),
                    )

            left_kinds, right_kinds = _schedule_kinds(left_entries), _schedule_kinds(right_entries)
            if left_kinds and right_kinds and left_kinds != right_kinds:
                collect(
                    medication_id,
                    ConflictType.FREQUENCY,
                    both,
                    f"{transition}: schedule type changed ({' + '.join(sorted(left_kinds))} → "
                    f"{' + '.join(sorted(right_kinds))})",
                )
            elif left_kinds == right_kinds == {"prn"}:
                left_gap = {i.frequency.interval_hours for i in left_entries if i.frequency} - {
                    None
                }
                right_gap = {i.frequency.interval_hours for i in right_entries if i.frequency} - {
                    None
                }
                if left_gap and right_gap and left_gap != right_gap:
                    collect(
                        medication_id,
                        ConflictType.FREQUENCY,
                        both,
                        f"{transition}: as-needed interval "
                        f"{'/'.join(map(str, sorted(left_gap)))} h → "
                        f"{'/'.join(map(str, sorted(right_gap)))} h",
                    )

            left_times, left_known = _timing_values(left_entries)
            right_times, right_known = _timing_values(right_entries)
            if left_times and right_times and left_times != right_times:
                # A timing the vocabulary does not recognise is still a likely change, but the
                # rule cannot be sure two spellings differ in meaning, so it goes to review.
                collect(
                    medication_id,
                    ConflictType.TIMING,
                    both,
                    f"{transition}: timing {' + '.join(sorted(left_times))} → "
                    f"{' + '.join(sorted(right_times))}",
                    0.9 if left_known and right_known else 0.6,
                )

            left_days, left_open, left_months = _duration_profile(left_entries)
            right_days, right_open, right_months = _duration_profile(right_entries)
            if (left_days or left_open) and (right_days or right_open):
                # Month lengths vary (28-31 days), so allow a small gap only when months are used.
                tolerance = 2 if left_months or right_months else 0
                if left_open != right_open or not _same_course(left_days, right_days, tolerance):
                    collect(
                        medication_id,
                        ConflictType.DURATION,
                        both,
                        f"{transition}: duration {_describe_duration(left_days, left_open)} → "
                        f"{_describe_duration(right_days, right_open)}",
                        0.9,
                    )

            left_routes = {i.route.normalized for i in left_entries if i.route}
            right_routes = {i.route.normalized for i in right_entries if i.route}
            if left_routes and right_routes and left_routes != right_routes:
                collect(
                    medication_id,
                    ConflictType.ROUTE,
                    both,
                    f"{transition}: administration routes differ",
                )

            left_actions = {i.action.casefold() for i in left_entries if i.action}
            right_actions = {i.action.casefold() for i in right_entries if i.action}
            if left_actions and right_actions and left_actions != right_actions:
                collect(
                    medication_id,
                    ConflictType.ACTION,
                    both,
                    f"{transition}: {' + '.join(sorted(left_actions))} → "
                    f"{' + '.join(sorted(right_actions))}",
                )

    serial = count(1)
    output: list[Conflict] = []
    for finding in findings.values():
        summary = "; ".join(finding.details)
        output.append(
            Conflict(
                conflict_id=f"c{next(serial)}",
                conflict_type=finding.kind,
                medication_name=finding.medication_name,
                instruction_ids=[item.instruction_id for item in finding.items],
                document_ids=[item.document_id for item in finding.items],
                summary=summary,
                clarification_question=_question(finding.medication_name, summary),
                status=(
                    ValidationStatus.VALIDATED
                    if finding.confidence >= settings.confidence_threshold
                    else ValidationStatus.NEEDS_REVIEW
                ),
                confidence=finding.confidence,
                evidence_spans=[item.evidence_span for item in finding.items],
            )
        )
    return output
