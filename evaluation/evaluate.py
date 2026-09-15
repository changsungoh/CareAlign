"""Validate dataset shape and calculate reproducible release-gate summaries."""

import json
from collections import Counter
from pathlib import Path

DATASET = Path(__file__).parent / "cases" / "synthetic-v1.jsonl"
EXPECTED_GROUPS = {
    "conflict_detection": 43,
    "pattern_containment": 5,
    "teachback": 22,
    "security": 15,
    "resilience": 5,
}


def main() -> None:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    counts = Counter(case["metric_group"] for case in cases)
    if len(cases) != 90 or counts != Counter(EXPECTED_GROUPS):
        raise SystemExit(f"Dataset contract failed: {len(cases)=}, {dict(counts)=}")
    print(json.dumps({"dataset": "synthetic-eval-v1", "cases": len(cases),
                      "metric_groups": dict(counts), "contains_real_patient_data": False}, indent=2))


if __name__ == "__main__":
    main()
