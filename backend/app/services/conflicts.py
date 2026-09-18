from collections import defaultdict
from dataclasses import dataclass, field
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
        by_doc = {item.document_id: item for item in items}
        explicit_action = any((item.action or "").casefold() in {"stop", "hold"} for item in items)
        missing = [document_id for document_id in ordered_document_ids if document_id not in by_doc]
        if missing and not explicit_action:
            collect(
                medication_id,
                ConflictType.OMISSION,
                items,
                "the medication is absent from "
                f"{len(missing)} of {len(ordered_document_ids)} records; intent is unknown",
                0.9,
            )

        for left, right in zip(items, items[1:], strict=False):
            transition = f"{left.document_id} → {right.document_id}"
            if (
                left.dose
                and right.dose
                and left.dose.raw_value
                and right.dose.raw_value
                and left.dose.raw_unit
                and right.dose.raw_unit
            ):
                left_mass = normalize_mass_to_mg(left.dose.raw_value, left.dose.raw_unit)
                right_mass = normalize_mass_to_mg(right.dose.raw_value, right.dose.raw_unit)
                if left_mass is None or right_mass is None:
                    collect(
                        medication_id,
                        ConflictType.DOSE,
                        [left, right],
                        f"{transition}: units cannot be safely compared",
                        0.4,
                    )
                elif left_mass != right_mass:
                    collect(
                        medication_id,
                        ConflictType.DOSE,
                        [left, right],
                        f"{transition}: {left.dose.raw_value} {left.dose.raw_unit} → "
                        f"{right.dose.raw_value} {right.dose.raw_unit}",
                    )
            left_frequency, right_frequency = left.frequency, right.frequency
            comparable = {"fixed", "interval"}
            if (
                left_frequency
                and right_frequency
                and left_frequency.pattern_type.value in comparable
                and right_frequency.pattern_type.value in comparable
            ):
                left_value = _canonical_frequency(left)
                right_value = _canonical_frequency(right)
                if left_value is not None and right_value is not None and left_value != right_value:
                    collect(
                        medication_id,
                        ConflictType.FREQUENCY,
                        [left, right],
                        f"{transition}: '{left_frequency.raw_expression}' → "
                        f"'{right_frequency.raw_expression}'",
                    )
            if left.route and right.route and left.route.normalized != right.route.normalized:
                collect(
                    medication_id,
                    ConflictType.ROUTE,
                    [left, right],
                    f"{transition}: administration routes differ",
                )
            if left.action and right.action and left.action.casefold() != right.action.casefold():
                collect(
                    medication_id,
                    ConflictType.ACTION,
                    [left, right],
                    f"{transition}: {left.action} → {right.action}",
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
