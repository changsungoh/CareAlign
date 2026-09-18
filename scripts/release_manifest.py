"""Create or verify hashes for CareAlign's safety-critical release artifacts."""

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release-manifest.json"
ARTIFACTS = (
    "backend/app/models/schemas.py",
    "backend/app/rules/medication_aliases.json",
    "backend/app/rules/route_aliases.json",
    "backend/app/services/conflicts.py",
    "backend/app/services/evidence.py",
    "backend/app/services/extraction.py",
    "backend/app/services/fhir.py",
    "backend/app/services/normalization.py",
    "backend/app/services/provider_guard.py",
    "backend/app/services/rxnorm.py",
    "backend/app/services/teachback.py",
    "evaluation/cases/synthetic-v1.jsonl",
    "evaluation/schema/case.schema.json",
    "evaluation/evaluate_rxnorm.py",
    "evaluation/rxnorm/cases-v1.json",
    "research/clinical/rxnorm-edge-cases-v2.csv",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_version(field: str) -> str:
    source = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
    match = re.search(rf'^\s*{re.escape(field)}:\s*str\s*=\s*"([^"]+)"', source, re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not locate {field} in backend settings.")
    return match.group(1)


def current_manifest() -> dict:
    project = tomllib.loads((ROOT / "backend/pyproject.toml").read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "app_version": project["project"]["version"],
        "prompt_version": config_version("prompt_version"),
        "rules_version": config_version("rules_version"),
        "dataset_version": config_version("dataset_version"),
        "terminology_policy_version": config_version("terminology_policy_version"),
        "artifacts": {relative: sha256(ROOT / relative) for relative in ARTIFACTS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Update release-manifest.json")
    parser.add_argument("--verify", action="store_true", help="Fail if the manifest is stale")
    arguments = parser.parse_args()
    current = current_manifest()
    rendered = json.dumps(current, indent=2, sort_keys=True) + "\n"
    if arguments.write:
        MANIFEST.write_text(rendered, encoding="utf-8")
        print(f"Wrote {MANIFEST.relative_to(ROOT)}")
        return
    if arguments.verify:
        if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "release-manifest.json is stale. Run: python scripts/release_manifest.py --write"
            )
        print("Release manifest verified.")
        return
    print(rendered, end="")


if __name__ == "__main__":
    main()
