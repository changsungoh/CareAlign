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


def test_redundant_daily_interval_metadata_does_not_create_frequency_conflict() -> None:
    left = instruction("a", "old", 1)
    right = instruction("b", "new", 1)
    right.frequency = Frequency(
        pattern_type=PatternType.FIXED,
        times_per_day=1,
        interval_hours=24,
        raw_expression="once a day in the morning",
    )

    assert detect_conflicts([left, right], ["old", "new"]) == []


def test_q24h_and_once_daily_are_equivalent() -> None:
    left = instruction("a", "old", 1)
    right = instruction("b", "new", 1)
    right.frequency = Frequency(
        pattern_type=PatternType.INTERVAL,
        interval_hours=24,
        raw_expression="every 24 hours",
    )

    assert detect_conflicts([left, right], ["old", "new"]) == []


def test_longitudinal_frequency_alerts_are_collapsed() -> None:
    conflicts = detect_conflicts(
        [instruction("a", "first", 2), instruction("b", "second", 1), instruction("c", "third", 3)],
        ["first", "second", "third"],
    )
    assert len(conflicts) == 1
    assert conflicts[0].document_ids == ["first", "second", "third"]
    assert "first → second" in conflicts[0].summary
    assert "second → third" in conflicts[0].summary


def test_missing_middle_document_yields_one_longitudinal_omission() -> None:
    conflicts = detect_conflicts(
        [instruction("a", "first", 1), instruction("c", "third", 1)],
        ["first", "second", "third"],
    )
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "possible_omission"


def _split_dose(identifier: str, document: str, dose: str | None) -> Instruction:
    item = instruction(identifier, document, 2)
    item.dose = Dose(raw_value=dose, raw_unit="mg") if dose else None
    return item


def test_same_document_entries_are_not_compared_with_each_other() -> None:
    # 500 mg morning + 1000 mg evening in both records must not produce a flag.
    conflicts = detect_conflicts(
        [
            _split_dose("a1", "old", "500"),
            _split_dose("a2", "old", "1000"),
            _split_dose("b1", "new", "500"),
            _split_dose("b2", "new", "1000"),
        ],
        ["old", "new"],
    )
    assert conflicts == []


def test_changed_split_regimen_is_still_flagged() -> None:
    conflicts = detect_conflicts(
        [
            _split_dose("a1", "old", "500"),
            _split_dose("a2", "old", "1000"),
            _split_dose("b1", "new", "500"),
            _split_dose("b2", "new", "500"),
        ],
        ["old", "new"],
    )
    assert [c.conflict_type for c in conflicts] == ["dose_difference"]


def test_dose_that_disappears_is_never_silent() -> None:
    conflicts = detect_conflicts(
        [_split_dose("a", "old", "500"), _split_dose("b", "new", None)], ["old", "new"]
    )
    assert [c.conflict_type for c in conflicts] == ["dose_difference"]
    assert "only one of the two records" in conflicts[0].summary


def test_identical_non_mass_dose_is_not_flagged() -> None:
    old, new = _split_dose("a", "old", None), _split_dose("b", "new", None)
    for item in (old, new):
        item.dose = Dose(raw_value="1", raw_unit="tablet")
    assert detect_conflicts([old, new], ["old", "new"]) == []


def _kind(
    identifier: str,
    document: str,
    pattern: PatternType,
    *,
    times: int | None = None,
    interval: int | None = None,
    timing: list[str] | None = None,
) -> Instruction:
    from app.models.schemas import Timing

    return Instruction(
        instruction_id=identifier,
        document_id=document,
        medication=MedicationIdentity(raw_name="acetaminophen", normalized_id="acetaminophen"),
        dose=Dose(raw_value="500", raw_unit="mg"),
        frequency=Frequency(
            pattern_type=pattern,
            times_per_day=times,
            interval_hours=interval,
            raw_expression="as written",
        ),
        timing=Timing(values=timing or [], raw_expression=", ".join(timing or []) or None),
        evidence_span="acetaminophen 500 mg",
        validation_status=ValidationStatus.VALIDATED,
    )


def _types(old: Instruction, new: Instruction) -> list[str]:
    return [c.conflict_type.value for c in detect_conflicts([old, new], ["old", "new"])]


def test_scheduled_to_as_needed_is_a_frequency_difference() -> None:
    old = _kind("a", "old", PatternType.FIXED, times=2)
    new = _kind("b", "new", PatternType.PRN)
    assert _types(old, new) == ["frequency_difference"]
    reverse_old = new.model_copy(update={"document_id": "old"})
    reverse_new = old.model_copy(update={"document_id": "new"})
    assert _types(reverse_old, reverse_new) == ["frequency_difference"]


def test_scheduled_to_taper_and_every_other_day_are_flagged() -> None:
    old = _kind("a", "old", PatternType.FIXED, times=1)
    assert _types(old, _kind("b", "new", PatternType.TAPER)) == ["frequency_difference"]
    assert _types(old, _kind("c", "new", PatternType.EVERY_OTHER_DAY)) == ["frequency_difference"]


def test_same_unsupported_or_same_kind_is_not_reported_as_a_change() -> None:
    fixed = _kind("a", "old", PatternType.FIXED, times=1)
    # The model could not classify the schedule: that says nothing about a change.
    assert _types(fixed, _kind("b", "new", PatternType.UNSUPPORTED)) == []
    assert _types(_kind("c", "old", PatternType.PRN), _kind("d", "new", PatternType.PRN)) == []


def test_as_needed_interval_change_is_flagged_but_missing_interval_is_not() -> None:
    six = _kind("a", "old", PatternType.PRN, interval=6)
    eight = _kind("b", "new", PatternType.PRN, interval=8)
    assert _types(six, eight) == ["frequency_difference"]
    assert _types(six, _kind("c", "new", PatternType.PRN)) == []


def test_timing_change_is_flagged() -> None:
    old = _kind("a", "old", PatternType.FIXED, times=1, timing=["morning"])
    new = _kind("b", "new", PatternType.FIXED, times=1, timing=["at bedtime"])
    conflicts = detect_conflicts([old, new], ["old", "new"])
    assert [c.conflict_type.value for c in conflicts] == ["timing_difference"]
    assert conflicts[0].status == "validated"


def test_equivalent_timing_spellings_are_not_a_change() -> None:
    old = _kind("a", "old", PatternType.FIXED, times=1, timing=["bedtime"])
    new = _kind("b", "new", PatternType.FIXED, times=1, timing=["at night"])
    assert _types(old, new) == []


def test_timing_present_in_only_one_record_is_not_a_change() -> None:
    old = _kind("a", "old", PatternType.FIXED, times=1, timing=["morning"])
    new = _kind("b", "new", PatternType.FIXED, times=1)
    assert _types(old, new) == []


def test_unrecognised_timing_spelling_goes_to_review_not_validated() -> None:
    old = _kind("a", "old", PatternType.FIXED, times=1, timing=["after lunch"])
    new = _kind("b", "new", PatternType.FIXED, times=1, timing=["after dinner"])
    conflicts = detect_conflicts([old, new], ["old", "new"])
    assert [c.conflict_type.value for c in conflicts] == ["timing_difference"]
    assert conflicts[0].status == "needs_review"


def _course(identifier: str, document: str, duration: str | None) -> Instruction:
    item = _kind(identifier, document, PatternType.FIXED, times=2)
    item.duration = duration
    return item


def test_different_course_lengths_are_a_duration_difference() -> None:
    old, new = _course("a", "old", "for 7 days"), _course("b", "new", "for 10 days")
    conflicts = detect_conflicts([old, new], ["old", "new"])
    assert [c.conflict_type.value for c in conflicts] == ["duration_difference"]
    assert conflicts[0].status == "validated"
    assert "7 days" in conflicts[0].summary and "10 days" in conflicts[0].summary


def test_equivalent_course_lengths_are_not_a_change() -> None:
    cases = [
        ("for 7 days", "1 week"),
        ("x 7 days", "one week"),
        ("1 month", "30 days"),
        ("1 month", "4 weeks"),  # month length varies, so a two-day gap is tolerated
    ]
    for earlier, later in cases:
        assert _types(_course("a", "old", earlier), _course("b", "new", later)) == [], (
            earlier,
            later,
        )


def test_a_month_is_not_the_same_as_five_weeks() -> None:
    assert _types(_course("a", "old", "1 month"), _course("b", "new", "5 weeks")) == [
        "duration_difference"
    ]


def test_finite_course_becoming_ongoing_is_flagged() -> None:
    assert _types(_course("a", "old", "7 days"), _course("b", "new", "ongoing")) == [
        "duration_difference"
    ]
    assert _types(_course("a", "old", "long-term"), _course("b", "new", "2 weeks")) == [
        "duration_difference"
    ]


def test_duration_stated_in_only_one_record_is_not_a_change() -> None:
    assert _types(_course("a", "old", "7 days"), _course("b", "new", None)) == []
    assert _types(_course("a", "old", None), _course("b", "new", "ongoing")) == []


def test_unparseable_or_frequency_wording_is_never_read_as_a_course_length() -> None:
    # "once a week" and "every 2 days" say how often, not how long.
    assert _types(_course("a", "old", "7 days"), _course("b", "new", "once a week")) == []
    assert _types(_course("a", "old", "until follow-up"), _course("b", "new", "as directed")) == []
    assert _types(_course("a", "old", "every 2 days"), _course("b", "new", "7 days")) == []
