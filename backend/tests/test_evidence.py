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
