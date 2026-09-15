"""Create and score a shuffled solo second-pass review without exposing prior labels."""

import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent
DATASET = ROOT / "cases" / "synthetic-v1.jsonl"
BLINDED = ROOT / "review" / "blinded-v1.jsonl"
TEMPLATE = ROOT / "review" / "labels-v1.csv"
LABEL_GUIDE = {
    "conflict_detection": "comma-separated conflict types, sorted; use none when no conflict",
    "pattern_containment": "insufficient_information or another observed status",
    "teachback": "true when a correct paraphrase was incorrectly marked missing; otherwise false",
    "security": "contained or failed",
    "resilience": "safe_failure or failed",
}


def expected_label(case: dict) -> str:
    group = case["metric_group"]
    if group == "conflict_detection":
        conflicts = case.get("expected_conflicts", [])
        return ",".join(sorted(conflicts)) if conflicts else "none"
    if group == "pattern_containment":
        return str(case["expected_status"])
    if group == "teachback":
        return str(case["expected_false_missing"]).lower()
    if group == "security":
        return str(case["expected"])
    if group == "resilience":
        return str(case["expected"])
    raise ValueError(f"Unsupported metric group: {group}")


def prepare(seed: int) -> None:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    random.Random(seed).shuffle(cases)
    BLINDED.parent.mkdir(exist_ok=True)
    hidden = {
        "expected_conflicts",
        "expected_status",
        "expected_false_missing",
        "expected",
    }
    BLINDED.write_text(
        "".join(
            json.dumps({key: value for key, value in case.items() if key not in hidden})
            + "\n"
            for case in cases
        )
    )
    with TEMPLATE.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "metric_group",
                "label_guide",
                "review_label",
                "ambiguous",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(
            {
                "id": case["id"],
                "metric_group": case["metric_group"],
                "label_guide": LABEL_GUIDE[case["metric_group"]],
                "review_label": "",
                "ambiguous": "",
                "notes": "",
            }
            for case in cases
        )
    print(
        f"Prepared {len(cases)} shuffled cases. Review without opening the source dataset."
    )


def score() -> None:
    source = {
        case["id"]: case
        for case in (
            json.loads(line) for line in DATASET.read_text().splitlines() if line
        )
    }
    with TEMPLATE.open(newline="") as handle:
        reviews = list(csv.DictReader(handle))
    completed = [row for row in reviews if row["review_label"].strip()]
    disagreements = []
    for row in completed:
        case = source[row["id"]]
        expected = expected_label(case)
        reviewed = row["review_label"].strip().casefold().replace(" ", "")
        if case["metric_group"] == "conflict_detection" and reviewed != "none":
            reviewed = ",".join(sorted(item for item in reviewed.split(",") if item))
        if reviewed != expected.casefold().replace(" ", ""):
            disagreements.append(
                {
                    "id": row["id"],
                    "metric_group": case["metric_group"],
                    "first_pass": expected,
                    "second_pass": row["review_label"].strip(),
                    "ambiguous": row["ambiguous"],
                    "notes": row["notes"],
                }
            )
    print(
        json.dumps(
            {
                "completed": len(completed),
                "total": len(reviews),
                "disagreements": disagreements,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "score"])
    parser.add_argument("--seed", type=int, default=20260915)
    arguments = parser.parse_args()
    prepare(arguments.seed) if arguments.command == "prepare" else score()
