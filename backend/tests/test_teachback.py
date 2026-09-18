from app.models.schemas import (
    Dose,
    Frequency,
    Instruction,
    MedicationIdentity,
    PatternType,
    Timing,
    ValidationStatus,
)
from app.services.teachback import build_checklist, evaluate_teachback


def safe_instruction() -> Instruction:
    return Instruction(
        instruction_id="safe-1",
        document_id="new",
        medication=MedicationIdentity(raw_name="lisinopril", normalized_id="lisinopril"),
        dose=Dose(raw_value="10", raw_unit="mg"),
        frequency=Frequency(
            pattern_type=PatternType.FIXED,
            times_per_day=1,
            raw_expression="once a day",
        ),
        timing=Timing(values=["morning"], raw_expression="morning"),
        evidence_span="lisinopril 10 mg once a day in the morning",
        validation_status=ValidationStatus.VALIDATED,
    )


def test_checklist_is_generated_only_from_validated_fields() -> None:
    checklist = build_checklist([safe_instruction()], set())
    assert {item.category for item in checklist} == {"medication", "dose", "frequency", "timing"}


def test_excluded_conflict_cannot_become_answer_key() -> None:
    assert build_checklist([safe_instruction()], {"safe-1"}) == []


def test_matching_paraphrase_is_not_marked_missing() -> None:
    result = evaluate_teachback(
        [safe_instruction()], set(), "I take lisinopril 10 mg once a day in the morning."
    )
    assert all(item.result == "correct" for item in result.findings)


def test_empty_checklist_cannot_report_success() -> None:
    result = evaluate_teachback(
        [safe_instruction()], {"safe-1"}, "I take lisinopril once a day."
    )

    assert result.checklist == []
    assert result.findings == []
    assert result.needs_human_review is True
    assert "unavailable" in result.message.casefold()
