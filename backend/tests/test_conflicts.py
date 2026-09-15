from app.models.schemas import (
    Dose,
    Frequency,
    Instruction,
    MedicationIdentity,
    PatternType,
    ValidationStatus,
)
from app.services.conflicts import detect_conflicts


def instruction(identifier: str, document: str, frequency: int) -> Instruction:
    return Instruction(
        instruction_id=identifier,
        document_id=document,
        medication=MedicationIdentity(
            raw_name="metoprolol tartrate", normalized_id="metoprolol_tartrate_ir"
        ),
        dose=Dose(raw_value="25", raw_unit="mg"),
        frequency=Frequency(
            pattern_type=PatternType.FIXED,
            times_per_day=frequency,
            raw_expression=f"{frequency} times a day",
        ),
        evidence_span=f"metoprolol tartrate 25 mg {frequency} times a day",
        validation_status=ValidationStatus.VALIDATED,
    )


def test_frequency_conflict_is_source_linked() -> None:
    conflicts = detect_conflicts(
        [instruction("a", "old", 2), instruction("b", "new", 1)], ["old", "new"]
    )
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "frequency_difference"
    assert len(conflicts[0].evidence_spans) == 2


def test_possible_omission_does_not_infer_stop() -> None:
    conflicts = detect_conflicts([instruction("a", "old", 1)], ["old", "new"])
    assert conflicts[0].conflict_type == "possible_omission"
    assert "intent is unknown" in conflicts[0].summary


def test_equivalent_mass_units_do_not_conflict() -> None:
    left = instruction("a", "old", 1)
    right = instruction("b", "new", 1)
    left.dose = Dose(raw_value="0.5", raw_unit="g")
    right.dose = Dose(raw_value="500", raw_unit="mg")
    assert detect_conflicts([left, right], ["old", "new"]) == []
