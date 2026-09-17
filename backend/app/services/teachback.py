import re
from datetime import UTC, datetime

from app.core.config import settings
from app.core.observability import current_request_id
from app.models.schemas import (
    AnalysisMetadata,
    ChecklistItem,
    Instruction,
    TeachBackFinding,
    TeachBackResponse,
    ValidationStatus,
)


def metadata() -> AnalysisMetadata:
    return AnalysisMetadata(
        app_version=settings.app_version,
        release_sha=settings.deployment_revision,
        request_id=current_request_id(),
        model_name=settings.llm_model if settings.anthropic_api_key else "transparent-demo-matcher",
        prompt_version=settings.prompt_version,
        rules_version=settings.rules_version,
        dataset_version=settings.dataset_version,
        evaluated_at=datetime.now(UTC),
    )


def build_checklist(instructions: list[Instruction], excluded: set[str]) -> list[ChecklistItem]:
    checklist: list[ChecklistItem] = []
    for item in instructions:
        if item.instruction_id in excluded or item.validation_status != ValidationStatus.VALIDATED:
            continue
        fields: list[tuple[str, str]] = [("medication", item.medication.raw_name)]
        if item.dose and item.dose.raw_value and item.dose.raw_unit:
            fields.append(("dose", f"{item.dose.raw_value} {item.dose.raw_unit}"))
        if item.frequency:
            fields.append(("frequency", item.frequency.raw_expression))
        if item.timing and item.timing.raw_expression:
            fields.append(("timing", item.timing.raw_expression))
        if item.warning:
            fields.append(("warning", item.warning))
        for category, value in fields:
            checklist.append(
                ChecklistItem(
                    item_id=f"{item.instruction_id}-{category}",
                    instruction_id=item.instruction_id,
                    category=category,
                    expected_value=value,
                    source_evidence=item.evidence_span,
                )
            )
    return checklist


def evaluate_teachback(
    instructions: list[Instruction], excluded: set[str], response: str
) -> TeachBackResponse:
    checklist = build_checklist(instructions, excluded)
    normalized = re.sub(r"[^a-z0-9.]+", " ", response.casefold())
    findings: list[TeachBackFinding] = []
    for item in checklist:
        tokens = [
            token
            for token in re.sub(r"[^a-z0-9.]+", " ", item.expected_value.casefold()).split()
            if len(token) > 1
        ]
        matched = bool(tokens) and all(token in normalized for token in tokens)
        findings.append(
            TeachBackFinding(
                item_id=item.item_id,
                category=item.category,
                result="correct" if matched else "missing",
                explanation=(
                    "Your explanation included this point."
                    if matched
                    else "This point was not mentioned. Please review it with your care team."
                ),
            )
        )
    missing = sum(item.result != "correct" for item in findings)
    message = (
        "You covered every source-supported point in this demo."
        if not missing
        else f"Let's review {missing} point{'s' if missing != 1 else ''} that were not mentioned."
    )
    return TeachBackResponse(
        checklist=checklist,
        findings=findings,
        message=message,
        needs_human_review=bool(missing),
        metadata=metadata(),
    )
