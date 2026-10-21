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
