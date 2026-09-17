"""Fail-fast production checks for the public CareAlign submission."""

import argparse
import json
import urllib.error
import urllib.request


def fetch(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "CareAlign-Preflight/0.4"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, response.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--backend-url", required=True)
    arguments = parser.parse_args()
    if not arguments.frontend_url.startswith("https://") or not arguments.backend_url.startswith(
        "https://"
    ):
        raise SystemExit("Production URLs must use HTTPS.")
    checks: dict[str, bool] = {}
    try:
        health_status, health = fetch(f"{arguments.backend_url.rstrip('/')}/api/health")
        version_status, version = fetch(f"{arguments.backend_url.rstrip('/')}/api/version")
        readiness_status, readiness = fetch(f"{arguments.backend_url.rstrip('/')}/api/readiness")
        frontend_status, frontend = fetch(arguments.frontend_url)
        checks["backend_health"] = health_status == 200 and json.loads(health)["status"] == "ok"
        checks["backend_readiness"] = (
            readiness_status == 200 and json.loads(readiness)["status"] == "ready"
        )
        metadata = json.loads(version)
        checks["version_metadata"] = version_status == 200 and all(
            metadata.get(key)
            for key in (
                "app_version",
                "prompt_version",
                "rules_version",
                "dataset_version",
                "terminology_policy_version",
                "release_sha",
                "provider_mode",
            )
        )
        checks["frontend"] = frontend_status == 200
        checks["medical_disclaimer"] = "not medical advice" in frontend.casefold()
        checks["synthetic_only"] = "synthetic" in frontend.casefold()
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        raise SystemExit(f"Preflight could not complete: {error}") from error
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise SystemExit("Production preflight failed.")


if __name__ == "__main__":
    main()
