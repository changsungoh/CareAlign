import asyncio

import pytest

from app.models.schemas import (
    CareDocument,
    Dose,
    Frequency,
    Instruction,
    MedicationIdentity,
    PatternType,
    ValidationStatus,
)
from app.services import extraction
from app.services.evidence import has_unsupported_script
from app.services.teachback import evaluate_teachback


@pytest.mark.parametrize(
    "text",
    [
        "Take acetaminophen 500 mg by mouth twice a day.",
        "Levothyroxine 100 µg every morning",  # micro sign
        "Levothyroxine 100 μg every morning",  # Greek mu
        "Continue the β-blocker metoprolol 25 mg",
        "Prescription from the café clinic, 10 mg daily",  # accented Latin letters
        "ＴＡＫＥ ５ ｍｇ",  # full-width Latin and digits normalise to ASCII
        "10 / 20 - 30 (mg) ; 2x",
        "",
    ],
)
def test_latin_text_is_supported(text: str) -> None:
    assert not has_unsupported_script(text)


@pytest.mark.parametrize(
    "text",
    [
        "아세트아미노펜 500 mg 필요시 복용",  # Hangul
        "Принимать ацетаминофен 500 mg",  # Cyrillic
        "每日一次 500 mg",  # Han
        "Take 5 mg 필요시",  # one foreign word is enough
    ],
)
def test_other_scripts_are_unsupported(text: str) -> None:
    assert has_unsupported_script(text)


def _provider_item(text: str, **overrides) -> dict:
    item = {
        "raw_name": "acetaminophen",
        "dose": "500",
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
    item.update(overrides)
    return item


def _extract(monkeypatch, text: str, **overrides) -> list[ValidationStatus]:
    async def provider(document, usage_callback=None):
        return [_provider_item(text, **overrides)]

    monkeypatch.setattr(extraction, "_call_anthropic", provider)
    document = CareDocument(
        document_id="d1", document_type="note", document_date="2026-01-01", raw_text=text
    )
    result = asyncio.run(extraction.extract_document(document, False))
    return [item.validation_status for item in result]


def test_english_control_is_still_validated(monkeypatch) -> None:
    statuses = _extract(monkeypatch, "Take acetaminophen 500 mg once a day")
    assert statuses == [ValidationStatus.VALIDATED]


@pytest.mark.parametrize(
    "text",
    [
        "아세트아미노펜 500 mg 통증이 있을 때 필요시 복용",  # as needed, labelled fixed
        "아세트아미노펜 500 mg 격일로 복용",  # every other day, labelled once a day
        "Принимать ацетаминофен 500 mg при необходимости",
    ],
)
def test_non_english_evidence_is_never_auto_validated(monkeypatch, text: str) -> None:
    # Regression: the English safety nets cannot read these, so a fixed-schedule mislabel used
    # to end "validated".
    assert _extract(monkeypatch, text) == [ValidationStatus.NEEDS_REVIEW]


def _instruction(name: str, evidence: str, status: ValidationStatus) -> Instruction:
    return Instruction(
        instruction_id="i1",
        document_id="d1",
        medication=MedicationIdentity(raw_name=name, normalized_id="x"),
        dose=Dose(raw_value="10", raw_unit="mg"),
        frequency=Frequency(
            pattern_type=PatternType.FIXED, times_per_day=1, raw_expression="하루 한 번"
        ),
        evidence_span=evidence,
        validation_status=status,
    )


def test_teachback_never_marks_a_non_latin_expected_value_correct() -> None:
    # A Korean source value has no comparable tokens, so it must read "missing", not "correct".
    instruction = _instruction(
        "리시노프릴", "리시노프릴 10 mg 하루 한 번", ValidationStatus.VALIDATED
    )
    result = evaluate_teachback([instruction], set(), "리시노프릴 하루 한 번 먹어요")
    outcomes = {f.category: f.result for f in result.findings}
    assert outcomes["medication"] == "missing"
    assert outcomes["frequency"] == "missing"
    assert result.needs_human_review


def test_teachback_excludes_instructions_that_need_review() -> None:
    instruction = _instruction("리시노프릴", "리시노프릴 10 mg", ValidationStatus.NEEDS_REVIEW)
    result = evaluate_teachback([instruction], set(), "anything")
    assert result.checklist == []
    assert result.needs_human_review
