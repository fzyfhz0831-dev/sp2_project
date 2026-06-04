from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from app.alerts import send_alert
    from app.pipeline_config import (
        ARCHIVE_DIR,
        COMPRESS_ARCHIVE,
        LATEST_INSIGHTS_PATH,
        MAX_ARCHIVE_FILES,
        PIPELINE_LOG_PATH,
        PROJECT_ROOT,
    )
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import ARCHIVE_DIR, COMPRESS_ARCHIVE, LATEST_INSIGHTS_PATH, MAX_ARCHIVE_FILES, PIPELINE_LOG_PATH, PROJECT_ROOT
    from app.utils import retry, save_json, setup_logger


# Use the shared logger helper so merge logs go to logs/pipeline.log.
LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
REDDIT_FILE = PROJECT_ROOT / "reddit_data.json"
STEAM_FILE = PROJECT_ROOT / "steam_data.json"
STEAM_NEWS_FILE = PROJECT_ROOT / "data" / "steam_news.json"
REDDIT_COMMENTS_FILE = PROJECT_ROOT / "data" / "reddit_comments.json"
STEAM_REVIEWS_FILE = PROJECT_ROOT / "data" / "steam_reviews.json"
OFFICIAL_NEWS_FILE = PROJECT_ROOT / "data" / "official_news.json"
OUTPUT_FILE = LATEST_INSIGHTS_PATH


def _compress_archive_file(archive_file: Path) -> Path:
    """Compress one JSON archive file into a .zip file."""
    zip_base_path = archive_file.with_suffix("")
    zip_path = archive_file.with_suffix(".zip")

    # shutil.make_archive wants the base path without ".zip".
    shutil.make_archive(
        base_name=str(zip_base_path),
        format="zip",
        root_dir=archive_file.parent,
        base_dir=archive_file.name,
    )
    archive_file.unlink()
    return zip_path


def prune_archive_files(
    max_files: int = MAX_ARCHIVE_FILES,
    compress_archive: bool = COMPRESS_ARCHIVE,
) -> None:
    """Compress or delete older run_insights archives beyond the newest max_files."""
    archive_files = sorted(
        ARCHIVE_DIR.glob("run_insights_*.json"),
        key=lambda path: path.stat().st_ctime,
        reverse=True,
    )

    # The newest files are at the front of the list. Everything after max_files
    # is old enough to compress or delete.
    old_files = archive_files[max_files:]
    if not old_files:
        return

    if compress_archive:
        LOGGER.info("Archive compression started for %s old files", len(old_files))

    for old_file in archive_files[max_files:]:
        try:
            if compress_archive:
                zip_path = _compress_archive_file(old_file)
                LOGGER.info("Compressed archive file %s to %s", old_file, zip_path)
            else:
                old_file.unlink()
                LOGGER.info("Deleted old archive file: %s", old_file)
        except Exception as error:
            LOGGER.error("Failed to process old archive file %s: %s", old_file, error)

    if compress_archive:
        LOGGER.info("Archive compression completed")


def read_json_file(input_file: Path, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Read a JSON source file, logging errors while allowing the pipeline to continue."""
    try:
        LOGGER.info("Reading source JSON file: %s", input_file)

        with input_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON list in {input_file}, got {type(data).__name__}")

        return data
    except FileNotFoundError:
        LOGGER.error("Source JSON file is missing: %s", input_file)
    except json.JSONDecodeError as error:
        LOGGER.error("Source JSON file is invalid: %s (%s)", input_file, error)
    except Exception as error:
        LOGGER.error("Failed to read source JSON file %s: %s", input_file, error)

    return default


def archive_latest_insights(source_file: Path) -> Path | None:
    """Copy latest_insights.json into archive/ with a timestamped file name."""
    try:
        # Create archive/ automatically so the copy works on a fresh project.
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        archive_file = ARCHIVE_DIR / f"run_insights_{timestamp}.json"

        # File copy can fail if the file is briefly locked, so reuse retry().
        retry(shutil.copy2, 3, 2, source_file, archive_file)

        LOGGER.info("Archived latest insights to: %s", archive_file)
        prune_archive_files(MAX_ARCHIVE_FILES)
        return archive_file
    except Exception as error:
        # Archiving is useful, but it should never stop the data pipeline.
        LOGGER.error("Failed to archive latest insights: %s", error)
        return None


def build_latest_insights() -> dict[str, Any]:
    """Merge Reddit and Steam data into one website-ready JSON structure."""
    # Missing or invalid source files become empty lists so one bad input does
    # not prevent later website builds from receiving a valid JSON payload.
    reddit_posts = read_json_file(REDDIT_FILE, [])
    steam_data = read_json_file(STEAM_FILE, [])
    steam_news = read_json_file(STEAM_NEWS_FILE, [])
    reddit_comments = read_json_file(REDDIT_COMMENTS_FILE, [])
    steam_reviews = read_json_file(STEAM_REVIEWS_FILE, [])
    official_news = read_json_file(OFFICIAL_NEWS_FILE, [])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reddit_posts": reddit_posts,
        "steam_data": steam_data,
        "steam_news": steam_news,
        "reddit_comments": reddit_comments,
        "steam_reviews": steam_reviews,
        "official_news": official_news,
    }


def validate_merged_insights(payload: dict[str, Any]) -> None:
    """Alert when merged data is invalid or contains no source records."""
    if not payload.get("generated_at"):
        raise ValueError("Merged JSON is missing generated_at")
    if not isinstance(payload.get("reddit_posts"), list):
        raise ValueError("Merged JSON field reddit_posts must be a list")
    if not isinstance(payload.get("steam_data"), list):
        raise ValueError("Merged JSON field steam_data must be a list")
    if not isinstance(payload.get("steam_news"), list):
        raise ValueError("Merged JSON field steam_news must be a list")
    for optional_field in ("reddit_comments", "steam_reviews", "official_news"):
        if not isinstance(payload.get(optional_field), list):
            raise ValueError(f"Merged JSON field {optional_field} must be a list")
    if not any(
        payload[field]
        for field in (
            "reddit_posts",
            "steam_data",
            "steam_news",
            "reddit_comments",
            "steam_reviews",
            "official_news",
        )
    ):
        send_alert(
            "Module: collect_data\n"
            "Error: Merged JSON is empty\n"
            "Details: all configured data sources are empty"
        )


def run() -> dict[str, Any]:
    """Entry point for pipeline_runner.py and direct script execution."""
    try:
        LOGGER.info("Data merge started")
        latest_insights = build_latest_insights()
        validate_merged_insights(latest_insights)
        # Use the shared JSON writer for consistent output and error logging.
        save_json(latest_insights, OUTPUT_FILE)
        archive_latest_insights(OUTPUT_FILE)
        LOGGER.info("Data merge completed successfully: %s", OUTPUT_FILE)
        return latest_insights
    except Exception as error:
        LOGGER.exception("Data merge failed: %s", error)
        send_alert(
            "Module: collect_data\n"
            "Error: Data merge failed or generated invalid JSON\n"
            f"Details: {error}"
        )
        raise


if __name__ == "__main__":
    run()
