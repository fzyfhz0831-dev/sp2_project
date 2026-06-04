from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUTOMATION_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AUTOMATION_ROOT.parent
LOGS_DIR = AUTOMATION_ROOT / "logs"
SUMMARY_PATH = LOGS_DIR / "batch_analyze_summary.json"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
RUN_LIKE_KEYS = {
    "character",
    "player_class",
    "class",
    "floor",
    "floor_reached",
    "floor_num",
    "victory",
    "won",
    "is_victory",
    "deck",
    "cards",
    "master_deck",
    "relics",
    "relic_names",
    "path",
    "floor_path",
    "route",
}
SKIP_NAMES = {
    "latest_insights.json",
    "run_analysis.json",
    "run_recommendations.json",
    "loss_classification.json",
    "log_summary.json",
    "final_check_summary.json",
    "run_review_self_check.json",
}


def configure_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sp2_batch_analyze")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.FileHandler(LOGS_DIR / "batch_analyze.log", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


LOGGER = configure_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload multiple sample run JSON files to the FastAPI analyzer."
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("SP2_API_BASE_URL") or DEFAULT_API_BASE_URL,
        help="Backend base URL, default: http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        help="File or directory to scan. May be provided multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum run JSON files to upload.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def default_inputs() -> list[Path]:
    return [
        AUTOMATION_ROOT / "data",
        PROJECT_ROOT / "sp2-backend" / "mock_data" / "runs",
        PROJECT_ROOT / "sp2-backend" / "sample_run.json",
    ]


def load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def is_run_json(path: Path) -> bool:
    if path.suffix.lower() != ".json" or path.name in SKIP_NAMES:
        return False

    payload = load_json_object(path)
    if payload is None:
        return False

    return bool(RUN_LIKE_KEYS.intersection(payload.keys()))


def discover_run_files(inputs: list[Path], limit: int) -> list[Path]:
    candidates: list[Path] = []

    for input_path in inputs:
        resolved = input_path.resolve()
        if resolved.is_file() and is_run_json(resolved):
            candidates.append(resolved)
        elif resolved.is_dir():
            candidates.extend(
                path.resolve()
                for path in sorted(resolved.rglob("*.json"))
                if is_run_json(path)
            )

    unique_files = list(dict.fromkeys(candidates))
    return unique_files[: max(1, limit)]


def request_json(url: str, timeout: int) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_backend(api_base_url: str, timeout: int) -> None:
    payload = request_json(f"{api_base_url.rstrip('/')}/health", timeout)
    if payload != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health payload: {payload!r}")


def upload_file(api_base_url: str, path: Path, timeout: int) -> dict[str, Any]:
    boundary = f"----sp2batch{uuid.uuid4().hex}"
    file_bytes = path.read_bytes()
    filename = path.name.replace('"', "")
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8"),
            b"Content-Type: application/json\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    request = urllib.request.Request(
        f"{api_base_url.rstrip('/')}/api/analyze",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def write_summary(summary: dict[str, Any]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    args = parse_args()
    inputs = args.input or default_inputs()
    api_base_url = args.api_base_url.rstrip("/")
    run_files = discover_run_files(inputs, args.limit)

    started_at = datetime.now(timezone.utc).isoformat()
    LOGGER.info("Batch analyze started against %s", api_base_url)
    LOGGER.info("Discovered %s run JSON files", len(run_files))

    summary: dict[str, Any] = {
        "started_at": started_at,
        "api_base_url": api_base_url,
        "inputs": [str(path) for path in inputs],
        "files_discovered": [str(path) for path in run_files],
        "successes": [],
        "failures": [],
    }

    try:
        check_backend(api_base_url, args.timeout)
    except Exception as error:
        message = f"Backend health check failed: {error}"
        LOGGER.error(message)
        summary["failures"].append({"stage": "health", "error": message})
        write_summary(summary)
        print(message)
        return 1

    if not run_files:
        message = "No run-like JSON files found."
        LOGGER.error(message)
        summary["failures"].append({"stage": "discovery", "error": message})
        write_summary(summary)
        print(message)
        return 1

    for path in run_files:
        try:
            response = upload_file(api_base_url, path, args.timeout)
            run_id = response.get("run_id")
            summary["successes"].append(
                {
                    "file": str(path),
                    "run_id": run_id,
                    "filename": response.get("filename"),
                }
            )
            LOGGER.info("Uploaded %s as run_id=%s", path, run_id)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            LOGGER.error("Upload failed for %s: HTTP %s %s", path, error.code, detail)
            summary["failures"].append(
                {"file": str(path), "status": error.code, "error": detail}
            )
        except Exception as error:
            LOGGER.error("Upload failed for %s: %s", path, error)
            summary["failures"].append({"file": str(path), "error": str(error)})

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary["success_count"] = len(summary["successes"])
    summary["failure_count"] = len(summary["failures"])
    write_summary(summary)

    print(
        "Batch analyze complete: "
        f"{summary['success_count']} succeeded, {summary['failure_count']} failed. "
        f"Summary: {SUMMARY_PATH}"
    )
    return 0 if summary["successes"] and not summary["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
