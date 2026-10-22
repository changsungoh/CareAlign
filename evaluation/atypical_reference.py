"""Author reference labels for the atypical-schedule cases, shared by the reviewer packet and the
live evaluation. These are the *author's* labels: independent reviewers are asked to produce their
own, and disagreements are reported, never overwritten."""

import json
from pathlib import Path

DATASET = Path(__file__).parent / "cases" / "atypical-v1.jsonl"
SCHEDULE_TYPES = (
    "fixed_daily",
    "interval",
    "prn",
    "taper",
    "non_daily",
    "range",
    "conditional",
    "other",
)
_PATTERN_TO_SCHEDULE = {
    "fixed": "fixed_daily",
    "interval": "interval",
    "prn": "prn",
    "taper": "taper",
    "every_other_day": "non_daily",
    "conditional": "conditional",
    "range": "range",
    "unsupported": "other",
}
# Plain-text cases whose provider output in the simulation is deliberately wrong; the correct
# values are written out here from the text itself.
_PLAIN_REFERENCE = {
    "fld-01": ("500", "mg", 2, None, "oral", None),
    "fld-02": ("500", "mg", 2, None, "oral", None),
    "fld-03": ("10", "mg", 1, None, "oral", None),
    "fld-04": ("20", "mg", 2, None, "oral", None),
    "fld-05": ("50", "mg", 3, None, "oral", None),
    "fld-06": ("25", "mg", None, 12, "oral", None),
    "fld-07": ("10", "mg", 1, None, "oral", None),
    "fld-08": ("5", "mg", 1, None, "oral", None),
    "fld-09": ("20", "mg", 1, None, "oral", "stop"),
    "fld-10": ("50", "mg", 1, None, "oral", "continue"),
}


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text().splitlines() if line]


def author_reference(case: dict) -> dict:
    """Return the author's reference reading of the case text."""
    group = case["metric_group"]
    provider = case["provider"]
    if group == "atypical_pattern":
        return {"schedule_type": _PATTERN_TO_SCHEDULE[provider["pattern_type"]]}
    if group == "mislabelled_schedule":
        note = case["note"].lower()
        if "prn" in note or "if-needed" in note:
            return {"schedule_type": "prn"}
        if "taper" in note or "titration" in note:
            return {"schedule_type": "taper"}
        return {"schedule_type": "non_daily"}
    if group == "benign_variation":
        times, interval = provider.get("times_per_day"), provider.get("interval_hours")
        return {
            "schedule_type": _PATTERN_TO_SCHEDULE[provider["pattern_type"]],
            "dose_value": provider.get("dose"),
            "dose_unit": provider.get("unit"),
            "times_per_day": times,
            "interval_hours": interval,
            "route": "oral" if provider.get("route") else None,
            "action": provider.get("action"),
        }
    dose, unit, times, interval, route, action = _PLAIN_REFERENCE[case["id"]]
    return {
        "schedule_type": "interval" if interval else "fixed_daily",
        "dose_value": dose,
        "dose_unit": unit,
        "times_per_day": times,
        "interval_hours": interval,
        "route": route,
        "action": action,
    }


def unique_texts() -> list[dict]:
    """One entry per distinct instruction text (benign wording wins over mismatch twins)."""
    priority = {"benign_variation": 0, "atypical_pattern": 1, "mislabelled_schedule": 2}
    chosen: dict[str, dict] = {}
    for case in sorted(
        load_cases(), key=lambda c: (priority.get(c["metric_group"], 3), c["id"])
    ):
        chosen.setdefault(case["text"], case)
    return sorted(chosen.values(), key=lambda c: c["id"])
