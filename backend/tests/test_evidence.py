from app.services.evidence import normalize_evidence, verify_evidence


def test_normalization_handles_case_whitespace_and_terminal_punctuation() -> None:
    assert normalize_evidence("  Take  ONE\nTablet. ") == "take one tablet"


def test_normalized_substring_is_validated() -> None:
    result = verify_evidence(
        "Instructions:\nTake one tablet every morning.",
        "take  one tablet every morning",
    )
    assert result.status == "validated"


def test_nonexistent_evidence_is_rejected() -> None:
    result = verify_evidence("Take one tablet every morning.", "Stop all medication")
    assert result.status == "invalid_evidence"


def test_dose_must_appear_in_quoted_evidence() -> None:
    from app.services.evidence import dose_supported_by_evidence

    quote = "Take metformin 500 mg twice a day"
    assert dose_supported_by_evidence(quote, "500", "mg")
    assert dose_supported_by_evidence(quote, "500.0", "MG")
    assert not dose_supported_by_evidence(quote, "50", "mg")  # right quote, wrong value
    assert not dose_supported_by_evidence(quote, "500", "mcg")
    assert dose_supported_by_evidence("levothyroxine 100 µg daily", "100", "mcg")
    assert dose_supported_by_evidence("take 1,000 mg", "1000", "mg")
    assert dose_supported_by_evidence(quote, None, None)


def test_wrong_structured_dose_is_downgraded_to_needs_review(monkeypatch) -> None:
    import asyncio

    from app.models.schemas import CareDocument, ValidationStatus
    from app.services import extraction

    text = "Take metformin 500 mg twice a day"

    async def provider(document, usage_callback=None):
        return [
            {
                "raw_name": "metformin",
                "dose": "50",
                "unit": "mg",
                "pattern_type": "fixed",
                "times_per_day": 2,
                "interval_hours": None,
                "raw_frequency": "twice a day",
                "timing": [],
                "route": None,
                "duration": None,
                "action": None,
                "warning": None,
                "evidence_span": text,
            }
        ]

    monkeypatch.setattr(extraction, "_call_anthropic", provider)
    document = CareDocument(
        document_id="d1", document_type="note", document_date="2026-01-01", raw_text=text
    )
    result = asyncio.run(extraction.extract_document(document, False))
    assert result[0].validation_status == ValidationStatus.NEEDS_REVIEW


def _check(evidence, **kw):
    from app.services.evidence import field_contradictions

    base = dict(pattern_type="fixed", times_per_day=None, interval_hours=None,
                route_raw=None, action=None)  # fmt: skip
    return field_contradictions(evidence, **{**base, **kw})


def test_consistent_fields_raise_no_contradiction() -> None:
    quote = "Continue metoprolol tartrate 25 mg by mouth twice a day."
    assert _check(quote, times_per_day=2, route_raw="by mouth", action="continue") == ([], [])
    assert _check("take 5 mg every 8 hours", pattern_type="interval", interval_hours=8) == ([], [])
    assert _check("take 5 mg every 12 hours", times_per_day=2) == ([], [])
    assert _check("take 5 mg BID", times_per_day=2) == ([], [])
    assert _check("take 5 mg once daily at bedtime", times_per_day=1) == ([], [])
    assert _check("take 5 mg by mouth", route_raw="oral") == ([], [])  # alias of the same route


def test_wrong_frequency_in_quote_is_a_value_contradiction() -> None:
    _, values = _check("Take lisinopril 10 mg once a day", times_per_day=2)
    assert values and "times_per_day=2" in values[0]
    _, values = _check("Take lisinopril every 6 hours", pattern_type="interval", interval_hours=8)
    assert values and "interval_hours=8" in values[0]


def test_unmentioned_frequency_is_not_treated_as_contradiction() -> None:
    assert _check("Take lisinopril 10 mg in the morning", times_per_day=1) == ([], [])


def test_mislabelled_schedule_types_are_schedule_contradictions() -> None:
    for quote in (
        "Take ibuprofen 400 mg once a day as needed for pain",
        "Take prednisone 40 mg once a day, taper by 10 mg weekly",
        "Take warfarin 5 mg every other day",
    ):
        schedule, _ = _check(quote, times_per_day=1)
        assert schedule, quote
    # The same words are fine when the extractor already declared an unsupported pattern.
    assert _check("Take ibuprofen as needed", pattern_type="prn")[0] == []


def test_route_and_action_must_match_the_quote() -> None:
    _, values = _check("Take 5 mg by mouth", route_raw="intravenous")
    assert any("route" in v for v in values)
    _, values = _check("Stop atorvastatin 20 mg", action="continue")
    assert any("action" in v for v in values)
    assert _check("Discontinue atorvastatin 20 mg", action="stop") == ([], [])


def test_contradicted_frequency_downgrades_extraction(monkeypatch) -> None:
    import asyncio

    from app.models.schemas import CareDocument, ValidationStatus
    from app.services import extraction

    text = "Take ibuprofen 400 mg once a day as needed for pain"

    async def provider(document, usage_callback=None):
        return [
            {
                "raw_name": "ibuprofen",
                "dose": "400",
                "unit": "mg",
                "pattern_type": "fixed",
                "times_per_day": 1,
                "interval_hours": None,
                "raw_frequency": "once a day",
                "timing": [],
                "route": None,
                "duration": None,
                "action": None,
                "warning": None,
                "evidence_span": text,
            }
        ]

    monkeypatch.setattr(extraction, "_call_anthropic", provider)
    document = CareDocument(
        document_id="d1", document_type="note", document_date="2026-01-01", raw_text=text
    )
    result = asyncio.run(extraction.extract_document(document, False))
    assert result[0].validation_status == ValidationStatus.INSUFFICIENT_INFORMATION


def test_two_times_of_day_count_as_two_doses() -> None:
    assert _check("Take metformin 500 mg every morning and at bedtime", times_per_day=2) == ([], [])
    assert _check("Take metformin 500 mg every night at bedtime", times_per_day=1) == ([], [])
    assert _check("Take x 5 mg daily in the morning and evening", times_per_day=2) == ([], [])
    _, values = _check("Take x 5 mg every morning and at bedtime", times_per_day=1)
    assert values  # a real contradiction is still caught


def test_unrelated_sentences_do_not_relabel_the_schedule() -> None:
    quote = (
        "Take lisinopril 10 mg once a day. Check blood pressure weekly. Call your doctor if needed."
    )
    assert _check(quote, times_per_day=1) == ([], [])


def test_real_weekly_and_prn_dosing_phrases_are_still_flagged() -> None:
    for quote in (
        "Take methotrexate 15 mg once weekly",
        "Take methotrexate 15 mg once a week",
        "Take ibuprofen 400 mg if needed for pain",
    ):
        assert _check(quote, times_per_day=1)[0], quote
