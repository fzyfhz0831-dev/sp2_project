from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate
from dotenv import load_dotenv

AUTOMATION_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = AUTOMATION_ROOT.parent / "sp2-backend"

os.environ.setdefault("SP2_PIPELINE_ROOT", str(AUTOMATION_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.pipeline_config import ARCHIVE_DIR, DATA_DIR, LATEST_INSIGHTS_PATH, LOGS_DIR, PIPELINE_LOG_PATH
from app.utils import setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
ARCHIVE_NAME_PATTERN = re.compile(r"run_insights_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}\.json$")

# This schema checks the required website payload and allows optional sources
# such as Steam news and newer collectors.
LATEST_INSIGHTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "generated_at": {"type": "string"},
        "reddit_posts": {"type": "array"},
        "steam_data": {"type": "array"},
        "steam_news": {"type": "array"},
        "reddit_comments": {"type": "array"},
        "steam_reviews": {"type": "array"},
        "official_news": {"type": "array"},
    },
    "required": ["generated_at", "reddit_posts", "steam_data"],
}

# Modules are run in the same practical order as the automation pipeline.
# Optional modules are still included when present in the project.
MODULES_TO_TEST = [
    "app.reddit_collector",
    "app.reddit_comments_collector",
    "app.steam_collector",
    "app.steam_news_collector",
    "app.steam_reviews_collector",
    "app.official_news_collector",
    "app.collect_data",
    "app.data_cleaner",
    "app.health_check",
    "app.log_analyzer",
    "app.report_generator",
    "app.run_parser",
    "app.loss_classifier",
    "app.run_analyzer",
    "app.recommendation_generator",
    "pipeline_runner",
]

REDDIT_MODULES = {
    "app.reddit_collector",
    "app.reddit_comments_collector",
}
STEAM_MODULES = {
    "app.steam_collector",
    "app.steam_news_collector",
    "app.steam_reviews_collector",
}
REDDIT_USER_AGENT_PLACEHOLDER = "sp2_run_doctor_by_<reddit_username>"
STEAM_API_KEY_PLACEHOLDER = "YOUR_STEAM_API_KEY"


def write_skipped_reddit_placeholder(module_name: str) -> None:
    """Write empty Reddit source files when Reddit modules are skipped."""
    if module_name == "app.reddit_collector":
        (DATA_DIR.parent / "reddit_data.json").write_text("[]", encoding="utf-8")
    if module_name == "app.reddit_comments_collector":
        (DATA_DIR / "reddit_comments.json").write_text("[]", encoding="utf-8")


def write_skipped_steam_placeholder(module_name: str) -> None:
    """Write empty Steam source files when Steam modules are skipped."""
    if module_name == "app.steam_collector":
        (DATA_DIR.parent / "steam_data.json").write_text("[]", encoding="utf-8")
    if module_name == "app.steam_news_collector":
        (DATA_DIR / "steam_news.json").write_text("[]", encoding="utf-8")
    if module_name == "app.steam_reviews_collector":
        (DATA_DIR / "steam_reviews.json").write_text("[]", encoding="utf-8")


def missing_reddit_credentials() -> list[str]:
    """Check .env for Reddit values and treat placeholders as missing."""
    load_dotenv()
    values = {
        "REDDIT_CLIENT_ID": os.getenv("REDDIT_CLIENT_ID"),
        "REDDIT_CLIENT_SECRET": os.getenv("REDDIT_CLIENT_SECRET"),
        "REDDIT_USER_AGENT": os.getenv("REDDIT_USER_AGENT"),
    }
    missing = [name for name, value in values.items() if not value]
    if values["REDDIT_USER_AGENT"] == REDDIT_USER_AGENT_PLACEHOLDER:
        missing.append("REDDIT_USER_AGENT")
    return sorted(set(missing))


def missing_steam_credentials() -> list[str]:
    """Check .env for STEAM_API_KEY and treat placeholders as missing."""
    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key or api_key == STEAM_API_KEY_PLACEHOLDER:
        return ["STEAM_API_KEY"]
    return []


def ensure_runtime_folders() -> None:
    """Create runtime folders before any module writes logs or data."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def import_run_function(module_name: str) -> Any:
    """Import a module and return run() or main() for pipeline_runner.py."""
    module = importlib.import_module(module_name)

    if hasattr(module, "run"):
        return module.run
    if hasattr(module, "main"):
        return module.main

    raise AttributeError(f"{module_name} does not define run() or main()")


def run_modules() -> tuple[list[str], list[str], list[str]]:
    """Run each pipeline module and collect success/failure messages."""
    successes: list[str] = []
    failures: list[str] = []
    skipped: list[str] = []
    missing_reddit = missing_reddit_credentials()
    missing_steam = missing_steam_credentials()

    for module_name in MODULES_TO_TEST:
        if module_name in REDDIT_MODULES and missing_reddit:
            message = (
                f"{module_name}: SKIPPED_CONFIG missing "
                + ", ".join(missing_reddit)
            )
            print(message)
            LOGGER.warning(message)
            write_skipped_reddit_placeholder(module_name)
            skipped.append(message)
            continue
        if module_name in STEAM_MODULES and missing_steam:
            message = f"{module_name}: SKIPPED_CONFIG missing " + ", ".join(missing_steam)
            print(message)
            LOGGER.warning(message)
            write_skipped_steam_placeholder(module_name)
            skipped.append(message)
            continue

        try:
            print(f"Running {module_name}...")
            run_function = import_run_function(module_name)
            result = run_function()

            # A module returning False is treated as a failed validation step.
            if result is False:
                failures.append(f"{module_name}: returned False")
            else:
                successes.append(module_name)
        except ModuleNotFoundError:
            # Some modules are optional by requirement, but the current project
            # has most of them. Missing optional modules are warnings only.
            failures.append(f"{module_name}: module not found")
        except Exception as error:
            failures.append(f"{module_name}: {error}")

    return successes, failures, skipped


def validate_latest_insights() -> tuple[bool, str]:
    """Verify data/latest_insights.json exists, is valid JSON, and matches schema."""
    if not LATEST_INSIGHTS_PATH.exists():
        return False, f"Missing JSON file: {LATEST_INSIGHTS_PATH}"

    try:
        payload = json.loads(LATEST_INSIGHTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return False, f"Invalid JSON: {error}"

    try:
        validate(instance=payload, schema=LATEST_INSIGHTS_SCHEMA)
    except ValidationError as error:
        return False, f"Schema validation failed: {error.message}"

    return True, "JSON validation passed"


def archive_backup_exists() -> bool:
    """Check for at least one timestamped archive backup."""
    return any(
        ARCHIVE_NAME_PATTERN.match(path.name)
        for path in ARCHIVE_DIR.glob("run_insights_*.json")
    )


def reports_generated() -> bool:
    """Check optional report outputs when report_generator.py exists."""
    return (DATA_DIR / "report.csv").exists() and (DATA_DIR / "report.html").exists()


def read_log_findings() -> tuple[list[str], list[str]]:
    """Return warning and error lines from logs/pipeline.log."""
    if not PIPELINE_LOG_PATH.exists():
        return [], [f"Missing log file: {PIPELINE_LOG_PATH}"]

    lines = PIPELINE_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    warnings = [line for line in lines if "[WARNING]" in line]
    errors = [line for line in lines if "[ERROR]" in line]
    return warnings, errors


def print_summary(
    successes: list[str],
    failures: list[str],
    skipped: list[str],
    json_status: tuple[bool, str],
    archive_exists: bool,
    reports_exist: bool,
    warnings: list[str],
    errors: list[str],
) -> None:
    """Print a clear final summary for humans running this script."""
    print("\n=== Pipeline Validation Summary ===")
    print(f"Modules run successfully: {len(successes)}")
    for module_name in successes:
        print(f"  OK  {module_name}")

    print(f"\nModule failures: {len(failures)}")
    for failure in failures:
        print(f"  FAIL  {failure}")

    print(f"\nSkipped modules: {len(skipped)}")
    for skip in skipped:
        print(f"  SKIPPED_CONFIG  {skip}")

    print(f"\nJSON validation: {json_status[1]}")
    print(f"Archive backup exists: {archive_exists}")
    print(f"Reports generated: {reports_exist}")
    print(f"Warnings found: {len(warnings)}")
    print(f"Errors found: {len(errors)}")

    if warnings:
        print("\nLatest warnings:")
        for line in warnings[-10:]:
            print(f"  {line}")

    if errors:
        print("\nLatest errors:")
        for line in errors[-10:]:
            print(f"  {line}")


def main() -> int:
    """Run the end-to-end validation and return an appropriate exit code."""
    ensure_runtime_folders()
    LOGGER.info("test_pipeline.py validation started")

    successes, failures, skipped = run_modules()
    json_status = validate_latest_insights()
    archive_exists = archive_backup_exists()
    reports_exist = reports_generated()
    warnings, errors = read_log_findings()

    print_summary(
        successes,
        failures,
        skipped,
        json_status,
        archive_exists,
        reports_exist,
        warnings,
        errors,
    )

    hard_failure = bool(failures) or not json_status[0] or not archive_exists
    if hard_failure:
        LOGGER.error("test_pipeline.py validation failed")
        return 1

    LOGGER.info("test_pipeline.py validation completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
