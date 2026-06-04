from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from app.alerts import send_alert
    from app.pipeline_config import ARCHIVE_DIR, LATEST_INSIGHTS_PATH, PIPELINE_LOG_PATH
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import ARCHIVE_DIR, LATEST_INSIGHTS_PATH, PIPELINE_LOG_PATH
    from app.utils import retry, save_json, setup_logger


# Use the shared project logger so cleaner activity appears in logs/pipeline.log.
LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
REDDIT_FIELDS = ("id", "title", "score", "num_comments", "url", "created_utc")
STEAM_FIELDS = ("appid", "name", "player_count")
STEAM_NEWS_FIELDS = ("gid", "title", "url", "author", "contents", "date")


def _to_int(value: Any, default: int = 0) -> int:
    """Convert a value to int, using a safe default when conversion fails."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_latest_insights() -> dict[str, Any]:
    """Read the latest insights JSON file before cleaning it."""
    with LATEST_INSIGHTS_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("latest_insights.json must contain a JSON object")

    return payload


def clean_reddit_posts(posts: Any) -> list[dict[str, Any]]:
    """Clean Reddit posts and keep only the fields used by the website."""
    cleaned_posts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not isinstance(posts, list):
        LOGGER.warning("reddit_posts is not a list; replacing with an empty list")
        return cleaned_posts

    for post in posts:
        if not isinstance(post, dict):
            continue

        post_id = str(post.get("id", "")).strip()
        title = str(post.get("title", "")).strip()

        # Skip records that cannot be identified or displayed.
        if not post_id or not title or post_id in seen_ids:
            continue

        seen_ids.add(post_id)
        cleaned_posts.append(
            {
                "id": post_id,
                "title": title,
                "score": _to_int(post.get("score")),
                "num_comments": _to_int(post.get("num_comments")),
                "url": str(post.get("url", "")),
                "created_utc": str(post.get("created_utc", "")),
            }
        )

    return cleaned_posts


def clean_steam_data(games: Any) -> list[dict[str, Any]]:
    """Clean Steam records and keep only appid, name, and player_count."""
    cleaned_games: list[dict[str, Any]] = []
    seen_appids: set[str] = set()

    if not isinstance(games, list):
        LOGGER.warning("steam_data is not a list; replacing with an empty list")
        return cleaned_games

    for game in games:
        if not isinstance(game, dict):
            continue

        appid = str(game.get("appid", "")).strip()
        name = str(game.get("name", "")).strip()

        # Skip unnamed games and duplicates by Steam app ID.
        if not appid or not name or appid in seen_appids:
            continue

        seen_appids.add(appid)
        cleaned_games.append(
            {
                "appid": appid,
                "name": name,
                "player_count": _to_int(game.get("player_count")),
            }
        )

    return cleaned_games


def clean_steam_news(news_items: Any) -> list[dict[str, Any]]:
    """Clean Steam news and keep only the fields used by the website."""
    cleaned_news: list[dict[str, Any]] = []
    seen_gids: set[str] = set()

    if not isinstance(news_items, list):
        LOGGER.warning("steam_news is not a list; replacing with an empty list")
        return cleaned_news

    for item in news_items:
        if not isinstance(item, dict):
            continue

        gid = str(item.get("gid", "")).strip()
        title = str(item.get("title", "")).strip()

        # Skip duplicates and items that cannot be shown in the UI.
        if not gid or not title or gid in seen_gids:
            continue

        seen_gids.add(gid)
        cleaned_news.append(
            {
                "gid": gid,
                "title": title,
                "url": str(item.get("url", "")),
                "author": str(item.get("author", "")),
                "contents": str(item.get("contents", "")),
                "date": _to_int(item.get("date")),
            }
        )

    return cleaned_news


def clean_reddit_comments(comments: Any) -> list[dict[str, Any]]:
    """Clean Reddit comments and remove duplicates by comment ID."""
    cleaned_comments: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not isinstance(comments, list):
        LOGGER.warning("reddit_comments is not a list; replacing with an empty list")
        return cleaned_comments

    for comment in comments:
        if not isinstance(comment, dict):
            continue
        comment_id = str(comment.get("id", "")).strip()
        body = str(comment.get("body", "")).strip()
        if not comment_id or not body or comment_id in seen_ids:
            continue
        seen_ids.add(comment_id)
        cleaned_comments.append(
            {
                "id": comment_id,
                "subreddit": str(comment.get("subreddit", "")),
                "body": body,
                "score": _to_int(comment.get("score")),
                "created_utc": float(comment.get("created_utc", 0) or 0),
                "permalink": str(comment.get("permalink", "")),
            }
        )

    return cleaned_comments


def clean_steam_reviews(reviews: Any) -> list[dict[str, Any]]:
    """Clean Steam reviews and remove duplicates by recommendation ID."""
    cleaned_reviews: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not isinstance(reviews, list):
        LOGGER.warning("steam_reviews is not a list; replacing with an empty list")
        return cleaned_reviews

    for review in reviews:
        if not isinstance(review, dict):
            continue
        recommendation_id = str(review.get("recommendationid", "")).strip()
        review_text = str(review.get("review", "")).strip()
        if not recommendation_id or recommendation_id in seen_ids:
            continue
        seen_ids.add(recommendation_id)
        cleaned_reviews.append(
            {
                "recommendationid": recommendation_id,
                "appid": str(review.get("appid", "")),
                "author_steamid": str(review.get("author_steamid", "")),
                "review": review_text,
                "voted_up": bool(review.get("voted_up", False)),
                "timestamp_created": _to_int(review.get("timestamp_created")),
                "votes_up": _to_int(review.get("votes_up")),
            }
        )

    return cleaned_reviews


def clean_official_news(news_items: Any) -> list[dict[str, Any]]:
    """Clean official news and remove duplicates by URL."""
    cleaned_news: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    if not isinstance(news_items, list):
        LOGGER.warning("official_news is not a list; replacing with an empty list")
        return cleaned_news

    for item in news_items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        if not url or not title or url in seen_urls:
            continue
        seen_urls.add(url)
        cleaned_news.append(
            {
                "source": str(item.get("source", "")),
                "title": title,
                "url": url,
                "published_at": _to_int(item.get("published_at")),
                "summary": str(item.get("summary", "")),
            }
        )

    return cleaned_news


def archive_cleaned_insights(source_file: Path) -> Path:
    """Copy the cleaned latest insights file into archive/ with a timestamp."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    archive_file = ARCHIVE_DIR / f"cleaned_insights_{timestamp}.json"

    # Reuse retry() because file copy can occasionally fail if a file is locked.
    retry(shutil.copy2, 3, 2, source_file, archive_file)
    return archive_file


def run() -> bool:
    """Clean latest_insights.json and return False instead of crashing on failure."""
    try:
        LOGGER.info("Data cleaner started")
        payload = _load_latest_insights()

        cleaned_payload = {
            "generated_at": payload.get("generated_at", ""),
            "reddit_posts": clean_reddit_posts(payload.get("reddit_posts", [])),
            "steam_data": clean_steam_data(payload.get("steam_data", [])),
            "steam_news": clean_steam_news(payload.get("steam_news", [])),
            "reddit_comments": clean_reddit_comments(payload.get("reddit_comments", [])),
            "steam_reviews": clean_steam_reviews(payload.get("steam_reviews", [])),
            "official_news": clean_official_news(payload.get("official_news", [])),
        }

        if not cleaned_payload["generated_at"]:
            send_alert(
                "Module: data_cleaner\n"
                "Error: Cleaned JSON is invalid\n"
                "Details: generated_at is missing or empty"
            )

        if (
            not any(
                cleaned_payload[field]
                for field in (
                    "reddit_posts",
                    "steam_data",
                    "steam_news",
                    "reddit_comments",
                    "steam_reviews",
                    "official_news",
                )
            )
        ):
            send_alert(
                "Module: data_cleaner\n"
                "Error: Cleaned JSON is empty\n"
                "Details: all configured data sources are empty after cleaning"
            )

        save_json(cleaned_payload, LATEST_INSIGHTS_PATH)
        archive_file = archive_cleaned_insights(LATEST_INSIGHTS_PATH)
        LOGGER.info("Cleaned insights archived to: %s", archive_file)
        LOGGER.info("Data cleaner completed successfully")
        return True
    except Exception as error:
        # Returning False lets pipeline_runner continue to health_check.run().
        LOGGER.exception("Data cleaner failed: %s", error)
        send_alert(
            "Module: data_cleaner\n"
            "Error: Data cleaner failed\n"
            f"Details: {error}"
        )
        return False


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
