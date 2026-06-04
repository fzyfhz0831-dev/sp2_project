from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import praw
from dotenv import load_dotenv
from prawcore.exceptions import PrawcoreException


LOG_FILE = Path.cwd() / "logs" / "pipeline.log"
OUTPUT_FILE = Path.cwd() / "reddit_data.json"
DEFAULT_SUBREDDIT = "slaythespire"
POST_LIMIT = 50
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0

T = TypeVar("T")


def setup_logger() -> logging.Logger:
    """Create the pipeline logger and write logs to logs/pipeline.log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("reddit_collector")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate log lines if run() is called multiple times in one process.
    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


LOGGER = setup_logger()


def retry(action: Callable[[], T], action_name: str) -> T:
    """Retry a Reddit API request up to three times before raising an error."""
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            LOGGER.info("%s started (attempt %s/%s)", action_name, attempt, MAX_RETRIES)
            return action()
        except (PrawcoreException, Exception) as error:
            last_error = error
            LOGGER.warning(
                "%s failed (attempt %s/%s): %s",
                action_name,
                attempt,
                MAX_RETRIES,
                error,
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"{action_name} failed after {MAX_RETRIES} attempts") from last_error


def create_reddit_client() -> praw.Reddit:
    """Load credentials from .env and create a PRAW Reddit client."""
    load_dotenv()

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not client_id or not client_secret or not user_agent:
        raise ValueError(
            "Missing Reddit API credentials. Set REDDIT_CLIENT_ID, "
            "REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT in your .env file."
        )

    LOGGER.info("Creating Reddit API client")
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def format_post(post: Any) -> dict[str, Any]:
    """Convert a PRAW post object into JSON-friendly structured data."""
    return {
        "id": post.id,
        "title": post.title,
        "score": int(post.score),
        "num_comments": int(post.num_comments),
        "url": post.url,
        "created_utc": str(post.created_utc),
    }


def fetch_latest_posts(
    reddit: praw.Reddit,
    subreddit_name: str,
    limit: int = POST_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch the latest posts from a specified subreddit."""
    LOGGER.info("Preparing to fetch %s latest posts from r/%s", limit, subreddit_name)

    def request_posts() -> list[dict[str, Any]]:
        subreddit = reddit.subreddit(subreddit_name)
        return [format_post(post) for post in subreddit.new(limit=limit)]

    posts = retry(request_posts, f"Fetch latest posts from r/{subreddit_name}")
    LOGGER.info("Fetched %s posts from r/%s", len(posts), subreddit_name)
    return posts


def save_posts(posts: list[dict[str, Any]], output_file: Path = OUTPUT_FILE) -> None:
    """Save scraped Reddit posts to reddit_data.json in the current directory."""
    LOGGER.info("Saving %s posts to %s", len(posts), output_file)

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(posts, file, indent=2, ensure_ascii=False)

    LOGGER.info("Saved Reddit data successfully")


def run(subreddit_name: str | None = None) -> list[dict[str, Any]]:
    """Entry point for pipeline_runner.py and direct script execution."""
    load_dotenv()
    selected_subreddit = subreddit_name or os.getenv("REDDIT_SUBREDDIT", DEFAULT_SUBREDDIT)

    LOGGER.info("Reddit scraping started for r/%s", selected_subreddit)
    reddit = create_reddit_client()
    posts = fetch_latest_posts(reddit, selected_subreddit, POST_LIMIT)
    save_posts(posts, OUTPUT_FILE)
    LOGGER.info("Reddit scraping completed successfully")

    return posts


if __name__ == "__main__":
    run()
