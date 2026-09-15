from collections import defaultdict
from itertools import count

from app.core.config import settings
from app.models.schemas import Conflict, ConflictType, Instruction, ValidationStatus
from app.services.normalization import normalize_mass_to_mg


def _question(name: str, detail: str) -> str:
    return (
        f"My records show different instructions for {name} ({detail}). "
        "Which instruction should I follow?"
    )


def detect_conflicts(
    instructions: list[Instruction], ordered_document_ids: list[str]
) -> list[Conflict]:
    groups: dict[str, list[Instruction]] = defaultdict(list)
    uncertain: list[Instruction] = []
    for item in instructions:
        key = item.medication.normalized_id
        (groups[key].append(item) if key else uncertain.append(item))
    output: list[Conflict] = []
    serial = count(1)

    def emit(kind: ConflictType, items: list[Instruction], summary: str, confidence: float = 0.96):
        status = (
            ValidationStatus.VALIDATED
            if confidence >= settings.confidence_threshold
            else ValidationStatus.NEEDS_REVIEW
        )
        output.append(
            Conflict(
                conflict_id=f"c{next(serial)}",
                conflict_type=kind,
                medication_name=items[0].medication.raw_name,
                instruction_ids=[item.instruction_id for item in items],
                document_ids=[item.document_id for item in items],
                summary=summary,
                clarification_question=_question(items[0].medication.raw_name, summary),
                status=status,
                confidence=confidence,
                evidence_spans=[item.evidence_span for item in items],
            )
        )

    for item in uncertain:
        emit(
            ConflictType.IDENTITY,
            [item],
            "the medication identity could not be safely matched",
            0.4,
        )

    for _, items in groups.items():
        by_doc = {item.document_id: item for item in items}
        explicit_action = any((item.action or "").casefold() in {"stop", "hold"} for item in items)
        if len(by_doc) < len(ordered_document_ids) and not explicit_action:
            emit(
                ConflictType.OMISSION,
                items,
                "the medication appears in one record but not another; intent is unknown",
                0.9,
            )
        if len(items) < 2:
            continue
        left, right = items[-2], items[-1]
        if (
            left.dose
            and right.dose
            and left.dose.raw_value
            and right.dose.raw_value
            and left.dose.raw_unit
            and right.dose.raw_unit
        ):
            a = normalize_mass_to_mg(left.dose.raw_value, left.dose.raw_unit)
            b = normalize_mass_to_mg(right.dose.raw_value, right.dose.raw_unit)
            if a is None or b is None:
                emit(
                    ConflictType.DOSE,
                    [left, right],
                    "the doses use units that cannot be safely compared",
                    0.4,
                )
            elif a != b:
                emit(
                    ConflictType.DOSE,
                    [left, right],
                    "dose changed from "
                    f"{left.dose.raw_value} {left.dose.raw_unit} to "
                    f"{right.dose.raw_value} {right.dose.raw_unit}",
                )
        lf, rf = left.frequency, right.frequency
        if (
            lf
            and rf
            and lf.pattern_type.value in {"fixed", "interval"}
            and rf.pattern_type.value in {"fixed", "interval"}
        ):
            lvalue = (lf.times_per_day, lf.interval_hours)
            rvalue = (rf.times_per_day, rf.interval_hours)
            if lvalue != rvalue:
                emit(
                    ConflictType.FREQUENCY,
                    [left, right],
                    f"frequency changed from '{lf.raw_expression}' to '{rf.raw_expression}'",
                )
        if left.route and right.route and left.route.normalized != right.route.normalized:
            emit(ConflictType.ROUTE, [left, right], "the administration routes differ")
        if left.action and right.action and left.action.casefold() != right.action.casefold():
            emit(
                ConflictType.ACTION,
                [left, right],
                f"action changed from {left.action} to {right.action}",
            )
    return output
