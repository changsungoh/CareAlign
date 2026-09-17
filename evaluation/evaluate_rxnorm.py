"""Validate or execute the versioned live RxNorm terminology contract."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CASES = ROOT / "evaluation/rxnorm/cases-v1.json"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.services.rxnorm import RxNormClient  # noqa: E402


def load_contract() -> dict:
    contract = json.loads(CASES.read_text(encoding="utf-8"))
    case_ids = [case["case_id"] for case in contract["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("RxNorm case IDs must be unique.")
    known = set(case_ids)
    required_case_fields = {"case_id", "query", "expected_status", "identity"}
    for case in contract["cases"]:
        if not required_case_fields <= case.keys():
            raise ValueError(f"Incomplete case: {case.get('case_id', 'unknown')}")
        if case["identity"] not in {"required", "forbidden"}:
            raise ValueError(f"Invalid identity rule: {case['case_id']}")
    for assertion in contract["relationship_assertions"]:
        if assertion["left_case_id"] not in known or assertion["right_case_id"] not in known:
            raise ValueError(f"Unknown relationship case: {assertion['assertion_id']}")
        if assertion["expected_relation"] not in {"same_identity", "distinct_identity"}:
            raise ValueError(f"Invalid relationship rule: {assertion['assertion_id']}")
    return contract


def case_failures(case: dict, result: dict) -> list[str]:
    failures: list[str] = []
    if result["status"] != case["expected_status"]:
        failures.append(f"status={result['status']} expected={case['expected_status']}")
    has_identity = result["normalized_id"] is not None
    if case["identity"] == "required" and not has_identity:
        failures.append("comparison identity was required")
    if case["identity"] == "forbidden" and has_identity:
        failures.append("comparison identity must remain absent")
    allowed_source = case.get("allowed_source_ttys", [])
    if result["term_type"] is not None and result["term_type"] not in allowed_source:
        failures.append(f"source_tty={result['term_type']} allowed={allowed_source}")
    allowed_canonical = case.get("allowed_canonical_ttys", [])
    if allowed_canonical and result["canonical_term_type"] not in allowed_canonical:
        failures.append(
            f"canonical_tty={result['canonical_term_type']} allowed={allowed_canonical}"
        )
    if has_identity and result["source_suppress"] != "N":
        failures.append("resolved source concept is not explicitly active")
    if has_identity and result["canonical_suppress"] != "N":
        failures.append("resolved canonical concept is not explicitly active")
    return failures


async def execute(contract: dict) -> dict:
    settings.rxnorm_enabled = True
    client = RxNormClient()
    results: list[dict] = []
    by_case: dict[str, dict] = {}
    failures: list[dict] = []
    for case in contract["cases"]:
        resolution = asdict(await client.resolve(case["query"]))
        checks = case_failures(case, resolution)
        entry = {"case_id": case["case_id"], "query": case["query"], **resolution}
        results.append(entry)
        by_case[case["case_id"]] = entry
        if checks:
            failures.append({"case_id": case["case_id"], "failures": checks})
        await asyncio.sleep(0.1)

    relationship_results: list[dict] = []
    for assertion in contract["relationship_assertions"]:
        left = by_case[assertion["left_case_id"]]["normalized_id"]
        right = by_case[assertion["right_case_id"]]["normalized_id"]
        actual = "same_identity" if left is not None and left == right else "distinct_identity"
        passed = actual == assertion["expected_relation"]
        relationship_results.append({**assertion, "actual_relation": actual, "passed": passed})
        if not passed:
            failures.append(
                {
                    "assertion_id": assertion["assertion_id"],
                    "failures": [f"relation={actual} expected={assertion['expected_relation']}"],
                }
            )

    versions = sorted(
        {
            (result["dataset_version"], result["api_version"])
            for result in results
            if result["dataset_version"] or result["api_version"]
        }
    )
    return {
        "evaluation_type": "live_rxnorm_terminology_contract",
        "disclaimer": contract["disclaimer"],
        "contract_version": contract["dataset_version"],
        "evaluated_at": datetime.now(UTC).isoformat(),
        "rxnorm_versions": [
            {"dataset_version": dataset, "api_version": api} for dataset, api in versions
        ],
        "case_accounting": {
            "cases": len(results),
            "relationships": len(relationship_results),
            "failed_checks": len(failures),
        },
        "results": results,
        "relationship_results": relationship_results,
        "failures": failures,
        "passed": not failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    contract = load_contract()
    if not arguments.live:
        print(
            json.dumps(
                {
                    "contract_version": contract["dataset_version"],
                    "cases": len(contract["cases"]),
                    "relationships": len(contract["relationship_assertions"]),
                    "contract_valid": True,
                    "live_calls": 0,
                },
                indent=2,
            )
        )
        return
    if not arguments.confirm_live:
        raise SystemExit("Live RxNorm execution requires --confirm-live.")
    report = asyncio.run(execute(contract))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not report["passed"]:
        raise SystemExit("RxNorm terminology contract failed.")


if __name__ == "__main__":
    main()
