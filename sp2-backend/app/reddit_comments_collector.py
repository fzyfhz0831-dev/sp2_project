from __future__ import annotations

import os
from typing import Any

import praw
from dotenv import load_dotenv

try:
    from app.alerts import send_alert
    from app.pipeline_config import (
        DATA_DIR,
        PIPELINE_LOG_PATH,
        REDDIT_COMMENT_LIMIT,
        REDDIT_COMMENT_SUBREDDITS,
    )
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH, REDDIT_COMMENT_LIMIT, REDDIT_COMMENT_SUBREDDITS
    from app.utils import retry, save_json, setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
OUTPUT_FILE = DATA_DIR / "reddit_comments.json"
REDDIT_USER_AGENT_PLACEHOLDER = "sp2_run_doctor_by_<reddit_username>"


def _missing_reddit_credentials() -> list[str]:
    """Return missing Reddit .env values so callers can skip cleanly."""
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


def _create_reddit_client() -> praw.Reddit:
    """Create a PRAW client using Reddit credentials from .env."""
    load_dotenv()
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    missing_values = _missing_reddit_credentials()
    if missing_values:
        message = (
            "Missing Reddit credentials for reddit_comments_collector: "
            + ", ".join(missing_values)
        )
        LOGGER.error(message)
        raise ValueError(message)

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def _format_comment(comment: Any, subreddit_name: str) -> dict[str, Any]:
    """Keep the fields needed for downstream analysis."""
    return {
        "id": str(comment.id),
        "subreddit": subreddit_name,
        "body": str(comment.body),
        "score": int(comment.score),
        "created_utc": float(comment.created_utc),
        "permalink": f"https://www.reddit.com{comment.permalink}",
    }


def fetch_comments(
    subreddits: list[str] = REDDIT_COMMENT_SUBREDDITS,
    limit: int = REDDIT_COMMENT_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch latest comments from configured subreddits with retry handling."""
    reddit = _create_reddit_client()
    comments: list[dict[str, Any]] = []

    for subreddit_name in subreddits:
        def request_comments() -> list[dict[str, Any]]:
            subreddit = reddit.subreddit(subreddit_name)
            return [
                _format_comment(comment, subreddit_name)
                for comment in subreddit.comments(limit=limit)
            ]

        LOGGER.info("Fetching Reddit comments from r/%s", subreddit_name)
        comments.extend(retry(request_comments, retries=3, delay=2))

    return comments


def run() -> list[dict[str, Any]]:
    """Collect Reddit comments and save raw JSON to data/."""
    missing_values = _missing_reddit_credentials()
    if missing_values:
        message = (
            "WARNING: Reddit credentials are missing or incomplete in .env: "
            + ", ".join(missing_values)
            + ". Reddit comment collection will be skipped."
        )
        print(message)
        LOGGER.warning(message)
        save_json([], OUTPUT_FILE)
        return []

    try:
        LOGGER.info("Reddit comments collector started")
        comments = fetch_comments()
        save_json(comments, OUTPUT_FILE)
        LOGGER.info("Reddit comments collector saved %s comments", len(comments))
        return comments
    except Exception as error:
        LOGGER.exception("Reddit comments collector failed: %s", error)
        send_alert(
            "Module: reddit_comments_collector\n"
            "Error: Reddit comments collection failed\n"
            f"Details: {error}"
        )
        return []


if __name__ == "__main__":
    run()
