from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH
    from app.utils import save_json, setup_logger
except ImportError:
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH
    from app.utils import save_json, setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
LOG_SUMMARY_JSON = DATA_DIR / "log_summary.json"
LOG_SUMMARY_TEXT = DATA_DIR / "log_summary.txt"


def _extract_timestamp(line: str) -> str:
    """Return the leading timestamp from a standard pipeline log line."""
    if len(line) >= 19:
        return line[:19]
    return ""


def _read_log_lines(log_path: Path) -> list[str]:
    """Read logs/pipeline.log safely and return all lines without newlines."""
    with log_path.open("r", encoding="utf-8") as file:
        return [line.rstrip("\n") for line in file]


def analyze_log(lines: list[str]) -> dict[str, Any]:
    """Convert raw log lines into a structured summary dictionary."""
    info_count = 0
    warning_count = 0
    error_count = 0
    latest_pipeline_start = ""
    latest_pipeline_finish = ""
    errors: list[str] = []
    warnings: list[str] = []

    for line in lines:
        if "[INFO]" in line:
            info_count += 1
        if "[WARNING]" in line:
            warning_count += 1
            warnings.append(line)
        if "[ERROR]" in line:
            error_count += 1
            errors.append(line)

        # Pipeline start/finish messages are written by pipeline_runner.py.
        if "Pipeline started at" in line:
            latest_pipeline_start = _extract_timestamp(line)
        if "Pipeline finished at" in line:
            latest_pipeline_finish = _extract_timestamp(line)

    return {
        "total_log_lines": len(lines),
        "info_messages": info_count,
        "warning_messages": warning_count,
        "error_messages": error_count,
        "latest_pipeline_start_time": latest_pipeline_start,
        "latest_pipeline_finish_time": latest_pipeline_finish,
        "latest_errors": errors[-10:],
        "latest_warnings": warnings[-10:],
    }


def save_text_report(summary: dict[str, Any], output_path: Path) -> None:
    """Write a beginner-friendly text summary beside the JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "Slay the Spire 2 Run Doctor Log Summary",
        "",
        f"Total log lines: {summary['total_log_lines']}",
        f"INFO messages: {summary['info_messages']}",
        f"WARNING messages: {summary['warning_messages']}",
        f"ERROR messages: {summary['error_messages']}",
        f"Latest pipeline start time: {summary['latest_pipeline_start_time']}",
        f"Latest pipeline finish time: {summary['latest_pipeline_finish_time']}",
        "",
        "Latest errors:",
    ]

    lines.extend(summary["latest_errors"] or ["None"])
    lines.append("")
    lines.append("Latest warnings:")
    lines.extend(summary["latest_warnings"] or ["None"])

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> bool:
    """Analyze logs/pipeline.log and save JSON plus text reports."""
    try:
        LOGGER.info("Log analyzer started")

        if not PIPELINE_LOG_PATH.exists():
            LOGGER.error("Log analyzer failed: missing log file %s", PIPELINE_LOG_PATH)
            return False

        # Read the log, count message levels, and collect recent warnings/errors.
        lines = _read_log_lines(PIPELINE_LOG_PATH)
        summary = analyze_log(lines)

        save_json(summary, LOG_SUMMARY_JSON)
        save_text_report(summary, LOG_SUMMARY_TEXT)

        LOGGER.info("Log analyzer saved JSON report to %s", LOG_SUMMARY_JSON)
        LOGGER.info("Log analyzer saved text report to %s", LOG_SUMMARY_TEXT)
        LOGGER.info("Log analyzer completed successfully")
        return True
    except Exception as error:
        # Returning False lets pipeline_runner finish without crashing.
        LOGGER.exception("Log analyzer failed: %s", error)
        return False


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
