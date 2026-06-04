from __future__ import annotations

import json
from typing import Any

try:
    from app.alerts import send_alert
    from app.pipeline_config import LATEST_INSIGHTS_PATH, PIPELINE_LOG_PATH
    from app.utils import setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import LATEST_INSIGHTS_PATH, PIPELINE_LOG_PATH
    from app.utils import setup_logger


# Use the shared pipeline logger so health check results are written beside the
# collector and merge logs in logs/pipeline.log.
LOGGER = setup_logger(str(PIPELINE_LOG_PATH))


def _alert_failure(message: str) -> bool:
    """Send a health-check alert and return False for simple failure paths."""
    send_alert(
        "Module: health_check\n"
        "Error: health_check.run() returned False\n"
        f"Details: {message}"
    )
    return False


def _load_latest_insights() -> dict[str, Any] | None:
    """Read data/latest_insights.json and return None when it is unusable."""
    if not LATEST_INSIGHTS_PATH.exists():
        LOGGER.error("Health check failed: missing JSON file %s", LATEST_INSIGHTS_PATH)
        return None

    try:
        with LATEST_INSIGHTS_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as error:
        LOGGER.error("Health check failed: invalid JSON in %s: %s", LATEST_INSIGHTS_PATH, error)
        return None

    if not isinstance(payload, dict):
        LOGGER.error("Health check failed: latest insights JSON must be an object")
        return None

    return payload


def _has_required_fields(payload: dict[str, Any]) -> bool:
    """Validate the fields required by the website data contract."""
    valid = True

    if "generated_at" not in payload:
        LOGGER.error("Health check failed: missing required field generated_at")
        valid = False

    if "reddit_posts" not in payload:
        LOGGER.error("Health check failed: missing required field reddit_posts")
        valid = False
    elif not isinstance(payload["reddit_posts"], list):
        LOGGER.error("Health check failed: reddit_posts must be a list")
        valid = False

    if "steam_data" not in payload:
        LOGGER.error("Health check failed: missing required field steam_data")
        valid = False
    elif not isinstance(payload["steam_data"], list):
        LOGGER.error("Health check failed: steam_data must be a list")
        valid = False

    for optional_field in ("steam_news", "reddit_comments", "steam_reviews", "official_news"):
        if optional_field in payload and not isinstance(payload[optional_field], list):
            LOGGER.error("Health check failed: %s must be a list when present", optional_field)
            valid = False

    return valid


def run() -> bool:
    """Run project output checks and return True when the pipeline data is healthy."""
    LOGGER.info("Health check started")

    if not PIPELINE_LOG_PATH.exists():
        LOGGER.error("Health check failed: missing log file %s", PIPELINE_LOG_PATH)
        return _alert_failure(f"Missing log file {PIPELINE_LOG_PATH}")

    payload = _load_latest_insights()
    if payload is None:
        return _alert_failure("latest_insights.json is missing, invalid, or not an object")

    if not _has_required_fields(payload):
        return _alert_failure("latest_insights.json is missing required fields")

    # Empty source lists are not schema failures, but they are worth noticing.
    if not payload["reddit_posts"]:
        LOGGER.warning("Health check warning: reddit_posts is empty")

    if not payload["steam_data"]:
        LOGGER.warning("Health check warning: steam_data is empty")

    LOGGER.info("Health check completed successfully")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
