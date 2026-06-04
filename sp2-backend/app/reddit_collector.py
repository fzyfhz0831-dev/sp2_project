from __future__ import annotations

import os
from typing import Any

import praw
from dotenv import load_dotenv

try:
    from app.alerts import send_alert
    from app.pipeline_config import (
        DEFAULT_SUBREDDIT,
        PIPELINE_LOG_PATH,
        PROJECT_ROOT,
        REDDIT_POST_LIMIT,
    )
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import DEFAULT_SUBREDDIT, PIPELINE_LOG_PATH, PROJECT_ROOT, REDDIT_POST_LIMIT
    from app.utils import retry, save_json, setup_logger


# All logging goes through backend.utils.setup_logger(), so every module writes
# to the same pipeline log file configured in backend/config.py.
LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
OUTPUT_FILE = PROJECT_ROOT / "reddit_data.json"
REDDIT_USER_AGENT_PLACEHOLDER = "sp2_run_doctor_by_<reddit_username>"


def _missing_reddit_credentials() -> list[str]:
    """Return missing Reddit .env values without exposing secrets."""
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
    """Create a read-only PRAW client from credentials stored in .env."""
    # python-dotenv loads values from a project-level .env file into os.environ.
    # Expected variables:
    # - REDDIT_CLIENT_ID
    # - REDDIT_CLIENT_SECRET
    # - REDDIT_USER_AGENT
    # Never hardcode these credentials in source code.
    load_dotenv()

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    missing_values = _missing_reddit_credentials()

    if missing_values:
        message = (
            "Missing Reddit credentials in .env: "
            + ", ".join(missing_values)
            + ". Set all required Reddit environment variables before running."
        )
        LOGGER.error(message)
        raise ValueError(message)

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def _format_post(post: Any) -> dict[str, Any]:
    """Convert a PRAW submission into the fields required by the website."""
    return {
        "id": post.id,
        "title": post.title,
        "score": int(post.score),
        "num_comments": int(post.num_comments),
        "url": post.url,
        "created_utc": str(post.created_utc),
    }


def fetch_latest_posts(
    subreddit_name: str,
    limit: int = REDDIT_POST_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch the newest Reddit posts from a subreddit with retry protection."""
    reddit = _create_reddit_client()

    def request_posts() -> list[dict[str, Any]]:
        subreddit = reddit.subreddit(subreddit_name)
        return [_format_post(post) for post in subreddit.new(limit=limit)]

    LOGGER.info("Fetching latest Reddit posts from r/%s", subreddit_name)
    # backend.utils.retry() keeps the API call resilient without duplicating
    # retry loops inside every collector.
    try:
        return retry(request_posts, retries=3, delay=2)
    except Exception as error:
        send_alert(
            "Module: reddit_collector\n"
            f"Error: Reddit API failed after all retries for r/{subreddit_name}\n"
            f"Details: {error}"
        )
        raise


def run(subreddit_name: str | None = None) -> list[dict[str, Any]]:
    """Collect Reddit data and save it for the merge step."""
    load_dotenv()
    selected_subreddit = subreddit_name or os.getenv("REDDIT_SUBREDDIT", DEFAULT_SUBREDDIT)

    missing_values = _missing_reddit_credentials()
    if missing_values:
        message = (
            "WARNING: Reddit credentials are missing or incomplete in .env: "
            + ", ".join(missing_values)
            + ". Reddit post collection will be skipped."
        )
        print(message)
        LOGGER.warning(message)
        save_json([], OUTPUT_FILE)
        return []

    try:
        LOGGER.info("Reddit collector started for r/%s", selected_subreddit)
        posts = fetch_latest_posts(selected_subreddit, REDDIT_POST_LIMIT)
        # backend.utils.save_json() creates parent folders and logs write errors.
        save_json(posts, OUTPUT_FILE)
        LOGGER.info("Reddit collector saved %s posts to %s", len(posts), OUTPUT_FILE)
        return posts
    except Exception as error:
        send_alert(
            "Module: reddit_collector\n"
            "Error: Reddit collector failed\n"
            f"Details: {error}"
        )
        raise


if __name__ == "__main__":
    run()
