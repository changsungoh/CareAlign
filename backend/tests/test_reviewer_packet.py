import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

EVALUATION = Path(__file__).resolve().parents[2] / "evaluation"


def _load(tmp_path: Path):
    sys.path.insert(0, str(EVALUATION))
    spec = importlib.util.spec_from_file_location(
        "reviewer_packet", EVALUATION / "reviewer_packet.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PACKET = tmp_path / "packet"
    module.KEY = tmp_path / "key.json"
    module.RESULTS = tmp_path / "results"
    return module


def _rows(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_packet_is_blinded_and_complete(tmp_path) -> None:
    packet = _load(tmp_path)
    packet.prepare()
    conflicts = _rows(packet.PACKET / "conflict-review-sheet.csv")
    extraction = _rows(packet.PACKET / "extraction-review-sheet.csv")
    assert len(conflicts) == 43 and len(extraction) == 35
    ids = [r["case_id"] for r in conflicts + extraction]
    assert len(set(ids)) == len(ids)
    for name in (
        "conflict-review-sheet.csv",
        "extraction-review-sheet.csv",
        "README_FOR_REVIEWERS.md",
    ):
        text = (packet.PACKET / name).read_text()
        for pattern in (
            r"conflict-\d", r"atyp-\d", r"mis-\d", r"fld-\d", r"ben-\d",
            r"expected", r"provider", r"frequency_difference", r"possible_omission_difference",
        ):  # fmt: skip
            assert not re.search(pattern, text), (name, pattern)
    # Reviewer answer columns start empty.
    assert all(not r["reference_outcome"] for r in conflicts)


def test_packet_is_deterministic(tmp_path) -> None:
    first, second = _load(tmp_path / "a"), _load(tmp_path / "b")
    first.prepare()
    second.prepare()
    assert (first.PACKET / "conflict-review-sheet.csv").read_text() == (
        second.PACKET / "conflict-review-sheet.csv"
    ).read_text()
    assert json.loads(first.KEY.read_text()) == json.loads(second.KEY.read_text())


def _fill_like_author(packet, tmp_path: Path, flip: bool) -> tuple[Path, Path]:
    key = json.loads(packet.KEY.read_text())
    conflicts_path, extraction_path = tmp_path / "c.csv", tmp_path / "e.csv"
    rows = _rows(packet.PACKET / "conflict-review-sheet.csv")
    for row in rows:
        outcome, category = packet._author_outcome(key["conflicts"][row["case_id"]]["expected"])
        if flip:
            outcome, category = "insufficient_information", "other"
        row["reference_outcome"], row["reference_category"] = outcome, category
    with conflicts_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=packet.CONFLICT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    rows = _rows(packet.PACKET / "extraction-review-sheet.csv")
    for row in rows:
        ref = key["extraction"][row["case_id"]]["reference"]
        row["schedule_type"] = "other" if flip else ref["schedule_type"]
        for field in (
            "dose_value",
            "dose_unit",
            "times_per_day",
            "interval_hours",
            "route",
            "action",
        ):
            if field in ref and ref[field] is not None:
                row[field] = str(ref[field])
    with extraction_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=packet.EXTRACTION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return conflicts_path, extraction_path


def test_scoring_reports_full_agreement_and_real_disagreement(tmp_path) -> None:
    packet = _load(tmp_path)
    packet.prepare()
    c, e = _fill_like_author(packet, tmp_path, flip=False)
    report = packet.score(c, e, "agree")
    assert report["conflict_sheet"]["outcome_agreement"] == 1.0
    assert report["disagreements"] == 0
    c2, e2 = _fill_like_author(packet, tmp_path, flip=True)
    flipped = packet.score(c2, e2, "disagree")
    assert flipped["conflict_sheet"]["outcome_agreement"] < 0.5
    assert flipped["disagreements"] > 40
    # Reviewer files are never modified by scoring.
    assert c2.read_text() == c2.read_text()
