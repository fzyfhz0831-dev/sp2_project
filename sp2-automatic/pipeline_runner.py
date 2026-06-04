from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTOMATION_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = AUTOMATION_ROOT.parent / "sp2-backend"

os.environ.setdefault("SP2_PIPELINE_ROOT", str(AUTOMATION_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import (
    collect_data,
    data_cleaner,
    health_check,
    log_analyzer,
    loss_classifier,
    official_news_collector,
    recommendation_generator,
    reddit_collector,
    reddit_comments_collector,
    report_generator,
    run_analyzer,
    run_parser,
    steam_collector,
    steam_news_collector,
    steam_reviews_collector,
)
from app.pipeline_config import PIPELINE_LOG_PATH, PROJECT_ROOT, ensure_project_directories
from app.utils import setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))


def run_step(step_name: str, step: Callable[[], Any]) -> Any | None:
    """Run one module and continue the pipeline if that module fails."""
    LOGGER.info("Module started: %s", step_name)

    try:
        result = step()
        LOGGER.info("Module completed successfully: %s", step_name)
        return result
    except Exception as error:
        # logger.exception includes the full traceback for debugging.
        LOGGER.exception("Module failed: %s. Error: %s", step_name, error)
        return None


def main() -> dict[str, Any | None]:
    """Run the full project pipeline in the required order."""
    # Make sure data/, logs/, and archive/ exist before any module runs.
    ensure_project_directories()

    start_time = datetime.now(timezone.utc)
    LOGGER.info("Pipeline started at %s", start_time.isoformat())
    LOGGER.info("Project root: %s", PROJECT_ROOT)
    LOGGER.info("Pipeline log path: %s", PIPELINE_LOG_PATH)

    # Each collector writes its own JSON file. The final step merges whatever
    # source files are available, even if an earlier collector failed.
    results = {
        "app.reddit_collector.run": run_step(
            "app.reddit_collector.run()",
            reddit_collector.run,
        ),
        "app.reddit_comments_collector.run": run_step(
            "app.reddit_comments_collector.run()",
            reddit_comments_collector.run,
        ),
        "app.steam_collector.run": run_step(
            "app.steam_collector.run()",
            steam_collector.run,
        ),
        "app.steam_news_collector.run": run_step(
            "app.steam_news_collector.run()",
            steam_news_collector.run,
        ),
        "app.steam_reviews_collector.run": run_step(
            "app.steam_reviews_collector.run()",
            steam_reviews_collector.run,
        ),
        "app.official_news_collector.run": run_step(
            "app.official_news_collector.run()",
            official_news_collector.run,
        ),
        "app.collect_data.run": run_step(
            "app.collect_data.run()",
            collect_data.run,
        ),
        "app.data_cleaner.run": run_step(
            "app.data_cleaner.run()",
            data_cleaner.run,
        ),
        "app.health_check.run": run_step(
            "app.health_check.run()",
            health_check.run,
        ),
    }

    # Write the finish time before log_analyzer.run() so the analyzer can
    # include this run's finish timestamp in data/log_summary.json.
    finish_time = datetime.now(timezone.utc)
    LOGGER.info("Pipeline finished at %s", finish_time.isoformat())
    results["app.log_analyzer.run"] = run_step(
        "app.log_analyzer.run()",
        log_analyzer.run,
    )
    results["app.report_generator.run"] = run_step(
        "app.report_generator.run()",
        report_generator.run,
    )

    # ------------------------------------------------------------------
    # Player Run Loss Review — these modules safely skip themselves
    # when data/player_run.json is missing (each returns None).
    # ------------------------------------------------------------------
    results["app.run_parser.run"] = run_step(
        "app.run_parser.run()",
        run_parser.run,
    )
    results["app.loss_classifier.run"] = run_step(
        "app.loss_classifier.run()",
        loss_classifier.run,
    )
    results["app.run_analyzer.run"] = run_step(
        "app.run_analyzer.run()",
        run_analyzer.run,
    )
    results["app.recommendation_generator.run"] = run_step(
        "app.recommendation_generator.run()",
        recommendation_generator.run,
    )

    return results


if __name__ == "__main__":
    main()
