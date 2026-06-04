from __future__ import annotations

import csv
import json
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

try:
    from app.pipeline_config import DATA_DIR, LATEST_INSIGHTS_PATH, PIPELINE_LOG_PATH
    from app.utils import setup_logger
except ImportError:
    from app.pipeline_config import DATA_DIR, LATEST_INSIGHTS_PATH, PIPELINE_LOG_PATH
    from app.utils import setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
CSV_REPORT_PATH = DATA_DIR / "report.csv"
HTML_REPORT_PATH = DATA_DIR / "report.html"


def _load_latest_insights() -> dict[str, Any]:
    """Read the latest cleaned insights JSON used by the reports."""
    with LATEST_INSIGHTS_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("latest_insights.json must contain a JSON object")

    return payload


def _as_list(value: Any) -> list[dict[str, Any]]:
    """Return only dictionary items from a JSON list-like value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _write_csv_report(payload: dict[str, Any]) -> None:
    """Write a one-row CSV summary for automation dashboards."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    reddit_posts = _as_list(payload.get("reddit_posts", []))
    steam_data = _as_list(payload.get("steam_data", []))
    steam_news = _as_list(payload.get("steam_news", []))

    with CSV_REPORT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "total_reddit_posts",
                "total_steam_games",
                "total_steam_news",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "timestamp": payload.get("generated_at", ""),
                "total_reddit_posts": len(reddit_posts),
                "total_steam_games": len(steam_data),
                "total_steam_news": len(steam_news),
            }
        )


def _reddit_counts_table(reddit_posts: list[dict[str, Any]]) -> str:
    """Build an HTML table with Reddit post counts grouped by subreddit."""
    counts = Counter(str(post.get("subreddit", "unknown") or "unknown") for post in reddit_posts)
    rows = "\n".join(
        f"<tr><td>{escape(subreddit)}</td><td>{count}</td></tr>"
        for subreddit, count in counts.most_common()
    )
    return rows or "<tr><td colspan='2'>No Reddit posts available</td></tr>"


def _steam_games_table(steam_data: list[dict[str, Any]]) -> str:
    """Build an HTML table for top Steam games sorted by player count."""
    sorted_games = sorted(
        steam_data,
        key=lambda game: int(game.get("player_count", 0) or 0),
        reverse=True,
    )
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(game.get('appid', '')))}</td>"
        f"<td>{escape(str(game.get('name', '')))}</td>"
        f"<td>{int(game.get('player_count', 0) or 0)}</td>"
        "</tr>"
        for game in sorted_games
    )
    return rows or "<tr><td colspan='3'>No Steam game data available</td></tr>"


def _steam_news_table(steam_news: list[dict[str, Any]]) -> str:
    """Build an HTML table for latest Steam news sorted by date."""
    sorted_news = sorted(
        steam_news,
        key=lambda item: int(item.get("date", 0) or 0),
        reverse=True,
    )
    rows = "\n".join(
        "<tr>"
        f"<td>{int(item.get('date', 0) or 0)}</td>"
        f"<td>{escape(str(item.get('title', '')))}</td>"
        f"<td><a href='{escape(str(item.get('url', '')))}'>link</a></td>"
        "</tr>"
        for item in sorted_news
    )
    return rows or "<tr><td colspan='3'>No Steam news available</td></tr>"


def _write_html_report(payload: dict[str, Any]) -> None:
    """Write a human-readable HTML report with simple summary tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    reddit_posts = _as_list(payload.get("reddit_posts", []))
    steam_data = _as_list(payload.get("steam_data", []))
    steam_news = _as_list(payload.get("steam_news", []))

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Slay the Spire 2 Run Doctor Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #f2f2f2; }}
  </style>
</head>
<body>
  <h1>Slay the Spire 2 Run Doctor Report</h1>
  <p>Generated at: {escape(str(payload.get("generated_at", "")))}</p>

  <h2>Reddit Posts Count Per Subreddit</h2>
  <table>
    <thead><tr><th>Subreddit</th><th>Post Count</th></tr></thead>
    <tbody>{_reddit_counts_table(reddit_posts)}</tbody>
  </table>

  <h2>Top Steam Games By Player Count</h2>
  <table>
    <thead><tr><th>App ID</th><th>Name</th><th>Player Count</th></tr></thead>
    <tbody>{_steam_games_table(steam_data)}</tbody>
  </table>

  <h2>Top Steam News By Date</h2>
  <table>
    <thead><tr><th>Date</th><th>Title</th><th>URL</th></tr></thead>
    <tbody>{_steam_news_table(steam_news)}</tbody>
  </table>
</body>
</html>
"""
    HTML_REPORT_PATH.write_text(html, encoding="utf-8")


def run() -> bool:
    """Generate CSV and HTML reports from data/latest_insights.json."""
    try:
        LOGGER.info("Report generator started")
        payload = _load_latest_insights()
        _write_csv_report(payload)
        _write_html_report(payload)
        LOGGER.info("CSV report saved to %s", CSV_REPORT_PATH)
        LOGGER.info("HTML report saved to %s", HTML_REPORT_PATH)
        LOGGER.info("Report generator completed successfully")
        return True
    except Exception as error:
        LOGGER.exception("Report generator failed: %s", error)
        return False


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
