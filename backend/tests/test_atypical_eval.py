import asyncio
import importlib.util
from pathlib import Path

EVALUATOR = Path(__file__).resolve().parents[2] / "evaluation" / "evaluate_atypical.py"


def _load():
    spec = importlib.util.spec_from_file_location("evaluate_atypical", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_atypical_robustness_gates_pass() -> None:
    report = asyncio.run(_load().evaluate())
    assert report["metrics"]["unsafe_validated"] == 0, report["failures"]
    assert report["gates_passed"], report["failures"]
    assert report["cases"] == 40


def test_evaluator_restores_the_real_provider() -> None:
    from app.services import extraction

    before = extraction._call_anthropic
    asyncio.run(_load().evaluate())
    assert extraction._call_anthropic is before


def test_live_evaluation_logic_with_a_faithful_fake_provider(monkeypatch, tmp_path) -> None:
    """The live script's accounting and gates work when the 'model' reads every text correctly."""
    import sys
    from decimal import Decimal

    from app.core.config import settings
    from app.services import extraction

    sys.path.insert(0, str(EVALUATOR.parent))
    spec = importlib.util.spec_from_file_location(
        "evaluate_atypical_live", EVALUATOR.parent / "evaluate_atypical_live.py"
    )
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)
    reference = live.reference
    by_text = {case["text"]: case for case in reference.unique_texts()}

    async def faithful(document, usage_callback=None):
        case = by_text[document.raw_text]
        ref = reference.author_reference(case)
        pattern = {
            "fixed_daily": "fixed",
            "non_daily": "every_other_day",
            "other": "unsupported",
        }.get(ref["schedule_type"], ref["schedule_type"])
        item = {
            "raw_name": case["drug"], "dose": ref.get("dose_value"), "unit": ref.get("dose_unit"),
            "pattern_type": pattern, "times_per_day": ref.get("times_per_day"),
            "interval_hours": ref.get("interval_hours"), "raw_frequency": "as written",
            "timing": [], "route": case["provider"].get("route"), "duration": None,
            "action": ref.get("action"), "warning": None, "evidence_span": case["text"],
        }  # fmt: skip
        if usage_callback:
            usage_callback({"input_tokens": 100, "output_tokens": 50})
        return [item]

    monkeypatch.setattr(extraction, "_call_anthropic", faithful)
    monkeypatch.setattr(settings, "anthropic_api_key", "synthetic-key")
    monkeypatch.setattr(live, "RESULTS", tmp_path / "live.json")
    report = asyncio.run(live.run(Decimal("1"), Decimal("5")))
    assert report["case_accounting"]["completed"] == 35
    assert report["metrics"]["unsafe_texts_ending_validated"] == 0
    assert report["metrics"]["plain_false_downgrade_rate"] <= 0.10
    assert report["usage"]["input_tokens"] == 3500
