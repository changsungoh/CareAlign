"""Deterministic robustness gates for atypical schedules and field/evidence mismatches.

No LLM is called. Each case supplies the structured output a provider *might* return, including
dangerous mistakes (PRN labelled as fixed, a dose that contradicts its own quote), and asserts that
the extraction pipeline never leaves an unsafe item ``validated`` while still validating
correctly extracted items with varied wording.

Gates (declared before the first run):
- unsafe_validated == 0 across atypical_pattern, mislabelled_schedule and field_mismatch
- benign_false_downgrade_rate <= 0.10 on benign_variation

The cases are synthetic and author-labelled; this is engineering evidence, not clinical validation.
"""

# ruff: noqa: E402

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.schemas import CareDocument
from app.services import extraction

DATASET = Path(__file__).parent / "cases" / "atypical-v1.jsonl"
RESULTS = Path(__file__).parent / "results" / "atypical-v1.json"
EXPECTED_GROUPS = {
    "atypical_pattern": 8,
    "mislabelled_schedule": 8,
    "field_mismatch": 10,
    "benign_variation": 14,
}
UNSAFE_GROUPS = ("atypical_pattern", "mislabelled_schedule", "field_mismatch")
MAX_BENIGN_FALSE_DOWNGRADE = 0.10


def provider_item(case: dict) -> dict:
    item = {
        "raw_name": case["drug"],
        "dose": None,
        "unit": None,
        "pattern_type": "unsupported",
        "times_per_day": None,
        "interval_hours": None,
        "raw_frequency": "as written",
        "timing": [],
        "route": None,
        "duration": None,
        "action": None,
        "warning": None,
        "evidence_span": case["text"],
    }
    item.update(case["provider"])
    return item


async def run_case(case: dict) -> list[str]:
    async def fake_provider(document, usage_callback=None):
        return [provider_item(case)]

    original = extraction._call_anthropic
    extraction._call_anthropic = fake_provider
    try:
        document = CareDocument(
            document_id="eval",
            document_type="synthetic",
            document_date=date(2026, 9, 1),
            raw_text=case["text"],
        )
        instructions = await extraction.extract_document(document, False)
    finally:
        extraction._call_anthropic = original
    return [item.validation_status.value for item in instructions]


async def evaluate() -> dict:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["metric_group"]] = counts.get(case["metric_group"], 0) + 1
    if counts != EXPECTED_GROUPS:
        raise RuntimeError(f"Atypical dataset contract failed: {counts}")

    unsafe_validated = []
    benign_downgraded = []
    unexpected = []
    per_group = {group: {"cases": n, "passed": 0} for group, n in counts.items()}
    for case in cases:
        statuses = await run_case(case)
        # An instruction that disappears entirely would also be a silent loss.
        ok = len(statuses) == 1 and statuses[0] in case["expect"]
        if ok:
            per_group[case["metric_group"]]["passed"] += 1
            continue
        record = {
            "id": case["id"],
            "note": case["note"],
            "got": statuses,
            "expected": case["expect"],
        }
        unexpected.append(record)
        if case["metric_group"] in UNSAFE_GROUPS and "validated" in statuses:
            unsafe_validated.append(record)
        if case["metric_group"] == "benign_variation":
            benign_downgraded.append(record)

    benign_rate = len(benign_downgraded) / counts["benign_variation"]
    report = {
        "evaluation_type": "deterministic_atypical_robustness",
        "disclaimer": (
            "No LLM was called. Provider outputs are author-written simulations; results are "
            "synthetic engineering evidence, not independent review or clinical validation."
        ),
        "cases": len(cases),
        "groups": per_group,
        "metrics": {
            "unsafe_validated": len(unsafe_validated),
            "benign_false_downgrade_rate": round(benign_rate, 4),
            "llm_calls": 0,
        },
        "failures": unexpected,
        "gates": {
            "unsafe_validated_equals_zero": not unsafe_validated,
            "benign_false_downgrade_within_limit": benign_rate <= MAX_BENIGN_FALSE_DOWNGRADE,
        },
    }
    report["gates_passed"] = all(report["gates"].values())
    return report


if __name__ == "__main__":
    result = asyncio.run(evaluate())
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["gates_passed"] else 1)
