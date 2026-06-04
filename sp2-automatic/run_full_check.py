from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT.parent / "sp2-backend"

os.environ.setdefault("SP2_PIPELINE_ROOT", str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.pipeline_config import ARCHIVE_DIR, DATA_DIR, LATEST_INSIGHTS_PATH, LOGS_DIR
from app.health_check import run as run_health_check
from pipeline_runner import main as run_pipeline


FINAL_SUMMARY_TEXT = DATA_DIR / "final_check_summary.txt"
FINAL_SUMMARY_JSON = DATA_DIR / "final_check_summary.json"
REDDIT_USER_AGENT_PLACEHOLDER = "sp2_run_doctor_by_<reddit_username>"
STEAM_API_KEY_PLACEHOLDER = "YOUR_STEAM_API_KEY"


def ensure_runtime_folders() -> None:
    """Create folders the automation pipeline needs before running checks."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def missing_reddit_credentials() -> list[str]:
    """Read .env and report missing Reddit settings for the final summary."""
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
    """Read .env and report missing Steam API key for the final summary."""
    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key or api_key == STEAM_API_KEY_PLACEHOLDER:
        return ["STEAM_API_KEY"]
    return []


def run_test_pipeline() -> dict[str, Any]:
    """Run test_pipeline.py in a subprocess because it exits with a status code."""
    script_path = PROJECT_ROOT / "test_pipeline.py"

    if not script_path.exists():
        return {
            "ran": False,
            "returncode": None,
            "status": "missing",
            "output": "test_pipeline.py was not found.",
        }

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "ran": True,
        "returncode": result.returncode,
        "status": "passed" if result.returncode == 0 else "failed",
        "output": (result.stdout + result.stderr).strip(),
    }


def run_optional_module(module_name: str) -> bool | None:
    """Import an optional monitoring module and run it when present."""
    try:
        module = __import__(module_name, fromlist=["run"])
    except ModuleNotFoundError:
        return None

    run_function = getattr(module, "run", None)
    if run_function is None:
        return None

    return bool(run_function())


def archive_backup_exists() -> bool:
    """Check whether at least one latest insights archive backup exists."""
    return any(ARCHIVE_DIR.glob("run_insights_*.json")) or any(ARCHIVE_DIR.glob("run_insights_*.zip"))


def build_summary() -> dict[str, Any]:
    """Run all checks and return a structured final summary."""
    ensure_runtime_folders()

    test_pipeline_result = run_test_pipeline()
    missing_reddit = missing_reddit_credentials()
    missing_steam = missing_steam_credentials()
    skipped_modules = []
    configuration_warnings = []

    if missing_reddit:
        skipped_modules.extend(["app.reddit_collector", "app.reddit_comments_collector"])
        configuration_warnings.append(
            "Missing Reddit credentials: " + ", ".join(missing_reddit)
        )
    if missing_steam:
        skipped_modules.extend(
            [
                "app.steam_collector",
                "app.steam_news_collector",
                "app.steam_reviews_collector",
            ]
        )
        configuration_warnings.append("Missing Steam API key: " + ", ".join(missing_steam))

    try:
        run_pipeline()
        pipeline_status = "passed"
        pipeline_failed = False
    except Exception as error:
        pipeline_status = f"failed: {error}"
        pipeline_failed = True

    latest_insights_exists = LATEST_INSIGHTS_PATH.exists()
    health_check_passed = run_health_check()
    log_analyzer_status = run_optional_module("app.log_analyzer")
    report_generator_status = run_optional_module("app.report_generator")

    run_parser_status = run_optional_module("app.run_parser")
    loss_classifier_status = run_optional_module("app.loss_classifier")
    run_analyzer_status = run_optional_module("app.run_analyzer")
    recommendation_generator_status = run_optional_module("app.recommendation_generator")

    log_summary_json = DATA_DIR / "log_summary.json"
    csv_report = DATA_DIR / "report.csv"
    html_report = DATA_DIR / "report.html"
    run_analysis_txt = DATA_DIR / "run_analysis.txt"
    run_recommendations_json = DATA_DIR / "run_recommendations.json"

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_status": pipeline_status,
        "latest_insights_exists": latest_insights_exists,
        "health_check_passed": health_check_passed,
        "archive_backup_exists": archive_backup_exists(),
        "log_summary_generated": log_summary_json.exists(),
        "csv_report_generated": csv_report.exists(),
        "html_report_generated": html_report.exists(),
        "run_analysis_txt_generated": run_analysis_txt.exists(),
        "run_recommendations_json_generated": run_recommendations_json.exists(),
        "archive_compression_present": any(ARCHIVE_DIR.glob("run_insights_*.zip")),
        "test_pipeline": test_pipeline_result,
        "configuration_warnings": configuration_warnings,
        "skipped_modules": skipped_modules,
        "missing_credentials": {"reddit": missing_reddit, "steam": missing_steam},
        "steam_api_configured": not missing_steam,
        "log_analyzer_run_status": log_analyzer_status,
        "report_generator_run_status": report_generator_status,
        "run_parser_run_status": run_parser_status,
        "loss_classifier_run_status": loss_classifier_status,
        "run_analyzer_run_status": run_analyzer_status,
        "recommendation_generator_run_status": recommendation_generator_status,
        "critical_failure": pipeline_failed or not latest_insights_exists or not health_check_passed,
    }
    return summary


def format_summary(summary: dict[str, Any]) -> str:
    """Create a human-readable final summary for terminal and text file output."""
    warnings: list[str] = []

    if not summary["log_summary_generated"]:
        warnings.append("Log summary is missing.")
    if not summary["csv_report_generated"]:
        warnings.append("CSV report is missing.")
    if not summary["html_report_generated"]:
        warnings.append("HTML report is missing.")
    if not summary["archive_compression_present"]:
        warnings.append("Archive compression file is not present yet.")
    if summary["test_pipeline"]["status"] != "passed":
        warnings.append("test_pipeline.py did not pass. Review its output for details.")
    warnings.extend(summary.get("configuration_warnings", []))

    if not summary.get("run_analysis_txt_generated", True):
        warnings.append("Run analysis text report is missing (player_run.json may be absent).")
    if not summary.get("run_recommendations_json_generated", True):
        warnings.append("Run recommendations JSON is missing (player_run.json may be absent).")

    lines = [
        "Final Full Check Summary",
        "",
        f"Generated at: {summary['generated_at']}",
        f"Pipeline run status: {summary['pipeline_run_status']}",
        f"latest_insights.json exists: {summary['latest_insights_exists']}",
        f"Health check passed: {summary['health_check_passed']}",
        f"Archive backup exists: {summary['archive_backup_exists']}",
        f"Log summary generated: {summary['log_summary_generated']}",
        f"CSV report generated: {summary['csv_report_generated']}",
        f"HTML report generated: {summary['html_report_generated']}",
        f"Run analysis TXT generated: {summary.get('run_analysis_txt_generated', 'N/A')}",
        f"Run recommendations JSON generated: {summary.get('run_recommendations_json_generated', 'N/A')}",
        f"Run parser status: {summary.get('run_parser_run_status', 'N/A')}",
        f"Loss classifier status: {summary.get('loss_classifier_run_status', 'N/A')}",
        f"Run analyzer status: {summary.get('run_analyzer_run_status', 'N/A')}",
        f"Recommendation generator status: {summary.get('recommendation_generator_run_status', 'N/A')}",
        f"Archive compression present: {summary['archive_compression_present']}",
        f"test_pipeline.py status: {summary['test_pipeline']['status']}",
        f"Skipped modules: {', '.join(summary['skipped_modules']) or 'None'}",
        f"Missing Reddit credentials: {', '.join(summary['missing_credentials']['reddit']) or 'None'}",
        f"Steam API configured: {summary['steam_api_configured']}",
        f"Missing Steam credentials: {', '.join(summary['missing_credentials']['steam']) or 'None'}",
        "",
        "Warnings:",
    ]

    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"Critical failure: {summary['critical_failure']}")
    return "\n".join(lines) + "\n"


def save_summary(summary: dict[str, Any], text_summary: str) -> None:
    """Save final check summary as both text and JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_SUMMARY_TEXT.write_text(text_summary, encoding="utf-8")
    FINAL_SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    """Run the final full check and return a shell-friendly exit code."""
    summary = build_summary()
    text_summary = format_summary(summary)
    save_summary(summary, text_summary)

    print(text_summary)
    return 1 if summary["critical_failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
