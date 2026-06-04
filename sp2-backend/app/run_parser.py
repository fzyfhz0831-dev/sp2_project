from __future__ import annotations

import json
from typing import Any


class RunParserError(Exception):
    """Raised when an uploaded run JSON cannot be parsed."""


def _first_value(data: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    """Return the first present, non-empty value from a list of possible keys."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _as_list(value: Any) -> list[Any]:
    """Return a list for list-like run fields, or [] when missing/invalid."""
    return value if isinstance(value, list) else []


def _extract_bosses(data: dict[str, Any], path: list[Any]) -> list[Any]:
    bosses = _first_value(data, ("bosses", "boss_relics"), [])
    if isinstance(bosses, list):
        return bosses

    single_boss = _first_value(data, ("boss", "killed_by", "final_boss"))
    if single_boss is not None:
        return [single_boss]

    path_bosses: list[Any] = []
    for step in path:
        if isinstance(step, dict) and step.get("type") == "boss":
            path_bosses.append(step.get("name") or step.get("enemy") or step.get("result"))
    return [boss for boss in path_bosses if boss is not None]


def _build_summary(parsed: dict[str, Any]) -> str:
    character = parsed.get("character") or "Unknown character"
    floor = parsed.get("floor_reached")
    victory = parsed.get("victory")
    bosses = parsed.get("bosses") or []
    card_count = len(parsed.get("cards") or [])
    relic_count = len(parsed.get("relics") or [])

    outcome = "won" if victory is True else "lost" if victory is False else "finished"
    floor_text = f"reached floor {floor}" if floor is not None else "has no recorded floor"
    boss_text = f" Bosses: {', '.join(str(boss) for boss in bosses)}." if bosses else ""

    return (
        f"{character} {outcome} and {floor_text}. "
        f"Cards: {card_count}. Relics: {relic_count}.{boss_text}"
    )


def parse_run_data(run_data: dict[str, Any]) -> dict[str, Any]:
    """Safely extract common run fields from different JSON formats."""
    if not isinstance(run_data, dict):
        raise RunParserError("Uploaded JSON must contain one JSON object.")

    path = _as_list(_first_value(run_data, ("path", "floor_path", "route")))
    parsed: dict[str, Any] = {
        "character": _first_value(run_data, ("character", "player_class", "class")),
        "floor_reached": _first_value(run_data, ("floor_reached", "floor", "floor_num")),
        "victory": _first_value(run_data, ("victory", "won", "is_victory")),
        "cards": _as_list(_first_value(run_data, ("cards", "deck", "master_deck"))),
        "relics": _as_list(_first_value(run_data, ("relics", "relic_names"))),
        "damage_taken": _as_list(_first_value(run_data, ("damage_taken", "damage", "damage_log"))),
        "path": path,
        "score": _first_value(run_data, ("score", "final_score")),
        "raw": run_data,
    }
    parsed["bosses"] = _extract_bosses(run_data, path)
    parsed["floor"] = parsed["floor_reached"]
    parsed["summary_text"] = _build_summary(parsed)

    return parsed


def _normalize_deck(cards: list[Any]) -> list[dict[str, Any]]:
    """Convert card lists into the compact deck format used by automation."""
    deck: dict[str, dict[str, Any]] = {}

    for card in cards:
        if isinstance(card, dict):
            name = str(card.get("name") or card.get("card") or "").strip()
            if not name:
                continue
            count = int(card.get("count") or 1)
            upgraded = bool(card.get("upgraded") or card.get("upgrade"))
        else:
            name = str(card).strip()
            if not name:
                continue
            count = 1
            upgraded = name.endswith("+")
            name = name.rstrip("+")

        if name not in deck:
            deck[name] = {"name": name, "upgraded": upgraded, "count": 0}
        deck[name]["count"] += count
        deck[name]["upgraded"] = deck[name]["upgraded"] or upgraded

    return list(deck.values())


def _normalize_path(path: list[Any]) -> list[dict[str, Any]]:
    """Keep path records predictable for downstream automation modules."""
    normalized_path: list[dict[str, Any]] = []

    for index, step in enumerate(path, start=1):
        if isinstance(step, dict):
            normalized_step = dict(step)
        else:
            normalized_step = {"result": str(step)}

        normalized_step.setdefault("floor", index)
        normalized_step.setdefault("type", "combat")
        normalized_step.setdefault("hp_after", normalized_step.get("hp", 0))
        normalized_path.append(normalized_step)

    return normalized_path


def normalize_for_automation(run_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize one run into the shape used by automation loss-review modules."""
    parsed = parse_run_data(run_data)
    path = _normalize_path(parsed.get("path") or [])
    bosses = parsed.get("bosses") or []

    return {
        "character": parsed.get("character") or "Unknown",
        "floor": parsed.get("floor_reached") or 0,
        "boss": bosses[-1] if bosses else _first_value(run_data, ("boss", "killed_by", "final_boss"), "unknown"),
        "hp": _first_value(run_data, ("hp", "final_hp"), 0),
        "max_hp": _first_value(run_data, ("max_hp", "maximum_hp"), 80),
        "deck": _normalize_deck(parsed.get("cards") or []),
        "relics": parsed.get("relics") or [],
        "path": path,
        "death_reason": _first_value(run_data, ("death_reason", "killed_by"), ""),
        "notes": _first_value(run_data, ("notes", "comment"), ""),
        "summary_text": parsed.get("summary_text"),
    }


def run() -> dict[str, Any] | None:
    """Automation entry point: normalize data/player_run.json when present."""
    from app.pipeline_config import NORMALIZED_RUN_PATH, PLAYER_RUN_PATH
    from app.utils import save_json

    if not PLAYER_RUN_PATH.exists():
        print(f"SKIPPED: {PLAYER_RUN_PATH} not found - nothing to parse.")
        return None

    try:
        raw_data = json.loads(PLAYER_RUN_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        print(f"ERROR: {PLAYER_RUN_PATH} contains invalid JSON.")
        return None
    except OSError:
        print(f"ERROR: cannot read {PLAYER_RUN_PATH}.")
        return None

    try:
        normalized = normalize_for_automation(raw_data)
    except RunParserError as error:
        print(f"ERROR: {error}")
        return None

    save_json(normalized, NORMALIZED_RUN_PATH)
    print(f"Run parsed: {NORMALIZED_RUN_PATH}")
    return normalized
