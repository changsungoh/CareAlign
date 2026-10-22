"""Run the atypical-schedule instruction texts through the configured LIVE provider.

This needs a real provider key and spends money, so it requires --confirm-cost and explicit,
current per-million-token rates (see LIVE_EVALUATION.md). It measures what the simulated suite
cannot: whether the real model labels PRN/taper/non-daily text correctly on its own, how often the
field/evidence safety net has to step in, and how often correct, plainly worded instructions are
wrongly downgraded.

Gates (declared before any live run):
- no instruction from a PRN/taper/non-daily/range/conditional text may end ``validated``
- at most 10% of plainly worded, correctly readable instructions may be downgraded
- every case must complete (provider failures are kept, never dropped)

Provider-injected errors (a wrong dose on purpose) cannot be reproduced against a real model; those
stay covered by evaluate_atypical.py. The text labels are the author's, not independent.
"""

# ruff: noqa: E402

import argparse
import asyncio
import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import atypical_reference as reference

from app.core.config import settings
from app.models.schemas import CareDocument
from app.services import extraction

RESULTS = Path(__file__).parent / "results" / "atypical-live-v1.json"
UNSAFE_SCHEDULES = {"prn", "taper", "non_daily", "range", "conditional"}
MAX_PLAIN_DOWNGRADE = 0.10


def _same_number(left, right) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except InvalidOperation:
        return False


async def run(input_rate: Decimal, output_rate: Decimal) -> dict:
    if not settings.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY is required for the live evaluation.")
    if input_rate <= 0 or output_rate <= 0:
        raise SystemExit("Current positive provider input/output rates are required.")
    settings.demo_mode = False
    texts = reference.unique_texts()
    usage = {"input_tokens": 0, "output_tokens": 0}

    def record(raw: dict) -> None:
        usage["input_tokens"] += int(raw.get("input_tokens", 0) or 0)
        usage["output_tokens"] += int(raw.get("output_tokens", 0) or 0)

    unsafe_total = unsafe_validated = model_correct_pattern = safety_net_caught = 0
    plain_total = plain_downgraded = 0
    dose_checked = dose_correct = freq_checked = freq_correct = 0
    failures: list[dict] = []
    detail: list[dict] = []

    for case in texts:
        ref = reference.author_reference(case)
        document = CareDocument(
            document_id="live",
            document_type="synthetic",
            document_date=date(2026, 9, 1),
            raw_text=case["text"],
        )
        try:
            items = await extraction.extract_document(document, False, record)
        except Exception as error:  # noqa: BLE001 - keep every provider/schema failure
            failures.append({"id": case["id"], "error_type": type(error).__name__})
            continue
        statuses = [i.validation_status.value for i in items]
        patterns = [i.frequency.pattern_type.value if i.frequency else None for i in items]
        detail.append({"id": case["id"], "schedule_reference": ref["schedule_type"],
                       "model_patterns": patterns, "statuses": statuses})  # fmt: skip
        if ref["schedule_type"] in UNSAFE_SCHEDULES or ref["schedule_type"] == "other":
            unsafe_total += 1
            if "validated" in statuses:
                unsafe_validated += 1
            if items and all(p not in {"fixed", "interval"} for p in patterns):
                model_correct_pattern += 1
            elif items and "validated" not in statuses:
                safety_net_caught += 1
        else:
            plain_total += 1
            if not items or any(s != "validated" for s in statuses):
                plain_downgraded += 1
            if items and "dose_value" in ref and ref["dose_value"] is not None:
                dose_checked += 1
                dose = items[0].dose
                dose_correct += int(bool(dose and _same_number(dose.raw_value, ref["dose_value"])))
            if items and (ref.get("times_per_day") or ref.get("interval_hours")):
                freq_checked += 1
                frequency = items[0].frequency
                times = frequency.times_per_day if frequency else None
                hours = frequency.interval_hours if frequency else None
                want_times = ref.get("times_per_day") or (24 // ref["interval_hours"])
                got_times = times or (24 // hours if hours and 24 % hours == 0 else None)
                freq_correct += int(got_times == want_times)

    total_cost = (
        Decimal(usage["input_tokens"]) * input_rate + Decimal(usage["output_tokens"]) * output_rate
    ) / Decimal(1_000_000)
    downgrade_rate = plain_downgraded / plain_total if plain_total else 1.0
    completed = len(detail)
    report = {
        "evaluation_type": "live_llm_atypical_schedule_evaluation",
        "disclaimer": (
            "Synthetic, author-labelled engineering evaluation; not independent review or clinical "
            "validation. Provider-injected errors are covered by the simulated suite instead."
        ),
        "evaluated_at": datetime.now(UTC).isoformat(),
        "versions": {
            "prompt": settings.prompt_version,
            "rules": settings.rules_version,
            "model": settings.llm_model,
        },
        "case_accounting": {
            "unique_texts": len(texts),
            "completed": completed,
            "failed_cases": failures,
        },
        "usage": {
            **usage,
            "input_cost_per_million_usd": str(input_rate),
            "output_cost_per_million_usd": str(output_rate),
            "estimated_cost_usd": str(total_cost.quantize(Decimal("0.000001"))),
        },
        "metrics": {
            "unsafe_texts": unsafe_total,
            "unsafe_texts_ending_validated": unsafe_validated,
            "model_labelled_non_scheduled_on_its_own": model_correct_pattern,
            "caught_only_by_safety_net": safety_net_caught,
            "plain_texts": plain_total,
            "plain_false_downgrade_rate": round(downgrade_rate, 4),
            "dose_exact_match": f"{dose_correct}/{dose_checked}",
            "frequency_match": f"{freq_correct}/{freq_checked}",
        },
        "per_text": detail,
    }
    report["live_gates_passed"] = bool(
        completed == len(texts) and unsafe_validated == 0 and downgrade_rate <= MAX_PLAIN_DOWNGRADE
    )
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
        raise SystemExit("Refusing to call a paid provider without --confirm-cost.")
    result = asyncio.run(
        run(arguments.input_cost_per_million_usd, arguments.output_cost_per_million_usd)
    )
    print(json.dumps({k: v for k, v in result.items() if k != "per_text"}, indent=2))
    raise SystemExit(0 if result["live_gates_passed"] else 1)
