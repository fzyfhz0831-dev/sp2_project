"""
knowledge_loader.py — Lightweight cached loader for gameplay knowledge JSON files.

Loads cards.json, relics.json, bosses.json, and archetypes.json from the
app/knowledge/ directory with in-memory caching to avoid repeated file I/O.

Usage:
    from app.knowledge_loader import get_cards, get_relics, get_bosses, get_archetypes
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("knowledge_loader")

# ---------------------------------------------------------------------------
# Path resolution — knowledge files live next to this file
# ---------------------------------------------------------------------------

_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"

_KNOWLEDGE_FILES: dict[str, Path] = {
    "cards": _KNOWLEDGE_DIR / "cards.json",
    "relics": _KNOWLEDGE_DIR / "relics.json",
    "bosses": _KNOWLEDGE_DIR / "bosses.json",
    "archetypes": _KNOWLEDGE_DIR / "archetypes.json",
    "pathing": _KNOWLEDGE_DIR / "pathing.json",
}

# ---------------------------------------------------------------------------
# In-memory cache — loaded once, reused forever
# ---------------------------------------------------------------------------

_cache: dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    """Load and parse a JSON file, returning None on any failure."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Loaded knowledge: %s (%s entries)", path.name, _count(data))
        return data
    except FileNotFoundError:
        logger.warning("Knowledge file not found: %s", path)
        return None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load knowledge file %s: %s", path, exc)
        return None


def _count(data: Any) -> int:
    """Return element count for lists or dict-key-count for dicts."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(data)
    return 0


def _load_if_needed(key: str) -> Any:
    """Return cached data for *key*, loading from disk on cache miss."""
    if key in _cache:
        return _cache[key]

    path = _KNOWLEDGE_FILES.get(key)
    if path is None:
        logger.warning("Unknown knowledge key: %s", key)
        return None

    data = _load_json(path)
    _cache[key] = data
    return data


def _lookup_by_name(data: Any, name: str) -> Any:
    """Search a list of dicts for one whose 'name' matches (case-insensitive)."""
    if not isinstance(data, list):
        return None
    name_lower = name.lower()
    for item in data:
        if isinstance(item, dict) and item.get("name", "").lower() == name_lower:
            return item
    return None


def _lookup_by_character(data: dict[str, Any], character: str) -> list[dict[str, Any]]:
    """Return all cards/archetypes for a given character (case-insensitive)."""
    if not isinstance(data, dict):
        return []
    char_lower = character.lower()
    for key, value in data.items():
        if key.lower() == char_lower:
            return value if isinstance(value, list) else []
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_cards() -> list[dict[str, Any]] | None:
    """Return all card entries (flat list across all characters)."""
    return _load_if_needed("cards")


def get_card(name: str) -> dict[str, Any] | None:
    """Look up a single card by name."""
    cards = get_cards()
    return _lookup_by_name(cards, name)


def get_cards_for_character(character: str) -> list[dict[str, Any]]:
    """Return cards belonging to a character group."""
    cards = get_cards()
    if not cards:
        return []
    char_lower = character.lower()
    return [c for c in cards if c.get("character", "").lower() == char_lower]


def get_relics() -> list[dict[str, Any]] | None:
    """Return all relic entries."""
    return _load_if_needed("relics")


def get_relic(name: str) -> dict[str, Any] | None:
    """Look up a single relic by name."""
    relics = get_relics()
    return _lookup_by_name(relics, name)


def get_bosses() -> list[dict[str, Any]] | None:
    """Return all boss entries."""
    return _load_if_needed("bosses")


def get_boss(name: str) -> dict[str, Any] | None:
    """Look up a single boss by name."""
    bosses = get_bosses()
    return _lookup_by_name(bosses, name)


def get_archetypes() -> dict[str, list[dict[str, Any]]] | None:
    """Return all archetypes grouped by character."""
    return _load_if_needed("archetypes")


def get_archetypes_for_character(character: str) -> list[dict[str, Any]]:
    """Return archetypes for a specific character."""
    archetypes = get_archetypes()
    if not archetypes:
        return []
    return _lookup_by_character(archetypes, character)


def reload_knowledge() -> dict[str, bool]:
    """Clear the cache and reload all knowledge files. Returns status per key."""
    _cache.clear()
    status: dict[str, bool] = {}
    for key in _KNOWLEDGE_FILES:
        data = _load_if_needed(key)
        status[key] = data is not None
    return status


def get_pathing() -> list[dict[str, Any]] | None:
    """Return all pathing knowledge entries."""
    return _load_if_needed("pathing")


def get_pathing_for_act(act: int) -> list[dict[str, Any]]:
    """Return pathing heuristics for a specific act (1-3) or 0 for general."""
    entries = get_pathing()
    if not entries:
        return []
    return [e for e in entries if e.get("act") == act]


def is_knowledge_available() -> bool:
    """Return True if at least cards.json is loaded successfully."""
    return get_cards() is not None
