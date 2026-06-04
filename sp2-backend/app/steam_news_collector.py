from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH, STEAM_NEWS_APPID, STEAM_NEWS_COUNT
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, PIPELINE_LOG_PATH, STEAM_NEWS_APPID, STEAM_NEWS_COUNT
    from app.utils import retry, save_json, setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
OUTPUT_FILE = DATA_DIR / "steam_news.json"
STEAM_NEWS_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
STEAM_API_KEY_PLACEHOLDER = "YOUR_STEAM_API_KEY"


def _get_steam_api_key() -> str | None:
    """Load STEAM_API_KEY from .env for Steam Web API calls."""
    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key or api_key == STEAM_API_KEY_PLACEHOLDER:
        return None
    return api_key


def _skip_if_missing_steam_key() -> bool:
    """Skip Steam news collection cleanly when STEAM_API_KEY is not configured."""
    if _get_steam_api_key():
        return False

    message = (
        "WARNING: STEAM_API_KEY is missing or incomplete in .env. "
        "Steam news collection will be skipped."
    )
    print(message)
    LOGGER.warning(message)
    save_json([], OUTPUT_FILE)
    return True


def _format_news_item(item: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields the website needs from a Steam news item."""
    return {
        "gid": str(item.get("gid", "")),
        "title": str(item.get("title", "")),
        "url": str(item.get("url", "")),
        "author": str(item.get("author", "")),
        "contents": str(item.get("contents", "")),
        "date": int(item.get("date", 0) or 0),
    }


def fetch_steam_news(
    appid: str = STEAM_NEWS_APPID,
    count: int = STEAM_NEWS_COUNT,
) -> list[dict[str, Any]]:
    """Fetch recent Steam news for one app ID with retry protection."""
    def request_news() -> list[dict[str, Any]]:
        api_key = _get_steam_api_key()
        if not api_key:
            raise ValueError("STEAM_API_KEY is missing")

        response = requests.get(
            STEAM_NEWS_URL,
            params={"appid": appid, "count": count, "format": "json", "key": api_key},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        app_news = payload.get("appnews")
        if not isinstance(app_news, dict):
            raise ValueError("Steam news response is missing appnews object")
        news_items = app_news.get("newsitems", [])

        if not isinstance(news_items, list):
            raise ValueError("Steam news response field appnews.newsitems must be a list")

        return [_format_news_item(item) for item in news_items if isinstance(item, dict)]

    LOGGER.info("Fetching Steam news for appid %s", appid)
    return retry(request_news, retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS)


def run() -> list[dict[str, Any]]:
    """Collect Steam news and save raw output without crashing the pipeline."""
    if _skip_if_missing_steam_key():
        return []

    try:
        LOGGER.info("Steam news collector started")
        news_items = fetch_steam_news(STEAM_NEWS_APPID, STEAM_NEWS_COUNT)
        save_json(news_items, OUTPUT_FILE)
        LOGGER.info("Steam news collector saved %s items to %s", len(news_items), OUTPUT_FILE)
        return news_items
    except Exception as error:
        LOGGER.exception("Steam news collector failed: %s", error)
        send_alert(
            "Module: steam_news_collector\n"
            "Error: Steam news collection failed after all retries\n"
            f"Details: {error}"
        )
        return []


if __name__ == "__main__":
    run()
