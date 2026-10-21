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
    result = evaluate_teachback([safe_instruction()], {"safe-1"}, "I take lisinopril once a day.")

    assert result.checklist == []
    assert result.findings == []
    assert result.needs_human_review is True
    assert "unavailable" in result.message.casefold()


def _dose_only(value: str, unit: str = "mg") -> Instruction:
    item = safe_instruction()
    item.dose = Dose(raw_value=value, raw_unit=unit)
    return item


def test_teachback_rejects_wrong_dose_that_contains_expected_digits() -> None:
    # Regression: "10" used to be satisfied by "100" via substring matching.
    result = evaluate_teachback(
        [_dose_only("10")], set(), "lisinopril 100 mg once a day in the morning"
    )
    assert {f.category: f.result for f in result.findings}["dose"] == "missing"


def test_teachback_single_digit_dose_is_not_ignored() -> None:
    # Regression: single-character tokens were dropped, so "5 mg" only required "mg".
    wrong = evaluate_teachback([_dose_only("5")], set(), "lisinopril mg once a day morning")
    assert {f.category: f.result for f in wrong.findings}["dose"] == "missing"
    right = evaluate_teachback([_dose_only("5")], set(), "lisinopril 5 mg once a day morning.")
    assert {f.category: f.result for f in right.findings}["dose"] == "correct"


def test_teachback_accepts_decimal_dose_and_trailing_period() -> None:
    result = evaluate_teachback([_dose_only("2.5")], set(), "I take lisinopril 2.5 mg.")
    assert {f.category: f.result for f in result.findings}["dose"] == "correct"
    wrong = evaluate_teachback([_dose_only("2.5")], set(), "I take lisinopril 25 mg.")
    assert {f.category: f.result for f in wrong.findings}["dose"] == "missing"
