from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree

try:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, OFFICIAL_NEWS_URLS, PIPELINE_LOG_PATH
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import DATA_DIR, OFFICIAL_NEWS_URLS, PIPELINE_LOG_PATH
    from app.utils import retry, save_json, setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
OUTPUT_FILE = DATA_DIR / "official_news.json"


def _text(element: ElementTree.Element, tag: str) -> str:
    """Read text from an XML child node, returning an empty string if missing."""
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _date_to_timestamp(value: str) -> int:
    """Convert RSS date text to a Unix timestamp when possible."""
    try:
        return int(parsedate_to_datetime(value).timestamp())
    except Exception:
        return 0


def _parse_rss(source_url: str, xml_text: str) -> list[dict[str, Any]]:
    """Parse simple RSS feeds into structured news records."""
    root = ElementTree.fromstring(xml_text)
    items = root.findall(".//item")
    news: list[dict[str, Any]] = []

    for item in items:
        title = _text(item, "title")
        link = _text(item, "link")
        pub_date = _text(item, "pubDate")
        news.append(
            {
                "source": source_url,
                "title": title,
                "url": link,
                "published_at": _date_to_timestamp(pub_date),
                "summary": _text(item, "description"),
            }
        )

    return news


def fetch_official_news(urls: list[str] = OFFICIAL_NEWS_URLS) -> list[dict[str, Any]]:
    """Fetch and parse official RSS/news URLs configured in backend/config.py."""
    all_news: list[dict[str, Any]] = []

    for source_url in urls:
        def request_feed() -> list[dict[str, Any]]:
            request = Request(source_url, headers={"User-Agent": "sp2-run-doctor/1.0"})
            with urlopen(request, timeout=15) as response:
                xml_text = response.read().decode("utf-8", errors="replace")
            return _parse_rss(source_url, xml_text)

        LOGGER.info("Fetching official news from %s", source_url)
        all_news.extend(retry(request_feed, retries=3, delay=2))

    return all_news


def run() -> list[dict[str, Any]]:
    """Collect official news and save raw JSON to data/."""
    try:
        LOGGER.info("Official news collector started")
        news = fetch_official_news()
        save_json(news, OUTPUT_FILE)
        LOGGER.info("Official news collector saved %s items", len(news))
        return news
    except Exception as error:
        LOGGER.exception("Official news collector failed: %s", error)
        send_alert(
            "Module: official_news_collector\n"
            "Error: Official news collection failed\n"
            f"Details: {error}"
        )
        return []


if __name__ == "__main__":
    run()
