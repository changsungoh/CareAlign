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
