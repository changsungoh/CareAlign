"""Deterministic two-record gates for schedule, as-needed interval, timing and duration changes.

No LLM is called. Each case gives the structured output a provider might return for an earlier and
a later record; the real extraction pipeline and conflict engine decide what is flagged.

Gates (declared before the first run): conflict-type precision and recall of at least 0.95 across
the 19 cases. The cases are author-written and author-labelled: engineering evidence only.
"""

# ruff: noqa: E402

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.models.schemas import CareDocument
from app.services import extraction
from app.services.conflicts import detect_conflicts

DATASET = Path(__file__).parent / "cases" / "longitudinal-v1.jsonl"
RESULTS = Path(__file__).parent / "results" / "longitudinal-v1.json"
EXPECTED_CASES = 19
MIN_PRECISION = MIN_RECALL = 0.95


def _item(drug: str, doc: dict) -> dict:
    base = {
        "raw_name": drug,
        "dose": None,
        "unit": None,
        "pattern_type": "fixed",
        "times_per_day": None,
        "interval_hours": None,
        "raw_frequency": "as written",
        "timing": [],
        "route": None,
        "duration": None,
        "action": None,
        "warning": None,
        "evidence_span": doc["text"],
    }
    base.update(doc["provider"])
    return base


async def evaluate() -> dict:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    if len(cases) != EXPECTED_CASES:
        raise RuntimeError(f"Longitudinal dataset contract failed: {len(cases)} cases")
    original = extraction._call_anthropic
    tp = fp = fn = 0
    failures = []
    try:
        for case in cases:
            by_text = {doc["text"]: _item(case["drug"], doc) for doc in case["docs"]}

            async def provider(document, usage_callback=None, _by_text=by_text):
                return [_by_text[document.raw_text]]

            extraction._call_anthropic = provider
            documents = [
                CareDocument(
                    document_id=name,
                    document_type="synthetic",
                    document_date=date(2026, month, 1),
                    raw_text=doc["text"],
                )
                for name, month, doc in zip(("old", "new"), (8, 9), case["docs"], strict=True)
            ]
            instructions = [
                i for d in documents for i in await extraction.extract_document(d, False)
            ]
            predicted = {
                c.conflict_type.value for c in detect_conflicts(instructions, ["old", "new"])
            }
            expected = set(case["expected_conflicts"])
            tp += len(predicted & expected)
            fp += len(predicted - expected)
            fn += len(expected - predicted)
            if predicted != expected:
                failures.append(
                    {"id": case["id"], "note": case["note"], "predicted": sorted(predicted),
                     "expected": sorted(expected)}
                )  # fmt: skip
    finally:
        extraction._call_anthropic = original
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "evaluation_type": "deterministic_longitudinal_changes",
        "disclaimer": (
            "No LLM was called. Provider outputs are author-written simulations; synthetic "
            "engineering evidence, not independent review or clinical validation."
        ),
        "cases": len(cases),
        "metrics": {"precision": round(precision, 4), "recall": round(recall, 4), "llm_calls": 0},
        "failures": failures,
        "gates_passed": precision >= MIN_PRECISION and recall >= MIN_RECALL,
    }


if __name__ == "__main__":
    result = asyncio.run(evaluate())
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["gates_passed"] else 1)
