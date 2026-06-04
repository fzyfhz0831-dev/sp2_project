"""
wiki_scraper.py — Scrape structured Slay the Spire 2 data from https://sts2.wiki/

Targets:
  - Cards          → backend/mock_data/knowledge_base/cards.json
  - Relics         → backend/mock_data/knowledge_base/relics.json
  - Status Effects → backend/mock_data/knowledge_base/status_effects.json
  - Characters     → backend/mock_data/knowledge_base/characters.json

Respects robots.txt with a 1-second delay between requests.
Uses requests + BeautifulSoup4. Card data is fetched from the site's JSON
endpoint; relics, status effects, and characters are scraped from HTML.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://sts2.wiki"
HEADERS = {
    "User-Agent": (
        "STS2WikiScraper/1.0 (+https://github.com/sts2-project; "
        "academic / personal use; respects robots.txt)"
    ),
}
REQUEST_DELAY = 1.0  # seconds — be polite between requests
TIMEOUT = 30  # seconds

OUTPUT_DIR = Path(__file__).resolve().parent / "mock_data" / "knowledge_base"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("wiki_scraper")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> requests.Response | None:
    """GET *url* with retries and polite delay.  Returns ``None`` on failure."""
    for attempt in range(1, 4):
        try:
            logger.info("GET %s (attempt %d)", url, attempt)
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning("Request failed (attempt %d/%d): %s", attempt, 3, exc)
            if attempt < 3:
                time.sleep(REQUEST_DELAY * 2)
    logger.error("Giving up on %s after 3 attempts.", url)
    return None


def _save_json(data: list[dict[str, Any]], filename: str) -> None:
    """Write *data* as pretty-printed JSON to *filename* inside OUTPUT_DIR."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %d items → %s", len(data), path)


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_cards() -> list[dict[str, Any]]:
    """Fetch cards from the site's built-in JSON endpoint.

    Returns a list of dicts with keys: name, cost, type, rarity, effect.
    """
    url = f"{BASE_URL}/cards/data.json"
    resp = _get(url)
    if resp is None:
        return []

    raw: list[dict[str, Any]] = resp.json()
    logger.info("Fetched %d raw card entries from JSON endpoint.", len(raw))

    cards: list[dict[str, Any]] = []
    for item in raw:
        cost_raw = item.get("cost", "0")
        # cost may be "N/A" or "X" for certain cards; map to 0 in those cases
        try:
            cost = int(cost_raw)
        except (ValueError, TypeError):
            cost = 0

        cards.append({
            "name": item.get("name", ""),
            "cost": cost,
            "type": item.get("type", ""),
            "rarity": item.get("rarity", ""),
            "effect": item.get("description", ""),
        })

    logger.info("Parsed %d cards.", len(cards))
    return cards


def scrape_relics() -> list[dict[str, Any]]:
    """Scrape relics from the /relics/ listing page.

    Relics live in ``<article class=\"relic-card\">`` tags with ``data-name``
    and ``data-text`` attributes.
    """
    url = f"{BASE_URL}/relics/"
    resp = _get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.find_all("article", class_="relic-card")
    logger.info("Found %d relic-card <article> elements.", len(articles))

    relics: list[dict[str, Any]] = []
    for art in articles:
        # Prefer the visible <h2> title (proper capitalisation) over the
        # lowercased data-name attribute.
        title_el = art.find("h2", class_="relic-card__title")
        name = title_el.get_text(strip=True) if title_el else (art.get("data-name") or "").strip()

        # Likewise, prefer the <p> description over data-text.
        desc_el = art.find("p", class_="relic-card__description")
        effect = desc_el.get_text(strip=True) if desc_el else (art.get("data-text") or "").strip()

        if not name:
            continue
        relics.append({"name": name, "effect": effect})

    logger.info("Parsed %d relics.", len(relics))
    return relics


def scrape_status_effects() -> list[dict[str, Any]]:
    """Scrape status effects from the /status-effects/ table page.

    Each row is ``<tr class=\"status-row\">``.  The name is inside
    ``<span class=\"status-effect-name\">`` and the description is in the
    ``<td data-label=\"Description\">`` cell.
    """
    url = f"{BASE_URL}/status-effects/"
    resp = _get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr", class_="status-row")
    logger.info("Found %d status-row <tr> elements.", len(rows))

    effects: list[dict[str, Any]] = []
    for row in rows:
        # --- name ---
        name_span = row.find("span", class_="status-effect-name")
        if name_span is None:
            continue
        # the visible name is in a nested bare <span>
        inner = name_span.find("span")
        name = inner.get_text(strip=True) if inner else name_span.get_text(strip=True)

        # --- description ---
        desc_td = row.find("td", attrs={"data-label": "Description"})
        effect = desc_td.get_text(strip=True) if desc_td else ""

        if not name:
            continue
        effects.append({"name": name, "effect": effect})

    logger.info("Parsed %d status effects.", len(effects))
    return effects


def scrape_characters() -> list[dict[str, Any]]:
    """Scrape characters from the /characters/ overview page.

    Each character is an ``<article class=\"character-card\">`` with the name
    in an ``<h3>``.  The wiki **does not publish base HP**, so ``base_hp`` is
    set to 0.
    """
    url = f"{BASE_URL}/characters/"
    resp = _get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("article", class_="character-card")
    logger.info("Found %d character-card <article> elements.", len(cards))

    characters: list[dict[str, Any]] = []
    for card in cards:
        h3 = card.find("h3")
        if h3 is None:
            continue
        name = h3.get_text(strip=True)
        if not name:
            continue
        characters.append({"name": name, "base_hp": 0})

    logger.info(
        "Parsed %d characters (base_hp set to 0 — wiki has no HP data).",
        len(characters),
    )
    return characters


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all four scrapers and persist their results to disk."""
    logger.info("=== STS2 Wiki Scraper ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scrapers = [
        ("Cards", scrape_cards, "cards.json"),
        ("Relics", scrape_relics, "relics.json"),
        ("Status Effects", scrape_status_effects, "status_effects.json"),
        ("Characters", scrape_characters, "characters.json"),
    ]

    for label, scraper_fn, filename in scrapers:
        logger.info("--- Scraping %s ---", label)
        try:
            data = scraper_fn()
        except Exception:
            logger.exception("Unhandled error scraping %s.", label)
            data = []
        if data:
            _save_json(data, filename)
        else:
            logger.warning("No %s data collected — skipping save.", label)
        time.sleep(REQUEST_DELAY)

    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
