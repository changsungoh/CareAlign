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
