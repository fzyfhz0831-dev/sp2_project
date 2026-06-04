from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_RUN_PATH = BASE_DIR / "sample_run.json"


def _print_result(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"{status}: {name}{suffix}")


def _assert_success_payload(payload: dict[str, Any], endpoint: str) -> None:
    required = {"success", "filename", "summary_text", "analysis", "run_id"}
    missing = required - set(payload)
    if missing:
        raise AssertionError(f"{endpoint} response missing keys: {sorted(missing)}")

    if payload.get("success") is not True:
        raise AssertionError(f"{endpoint} did not return success=true")


def check_health(client: TestClient) -> None:
    response = client.get("/health")
    if response.status_code != 200:
        raise AssertionError(f"expected 200, got {response.status_code}")

    payload = response.json()
    if payload != {"status": "ok"}:
        raise AssertionError(f"unexpected payload: {payload!r}")


def check_analyze_json(client: TestClient) -> dict[str, Any]:
    if not SAMPLE_RUN_PATH.exists():
        raise AssertionError(f"sample run not found: {SAMPLE_RUN_PATH}")

    with SAMPLE_RUN_PATH.open("rb") as sample_file:
        response = client.post(
            "/api/analyze",
            files={"file": ("sample_run.json", sample_file, "application/json")},
        )

    if response.status_code != 200:
        raise AssertionError(f"expected 200, got {response.status_code}: {response.text}")

    payload = response.json()
    _assert_success_payload(payload, "/api/analyze")
    return payload

def main() -> int:
    checks = (
        ("GET /health", check_health),
        ("POST /api/analyze JSON", check_analyze_json),
    )
    failures: list[str] = []

    with TestClient(app) as client:
        for name, check in checks:
            try:
                check(client)
                _print_result(name, True)
            except Exception as error:
                failures.append(f"{name}: {error}")
                _print_result(name, False, str(error))

    if failures:
        print("\nMVP self-check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nMVP self-check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
