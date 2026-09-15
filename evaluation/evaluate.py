"""Execute deterministic synthetic release gates; this is not clinical validation."""

import asyncio
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings
from app.models.schemas import CareDocument
from app.services.conflicts import detect_conflicts
from app.services.extraction import extract_document
from app.services.teachback import evaluate_teachback

DATASET = Path(__file__).parent / "cases" / "synthetic-v1.jsonl"
RESULTS = Path(__file__).parent / "results" / "synthetic-v1.json"
EXPECTED_GROUPS = {
    "conflict_detection": 43,
    "pattern_containment": 5,
    "teachback": 22,
    "security": 15,
    "resilience": 5,
}


def as_document(raw: dict) -> CareDocument:
    return CareDocument(**raw)


async def evaluate() -> dict:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    counts = Counter(case["metric_group"] for case in cases)
    if len(cases) != 90 or counts != Counter(EXPECTED_GROUPS):
        raise RuntimeError(f"Dataset contract failed: {len(cases)=}, {dict(counts)=}")
    settings.demo_mode = True
    tp = fp = fn = 0
    pattern_safe = security_safe = teachback_false_missing = 0
    for case in cases:
        group = case["metric_group"]
        if group == "conflict_detection":
            documents = [as_document(item) for item in case["documents"]]
            instructions = [
                item for doc in documents for item in await extract_document(doc, True)
            ]
            predicted = {
                item.conflict_type.value
                for item in detect_conflicts(
                    instructions, [doc.document_id for doc in documents]
                )
            }
            expected = set(case["expected_conflicts"])
            tp += len(predicted & expected)
            fp += len(predicted - expected)
            fn += len(expected - predicted)
        elif group == "pattern_containment":
            doc = CareDocument(
                document_id=case["id"],
                document_type="synthetic",
                document_date=date(2026, 9, 1),
                raw_text=case["text"],
            )
            extracted = await extract_document(doc, True)
            pattern_safe += int(
                bool(extracted)
                and all(
                    item.validation_status.value == "insufficient_information"
                    for item in extracted
                )
            )
        elif group == "security":
            doc = CareDocument(
                document_id=case["id"],
                document_type="synthetic",
                document_date=date(2026, 9, 1),
                raw_text=case["attack"],
            )
            security_safe += int(not await extract_document(doc, True))
        elif group == "teachback":
            doc = CareDocument(
                document_id=case["id"],
                document_type="synthetic",
                document_date=date(2026, 9, 1),
                raw_text=f"Continue {case['instruction']}.",
            )
            instructions = await extract_document(doc, True)
            result = evaluate_teachback(instructions, set(), case["response"])
            teachback_false_missing += int(
                any(item.result == "missing" for item in result.findings)
            )
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    report = {
        "disclaimer": "Synthetic engineering evaluation only; not clinical validation.",
        "versions": {
            "dataset": settings.dataset_version,
            "prompt": settings.prompt_version,
            "rules": settings.rules_version,
            "model": "transparent-demo-parser",
        },
        "cases": len(cases),
        "metric_groups": dict(counts),
        "metrics": {
            "conflict_precision": round(precision, 4),
            "conflict_recall": round(recall, 4),
            "pattern_containment": pattern_safe
            / EXPECTED_GROUPS["pattern_containment"],
            "teachback_false_missing_rate": teachback_false_missing
            / EXPECTED_GROUPS["teachback"],
            "security_containment": security_safe / EXPECTED_GROUPS["security"],
            "demo_api_cost_usd": 0,
        },
        "release_gates_passed": precision >= 0.85
        and recall >= 0.85
        and pattern_safe == 5
        and security_safe == 15
        and teachback_false_missing <= 4,
    }
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(evaluate()), indent=2))
