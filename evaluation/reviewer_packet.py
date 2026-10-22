"""Build a blinded packet for independent pharmacist/clinician review and score returned sheets.

Implements the first pass of research/clinical/EXPERT_REVIEW_PROTOCOL.md (CA-CLIN-001): randomized
order, random case IDs, and no CareAlign output or author labels in anything reviewers receive.

    python evaluation/reviewer_packet.py prepare
    python evaluation/reviewer_packet.py score --conflicts RETURNED.csv --extraction RETURNED.csv \
        --reviewer R1

Scoring never edits a reviewer's file. Disagreements are written to a separate report and are not
resolved here; adjudication follows the protocol.
"""

# ruff: noqa: E501

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import atypical_reference as reference  # noqa: E402

ROOT = Path(__file__).parent
CONFLICT_DATASET = ROOT / "cases" / "synthetic-v1.jsonl"
PACKET = ROOT / "review" / "packet-v1"
KEY = ROOT / "review" / "packet-v1-key.json"
RESULTS = ROOT / "review" / "results"
SEED = 20261022
PROTOCOL = "CA-CLIN-001"

OUTCOMES = (
    "clarification_warranted",
    "no_clarification_warranted",
    "insufficient_information",
)
CATEGORIES = (
    "dose",
    "frequency",
    "route",
    "action",
    "possible_omission",
    "identity",
    "other",
    "none",
)
CONFLICT_COLUMNS = [
    "case_id", "doc1_date", "doc1_type", "doc1_text", "doc2_date", "doc2_type", "doc2_text",
    "reference_outcome", "reference_category", "clinically_meaningful",
    "evidence_document_1", "evidence_document_2", "confidence_1_to_5", "rationale",
]  # fmt: skip
EXTRACTION_COLUMNS = [
    "case_id", "instruction_text", "schedule_type", "dose_value", "dose_unit", "times_per_day",
    "interval_hours", "route", "action", "safe_to_compare_as_fixed_daily", "confidence_1_to_5",
    "rationale",
]  # fmt: skip

README = f"""# CareAlign independent review packet

**Protocol:** {PROTOCOL} (first pass) | **Data:** fictional, synthetic text only | **Time:** about 2 hours

Thank you for reviewing. CareAlign is a research prototype that compares medication instructions
from different care records and prepares questions for a healthcare professional. You are asked to
judge the source text yourself. **Please do not look up the project's code, dataset or results while
reviewing** - your independence is what makes this review useful. You will not be shown any
CareAlign output in this pass.

## What you receive
- `conflict-review-sheet.csv`: 43 pairs of two dated, fictional records (an earlier and a later one).
- `extraction-review-sheet.csv`: 35 single fictional instructions.
- `REVIEWER_ATTESTATION.md`: independence and conflict-of-interest declaration. Please complete it.

All case IDs are random and the order is shuffled. All text is fictional; never enter real patient data.

## Sheet 1 - conflict review
Read both records and decide whether a pharmacist or prescriber would want the difference clarified.
Fill, for each row:
- `reference_outcome`: one of {", ".join(OUTCOMES)}
- `reference_category`: one of {", ".join(CATEGORIES)}. Use `possible_omission` when a medicine in one
  record is simply absent from the other and you cannot tell whether that was intended. Use `none`
  when no clarification is warranted.
- `clinically_meaningful`: yes / no / uncertain
- `evidence_document_1`, `evidence_document_2`: the exact words that support your decision
- `confidence_1_to_5` and a short `rationale`

Do not infer an intention that the text does not state (for example, that an absent medicine was
stopped on purpose).

## Sheet 2 - instruction reading
For each instruction, record how *you* read it:
- `schedule_type`: one of {", ".join(reference.SCHEDULE_TYPES)}
  (`fixed_daily` = a set number of doses each day; `interval` = every N hours; `prn` = as needed;
  `taper` = changing dose over time; `non_daily` = less often than daily; `range` = a dose or
  frequency range; `conditional` = depends on a condition; `other` = none of these or unclear)
- `dose_value` (number only) and `dose_unit`; leave blank when not stated or not a single value
- `times_per_day` or `interval_hours` (whichever the text gives; leave the other blank)
- `route` (oral, sublingual, topical, inhaled, intramuscular, intravenous, subcutaneous) or blank
- `action` (continue, start, stop, hold) or blank when not stated
- `safe_to_compare_as_fixed_daily`: yes / no / uncertain - could a software check safely compare
  this instruction with another by treating it as a fixed daily schedule?
- `confidence_1_to_5` and a short `rationale`

## Returning your work
Save your answers in the same CSV files (do not rename columns) and return them with the completed
attestation. Please do not discuss your answers with other reviewers before returning them.
"""


def _hash_of(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def prepare() -> None:
    rng = random.Random(SEED)
    conflicts = [
        json.loads(line)
        for line in CONFLICT_DATASET.read_text().splitlines()
        if line and json.loads(line)["metric_group"] == "conflict_detection"
    ]
    texts = reference.unique_texts()
    rng.shuffle(conflicts)
    rng.shuffle(texts)
    ids = rng.sample(range(1000, 9999), len(conflicts) + len(texts))
    key: dict[str, dict] = {
        "seed": SEED,
        "protocol": PROTOCOL,
        "conflicts": {},
        "extraction": {},
    }

    PACKET.mkdir(parents=True, exist_ok=True)
    with (PACKET / "conflict-review-sheet.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONFLICT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for number, case in zip(ids, conflicts, strict=False):
            case_id = f"C-{number}"
            old, new = case["documents"]
            writer.writerow(
                {
                    "case_id": case_id,
                    "doc1_date": old["document_date"], "doc1_type": old["document_type"],
                    "doc1_text": old["raw_text"],
                    "doc2_date": new["document_date"], "doc2_type": new["document_type"],
                    "doc2_text": new["raw_text"],
                }
            )  # fmt: skip
            key["conflicts"][case_id] = {
                "source_id": case["id"],
                "expected": case["expected_conflicts"],
            }
    with (PACKET / "extraction-review-sheet.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXTRACTION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for number, case in zip(ids[len(conflicts) :], texts, strict=False):
            case_id = f"E-{number}"
            writer.writerow({"case_id": case_id, "instruction_text": case["text"]})
            key["extraction"][case_id] = {
                "source_id": case["id"],
                "reference": reference.author_reference(case),
            }
    (PACKET / "README_FOR_REVIEWERS.md").write_text(README)
    shutil.copyfile(
        ROOT.parent / "research" / "clinical" / "REVIEWER_ATTESTATION.md",
        PACKET / "REVIEWER_ATTESTATION.md",
    )
    key["packet_hash"] = _hash_of(
        *(
            (PACKET / name).read_text()
            for name in ("conflict-review-sheet.csv", "extraction-review-sheet.csv")
        )
    )
    KEY.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n")
    print(
        f"Packet written to {PACKET} ({len(conflicts)} conflict + {len(texts)} instruction rows)."
    )
    print(f"Author key written to {KEY}; do NOT send it to reviewers.")


def _author_outcome(expected: list[str]) -> tuple[str, str]:
    if not expected:
        return "no_clarification_warranted", "none"
    return "clarification_warranted", expected[0].removesuffix("_difference")


def cohen_kappa(left: list[str], right: list[str]) -> float | None:
    n = len(left)
    if n == 0:
        return None
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / n
    left_counts, right_counts = Counter(left), Counter(right)
    expected = sum(left_counts[k] * right_counts[k] for k in left_counts) / (n * n)
    return None if expected == 1 else round((observed - expected) / (1 - expected), 4)


def _read(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _norm(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def score(conflicts_csv: Path | None, extraction_csv: Path | None, reviewer: str) -> dict:
    key = json.loads(KEY.read_text())
    RESULTS.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "reviewer": reviewer,
        "protocol": PROTOCOL,
        "packet_hash": key["packet_hash"],
    }
    disagreements: list[dict] = []

    if conflicts_csv:
        rows = [r for r in _read(conflicts_csv) if _norm(r.get("reference_outcome"))]
        author_out, rev_out, author_cat, rev_cat = [], [], [], []
        for row in rows:
            entry = key["conflicts"].get(row["case_id"])
            if entry is None:
                raise SystemExit(f"Unknown case_id in conflict sheet: {row['case_id']}")
            outcome, category = _author_outcome(entry["expected"])
            r_outcome, r_category = (
                _norm(row["reference_outcome"]),
                _norm(row["reference_category"]),
            )
            author_out.append(outcome), rev_out.append(r_outcome)
            author_cat.append(category), rev_cat.append(r_category)
            if (outcome, category) != (r_outcome, r_category):
                disagreements.append(
                    {"sheet": "conflict", "case_id": row["case_id"], "source_id": entry["source_id"],
                     "author": f"{outcome}/{category}", "reviewer": f"{r_outcome}/{r_category}",
                     "reviewer_rationale": row.get("rationale", "")}
                )  # fmt: skip
        n = len(rows)
        report["conflict_sheet"] = {
            "rows_scored": n,
            "outcome_agreement": round(sum(a == b for a, b in zip(author_out, rev_out, strict=True)) / n, 4) if n else None,
            "outcome_kappa": cohen_kappa(author_out, rev_out),
            "category_agreement": round(sum(a == b for a, b in zip(author_cat, rev_cat, strict=True)) / n, 4) if n else None,
        }  # fmt: skip

    if extraction_csv:
        rows = [r for r in _read(extraction_csv) if _norm(r.get("schedule_type"))]
        agree: Counter[str] = Counter()
        total: Counter[str] = Counter()
        for row in rows:
            entry = key["extraction"].get(row["case_id"])
            if entry is None:
                raise SystemExit(f"Unknown case_id in extraction sheet: {row['case_id']}")
            ref = entry["reference"]
            checks = {
                "schedule_type": _norm(row["schedule_type"]),
                "dose_value": row.get("dose_value", "").strip().replace(",", ""),
                "dose_unit": _norm(row.get("dose_unit")),
                "times_per_day": row.get("times_per_day", "").strip(),
                "interval_hours": row.get("interval_hours", "").strip(),
                "route": _norm(row.get("route")),
                "action": _norm(row.get("action")),
            }
            for field, given in checks.items():
                if field not in ref:
                    continue
                truth = "" if ref[field] is None else str(ref[field]).lower()
                if field == "dose_value" and given and truth:
                    same = float(given) == float(truth)
                else:
                    same = given == truth
                total[field] += 1
                agree[field] += int(same)
                if not same:
                    disagreements.append(
                        {"sheet": "extraction", "case_id": row["case_id"], "source_id": entry["source_id"],
                         "field": field, "author": truth, "reviewer": given,
                         "reviewer_rationale": row.get("rationale", "")}
                    )  # fmt: skip
        report["extraction_sheet"] = {
            "rows_scored": len(rows),
            "field_agreement": {f: round(agree[f] / total[f], 4) for f in sorted(total)},
        }

    out = RESULTS / f"disagreements-{reviewer}.csv"
    fields = [
        "sheet",
        "case_id",
        "source_id",
        "field",
        "author",
        "reviewer",
        "reviewer_rationale",
    ]
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(disagreements)
    report["disagreements"] = len(disagreements)
    report["disagreement_file"] = out.name
    report["note"] = (
        "Disagreements are inputs to adjudication, not corrections. Neither the reviewer's file nor "
        "the author labels are modified."
    )
    (RESULTS / f"summary-{reviewer}.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    scoring = sub.add_parser("score")
    scoring.add_argument("--conflicts", type=Path)
    scoring.add_argument("--extraction", type=Path)
    scoring.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        print(json.dumps(score(args.conflicts, args.extraction, args.reviewer), indent=2))
