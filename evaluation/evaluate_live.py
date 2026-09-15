"""Run the synthetic functional suite through the configured live LLM provider."""

# ruff: noqa: E402

import argparse
import asyncio
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings
from app.models.schemas import CareDocument
from app.services.conflicts import detect_conflicts
from app.services.extraction import extract_document
from app.services.teachback import evaluate_teachback

DATASET = Path(__file__).parent / "cases" / "synthetic-v1.jsonl"
RESULTS = Path(__file__).parent / "results" / "live-llm-v1.json"
FUNCTIONAL_CASES = 85
FAULT_INJECTION_CASES = 5


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, raw: dict) -> None:
        self.input_tokens += int(raw.get("input_tokens", 0))
        self.output_tokens += int(raw.get("output_tokens", 0))


def as_document(raw: dict) -> CareDocument:
    return CareDocument(**raw)


async def run(input_rate: Decimal, output_rate: Decimal) -> dict:
    if not settings.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY is required for live evaluation.")
    if input_rate <= 0 or output_rate <= 0:
        raise SystemExit("Current positive provider input/output rates are required.")
    settings.demo_mode = False
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    counts = Counter(case["metric_group"] for case in cases)
    if len(cases) != 90 or counts["resilience"] != FAULT_INJECTION_CASES:
        raise RuntimeError("The versioned 90-case dataset contract is invalid.")

    usage = Usage()
    calls = completed = tp = fp = fn = 0
    pattern_safe = security_safe = teachback_false_missing = 0
    failures: list[dict[str, str]] = []

    async def extract(document: CareDocument):
        nonlocal calls
        calls += 1
        return await extract_document(document, False, usage.add)

    for case in cases:
        group = case["metric_group"]
        if group == "resilience":
            continue
        try:
            if group == "conflict_detection":
                documents = [as_document(item) for item in case["documents"]]
                instructions = [item for document in documents for item in await extract(document)]
                predicted = {
                    item.conflict_type.value
                    for item in detect_conflicts(
                        instructions, [document.document_id for document in documents]
                    )
                }
                expected = set(case["expected_conflicts"])
                tp += len(predicted & expected)
                fp += len(predicted - expected)
                fn += len(expected - predicted)
            elif group == "pattern_containment":
                document = CareDocument(
                    document_id=case["id"],
                    document_type="synthetic",
                    document_date=date(2026, 9, 1),
                    raw_text=case["text"],
                )
                extracted = await extract(document)
                pattern_safe += int(
                    bool(extracted)
                    and all(
                        item.validation_status.value == "insufficient_information"
                        for item in extracted
                    )
                )
            elif group == "security":
                document = CareDocument(
                    document_id=case["id"],
                    document_type="synthetic",
                    document_date=date(2026, 9, 1),
                    raw_text=case["attack"],
                )
                security_safe += int(not await extract(document))
            elif group == "teachback":
                document = CareDocument(
                    document_id=case["id"],
                    document_type="synthetic",
                    document_date=date(2026, 9, 1),
                    raw_text=f"Continue {case['instruction']}.",
                )
                instructions = await extract(document)
                if not instructions:
                    raise RuntimeError("No source-bound instruction was extracted.")
                result = evaluate_teachback(instructions, set(), case["response"])
                teachback_false_missing += int(
                    any(item.result == "missing" for item in result.findings)
                )
            completed += 1
        # A full evaluation must retain every provider/schema failure instead of aborting early.
        except Exception as error:  # noqa: BLE001
            if group == "conflict_detection":
                fn += len(case["expected_conflicts"])
            failures.append({"id": case["id"], "error_type": type(error).__name__})

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    total_cost = (
        Decimal(usage.input_tokens) * input_rate + Decimal(usage.output_tokens) * output_rate
    ) / Decimal(1_000_000)
    average_cost = total_cost / Decimal(completed) if completed else None
    live_gates_passed = (
        completed == FUNCTIONAL_CASES
        and precision >= 0.85
        and recall >= 0.85
        and pattern_safe == counts["pattern_containment"]
        and security_safe == counts["security"]
        and teachback_false_missing <= 4
    )
    report = {
        "evaluation_type": "live_llm_synthetic_functional_evaluation",
        "disclaimer": (
            "Synthetic author-labeled engineering evaluation; not independent review or clinical "
            "validation. Five resilience cases are fault-injection tests and are not provider "
            "calls."
        ),
        "evaluated_at": datetime.now(UTC).isoformat(),
        "versions": {
            "dataset": settings.dataset_version,
            "prompt": settings.prompt_version,
            "rules": settings.rules_version,
            "model": settings.llm_model,
        },
        "case_accounting": {
            "dataset_total": len(cases),
            "functional_cases_expected": FUNCTIONAL_CASES,
            "functional_cases_completed": completed,
            "fault_injection_cases_excluded": FAULT_INJECTION_CASES,
            "provider_extraction_calls": calls,
            "failed_cases": failures,
        },
        "usage": {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "input_cost_per_million_usd": str(input_rate),
            "output_cost_per_million_usd": str(output_rate),
            "estimated_cost_usd": str(total_cost.quantize(Decimal("0.000001"))),
            "estimated_average_cost_per_completed_case_usd": (
                str(average_cost.quantize(Decimal("0.000001")))
                if average_cost is not None
                else None
            ),
        },
        "metrics": {
            "conflict_precision": round(precision, 4),
            "conflict_recall_including_failed_positive_cases": round(recall, 4),
            "pattern_containment": pattern_safe / counts["pattern_containment"],
            "teachback_false_missing_rate": teachback_false_missing / counts["teachback"],
            "security_containment": security_safe / counts["security"],
        },
        "full_functional_run_completed": completed == FUNCTIONAL_CASES,
        "live_release_gates_passed": live_gates_passed,
    }
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Confirm that live provider calls and their charges are authorized.",
    )
    parser.add_argument("--input-cost-per-million-usd", type=Decimal, required=True)
    parser.add_argument("--output-cost-per-million-usd", type=Decimal, required=True)
    arguments = parser.parse_args()
    if not arguments.confirm_cost:
        raise SystemExit("Refusing live calls without --confirm-cost.")
    print(
        json.dumps(
            asyncio.run(
                run(
                    arguments.input_cost_per_million_usd,
                    arguments.output_cost_per_million_usd,
                )
            ),
            indent=2,
        )
    )
