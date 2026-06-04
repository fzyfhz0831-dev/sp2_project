from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH, STEAM_REVIEW_APPIDS, STEAM_REVIEW_COUNT
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH, STEAM_REVIEW_APPIDS, STEAM_REVIEW_COUNT
    from app.utils import retry, save_json, setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
OUTPUT_FILE = DATA_DIR / "steam_reviews.json"
REVIEWS_URL_TEMPLATE = "https://store.steampowered.com/appreviews/{appid}"
STEAM_API_KEY_PLACEHOLDER = "YOUR_STEAM_API_KEY"


def _get_steam_api_key() -> str | None:
    """Load STEAM_API_KEY from .env so review requests share config rules."""
    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key or api_key == STEAM_API_KEY_PLACEHOLDER:
        return None
    return api_key


def _skip_if_missing_steam_key() -> bool:
    """Skip Steam review collection cleanly when STEAM_API_KEY is absent."""
    if _get_steam_api_key():
        return False

    message = (
        "WARNING: STEAM_API_KEY is missing or incomplete in .env. "
        "Steam review collection will be skipped."
    )
    print(message)
    LOGGER.warning(message)
    save_json([], OUTPUT_FILE)
    return True


def _format_review(appid: str, review: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Steam review into a small JSON-friendly structure."""
    author = review.get("author", {})
    if not isinstance(author, dict):
        author = {}

    return {
        "recommendationid": str(review.get("recommendationid", "")),
        "appid": appid,
        "author_steamid": str(author.get("steamid", "")),
        "review": str(review.get("review", "")),
        "voted_up": bool(review.get("voted_up", False)),
        "timestamp_created": int(review.get("timestamp_created", 0) or 0),
        "votes_up": int(review.get("votes_up", 0) or 0),
    }


def fetch_reviews(
    appids: list[str] = STEAM_REVIEW_APPIDS,
    count: int = STEAM_REVIEW_COUNT,
) -> list[dict[str, Any]]:
    """Fetch latest Steam reviews for configured app IDs."""
    reviews: list[dict[str, Any]] = []

    for appid in appids:
        def request_reviews() -> list[dict[str, Any]]:
            api_key = _get_steam_api_key()
            if not api_key:
                raise ValueError("STEAM_API_KEY is missing")

            response = requests.get(
                REVIEWS_URL_TEMPLATE.format(appid=appid),
                params={
                    "key": api_key,
                    "json": 1,
                    "num_per_page": count,
                    "filter": "recent",
                    "language": "all",
                    "purchase_type": "all",
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            raw_reviews = payload.get("reviews", [])
            if not isinstance(raw_reviews, list):
                raise ValueError("Steam review response field reviews must be a list")
            return [_format_review(appid, item) for item in raw_reviews if isinstance(item, dict)]

        LOGGER.info("Fetching Steam reviews for appid %s", appid)
        reviews.extend(retry(request_reviews, retries=3, delay=2))

    return reviews


def run() -> list[dict[str, Any]]:
    """Collect Steam reviews and save raw JSON to data/."""
    if _skip_if_missing_steam_key():
        return []

    try:
        LOGGER.info("Steam reviews collector started")
        reviews = fetch_reviews()
        save_json(reviews, OUTPUT_FILE)
        LOGGER.info("Steam reviews collector saved %s reviews", len(reviews))
        return reviews
    except Exception as error:
        LOGGER.exception("Steam reviews collector failed: %s", error)
        send_alert(
            "Module: steam_reviews_collector\n"
            "Error: Steam reviews collection failed\n"
            f"Details: {error}"
        )
        return []


if __name__ == "__main__":
    run()
