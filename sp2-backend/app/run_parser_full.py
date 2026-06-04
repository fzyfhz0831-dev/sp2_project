"""
run_parser.py — Load, validate, and summarise a Slay the Spire 2 run JSON file.

Functions
---------
- load_run(file_path: str) -> dict
- validate_run(run_data: dict) -> list[str]
- summarize_run(run_data: dict) -> dict

CLI usage
---------
    python backend/run_parser.py backend/mock_data/runs/mock-001-low-hp-elite.json
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_parser")

# ---------------------------------------------------------------------------
# Required fields for a valid mock run
# ---------------------------------------------------------------------------

_REQUIRED_TOP_KEYS: tuple[str, ...] = (
    "run_id",
    "character",
    "floor_reached",
    "killed_by",
    "max_hp",
    "final_hp",
    "cards",
    "relics",
    "path",
)

_REQUIRED_PATH_KEYS: tuple[str, ...] = (
    "floor",
    "type",
)

# ---------------------------------------------------------------------------
# Card type knowledge — loaded lazily from the wiki knowledge base
# ---------------------------------------------------------------------------

_CARD_TYPE_MAP: dict[str, str] | None = None


def _load_card_types() -> dict[str, str]:
    """Load card-name → type mapping from the scraped knowledge base.

    Returns a dict mapping **lowercased** card names to types
    (Attack / Skill / Power / …).  Cached after the first call.
    """
    global _CARD_TYPE_MAP
    if _CARD_TYPE_MAP is not None:
        return _CARD_TYPE_MAP

    _CARD_TYPE_MAP = {}
    kb_path = Path(__file__).resolve().parents[1] / "mock_data" / "knowledge_base" / "cards.json"
    try:
        with kb_path.open("r", encoding="utf-8") as fh:
            cards = json.load(fh)
        for card in cards:
            name = card.get("name", "")
            ctype = card.get("type", "")
            if name and ctype:
                _CARD_TYPE_MAP[name.lower()] = ctype
        logger.info("Loaded %d card types from knowledge base.", len(_CARD_TYPE_MAP))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load card-type map: %s", exc)

    return _CARD_TYPE_MAP


# ---------------------------------------------------------------------------
# load_run
# ---------------------------------------------------------------------------

def load_run(file_path: str) -> dict[str, Any]:
    """Load and parse a run JSON file.

    Parameters
    ----------
    file_path : str
        Path to a ``.json`` run file.

    Returns
    -------
    dict
        Parsed run data.

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    """
    path = Path(file_path).resolve()
    logger.info("Loading run from %s", path)

    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    logger.info("Loaded run: id=%s  character=%s  floor=%s",
                 data.get("run_id", "?"),
                 data.get("character", "?"),
                 data.get("floor_reached", "?"))
    return data


# ---------------------------------------------------------------------------
# validate_run
# ---------------------------------------------------------------------------

def validate_run(run_data: dict[str, Any]) -> list[str]:
    """Validate a run dictionary and return a list of issue descriptions.

    An empty list means the run is valid.

    Parameters
    ----------
    run_data : dict
        The parsed run data (from :func:`load_run`).

    Returns
    -------
    list[str]
        Human-readable validation issues.  Empty list → valid.
    """
    issues: list[str] = []

    # --- top-level keys ----------------------------------------------------
    for key in _REQUIRED_TOP_KEYS:
        if key not in run_data or run_data[key] is None:
            issues.append(f"Missing top-level field: '{key}'")

    # --- type checks on scalars --------------------------------------------
    if not isinstance(run_data.get("run_id"), str) or not run_data.get("run_id"):
        issues.append("'run_id' must be a non-empty string.")

    if not isinstance(run_data.get("character"), str) or not run_data.get("character"):
        issues.append("'character' must be a non-empty string.")

    for int_field in ("max_hp", "final_hp", "floor_reached"):
        val = run_data.get(int_field)
        if not isinstance(val, (int, float)):
            issues.append(f"'{int_field}' must be a number, got {type(val).__name__}.")

    if not isinstance(run_data.get("killed_by"), str):
        issues.append("'killed_by' must be a string.")

    # --- cards -------------------------------------------------------------
    cards = run_data.get("cards")
    if not isinstance(cards, list):
        issues.append("'cards' must be a list.")
    elif cards and not all(isinstance(c, str) for c in cards):
        issues.append("Every entry in 'cards' must be a string.")

    # --- relics ------------------------------------------------------------
    relics = run_data.get("relics")
    if not isinstance(relics, list):
        issues.append("'relics' must be a list.")
    elif relics and not all(isinstance(r, str) for r in relics):
        issues.append("Every entry in 'relics' must be a string.")

    # --- path --------------------------------------------------------------
    path = run_data.get("path")
    if not isinstance(path, list):
        issues.append("'path' must be a list.")
    elif len(path) == 0:
        issues.append("'path' must contain at least one floor entry.")
    else:
        for i, step in enumerate(path):
            if not isinstance(step, dict):
                issues.append(f"path[{i}] is not a dict.")
                continue
            for pk in _REQUIRED_PATH_KEYS:
                if pk not in step:
                    issues.append(f"path[{i}] is missing required key: '{pk}'")
            ftype = step.get("type", "")
            if ftype not in ("combat", "event", "elite", "shop", "rest", "boss"):
                issues.append(
                    f"path[{i}].type is '{ftype}' — expected one of: "
                    "combat, event, elite, shop, rest, boss"
                )

    # --- logical checks ----------------------------------------------------
    if isinstance(run_data.get("final_hp"), (int, float)) and run_data.get("final_hp", 0) > 0:
        issues.append("'final_hp' > 0 on a failed run — expected 0 (run ended in death).")

    if isinstance(run_data.get("floor_reached"), (int, float)) and isinstance(path, list) and path:
        last = path[-1]
        if isinstance(last, dict) and last.get("floor", 0) > run_data["floor_reached"]:
            issues.append(
                f"Last path floor ({last['floor']}) exceeds "
                f"'floor_reached' ({run_data['floor_reached']})."
            )

    if not issues:
        logger.info("Validation passed.")
    else:
        logger.warning("Validation found %d issue(s).", len(issues))

    return issues


# ---------------------------------------------------------------------------
# summarize_run
# ---------------------------------------------------------------------------

def summarize_run(run_data: dict[str, Any]) -> dict[str, Any]:
    """Produce a structured summary with risk-flag analysis.

    Parameters
    ----------
    run_data : dict
        The parsed run data.

    Returns
    -------
    dict
        Summary with keys: character, floor_reached, killed_by,
        final_deck_size, relic_count, elite_count, boss_count,
        lowest_hp_floor, possible_risk_flags.
    """
    cards: list[str] = run_data.get("cards", [])
    relics: list[str] = run_data.get("relics", [])
    path: list[dict[str, Any]] = run_data.get("path", [])
    max_hp: int = int(run_data.get("max_hp", 80))

    # --- basic counts ------------------------------------------------------
    elite_count = sum(1 for p in path if p.get("type") == "elite")
    boss_count = sum(1 for p in path if p.get("type") == "boss")

    # --- lowest HP floor ---------------------------------------------------
    lowest_hp = max_hp
    lowest_floor = 0
    for p in path:
        hp_after = p.get("hp_after")
        if isinstance(hp_after, (int, float)) and hp_after < lowest_hp:
            lowest_hp = int(hp_after)
            lowest_floor = int(p.get("floor", 0))

    # --- risk flags --------------------------------------------------------
    flags: list[str] = []

    # 1. low_hp_before_elite — entered any elite below 50 % max HP.
    for p in path:
        if p.get("type") == "elite":
            hp_before = p.get("hp_before", max_hp)
            if isinstance(hp_before, (int, float)) and hp_before < max_hp * 0.5:
                flags.append("low_hp_before_elite")
                break

    # 2. poor_defense_hint — deck has few block-oriented cards relative to
    #    attacks.  Uses the card-type knowledge base when available, falling
    #    back to keyword heuristics for unrecognised names.
    ctype_map = _load_card_types()

    # --- keyword heuristics for fallback classification --------------------
    _ATTACK_KW = (
        "strike", "slash", "blade", "bolt", "beam", "cut", "fury", "rage",
        "bash", "cleave", "carnage", "whirlwind", "barrage", "burst",
        "arrow", "dart", "stab", "knife", "shiv", "uppercut", "heavy",
        "sunder", "melter", "streamline", "hyperbeam", "ball lightning",
        "compile driver", "go for the eyes", "scrape", "dualcast",
        "assassinate", "bane", "choke", "dagger", "die die die",
        "eviscerate", "finisher", "flechettes", "glass knife",
        "masterful stab", "neutralize", "riddle with holes", "skewer",
        "slice", "sucker punch", "unload", "celestial arrow",
        "divine strike", "falling star", "heavenly strike",
        "shooting star", "solar flare", "zenith", "supernova",
        "death grip", "doom clock", "grave rot", "phantom strike",
        "shadow bolt", "soul burn", "spectral blade", "wraith strike",
        "bone storm", "cadaver", "carrion feast", "gravedigger",
        "lich form",
    )
    _SKILL_KW = (
        "defend", "shield", "block", "barrier", "guard", "armor", "wall",
        "footwork", "dodge", "cloak", "deflect", "escape", "backflip",
        "leg sweep", "piercing wail", "survivor", "blur", "concentrate",
        "expertise", "outmaneuver", "prepared", "reflex", "tactician",
        "acrobatics", "backflip", "calculated gamble", "adrenaline",
        "alchemize", "apparition", "double energy", "equilibrium",
        "fission", "hologram", "reboot", "recycle", "seek",
        "turbo", "bloodletting", "burning pact", "offering",
        "second wind", "seeing red", "sentinel", "shrug",
        "cosmic shield", "twilight shield", "void step",
        "bone armor", "nether shield", "chill of the grave",
        "dark ritual", "life drain", "reanimate", "soul bind",
    )
    _POWER_KW = (
        "form", "inflame", "brutality", "barricade", "corruption",
        "dark embrace", "evolve", "feel no pain", "fire breathing",
        "juggernaut", "metallicize", "rupture", "combust",
        "afterimage", "envenom", "noxious fumes", "tools of the trade",
        "well laid plans", "wraith form", "thousand cuts",
        "creative ai", "echo form", "electrodynamics", "hello world",
        "machine learning", "self repair", "storm", "capacitor",
        "defragment", "heatsinks", "loop",
        "beacon of hope", "constellation", "empyrean",
        "oracle", "pillar of creation", "starlight beacon",
        "stellar core", "nova", "zenith",
        "dread presence", "unholy vigor", "wither",
        "infinite blades", "caltrops", "star align",
        "doom clock", "dark ritual", "lich form",
        "aggression", "automation", "arsenal",
    )

    def _classify_card(cname: str) -> str | None:
        """Return 'Attack' / 'Skill' / 'Power' or None."""
        base = cname.rsplit("+", 1)[0].strip().lower()
        # 1) knowledge-base lookup
        ctype = ctype_map.get(base)
        if ctype is None:
            ctype = ctype_map.get(cname.lower())
        if ctype in ("Attack", "Skill", "Power"):
            return ctype

        # 2) keyword heuristic fallback
        low = base
        if any(kw in low for kw in _POWER_KW):
            return "Power"
        if any(kw in low for kw in _ATTACK_KW):
            return "Attack"
        if any(kw in low for kw in _SKILL_KW):
            return "Skill"

        return None

    attack_count = 0
    skill_count = 0
    power_count = 0
    for cname in cards:
        ct = _classify_card(cname)
        if ct == "Attack":
            attack_count += 1
        elif ct == "Skill":
            skill_count += 1
        elif ct == "Power":
            power_count += 1

    total_typed = attack_count + skill_count + power_count
    if total_typed >= 6 and attack_count > skill_count * 2:
        flags.append("poor_defense_hint")

    # 3. thick_deck — more than 25 cards.
    if len(cards) > 25:
        flags.append("thick_deck")

    # 4. died_to_elite — the final path entry is an elite fight.
    if path and path[-1].get("type") == "elite":
        flags.append("died_to_elite")

    # 5. no_scaling — fewer than 2 Power cards in the deck.
    if power_count < 2:
        flags.append("no_scaling")

    # 6. bad_upgrade — more than half of rest sites were used for healing
    #    (no card picked) instead of upgrading.
    rest_sites = [p for p in path if p.get("type") == "rest"]
    if len(rest_sites) >= 3:
        heal_rests = sum(
            1 for p in rest_sites
            if not p.get("picked_card") and p.get("hp_before", 0) < max_hp * 0.8
        )
        if heal_rests > len(rest_sites) / 2:
            flags.append("bad_upgrade")

    # 7. greedy_path — consecutive elites without resting, or taking far
    #    more elites than rests (especially in the first act, floor ≤ 17).
    consecutive_elites = 0
    for p in path:
        if p.get("type") == "elite":
            consecutive_elites += 1
        elif p.get("type") == "rest":
            if consecutive_elites >= 2:
                break  # already detected
            consecutive_elites = 0
    if consecutive_elites >= 2:
        flags.append("greedy_path")
    else:
        # High elite density in act 1: 3+ elites and fewer rests than elites.
        act1_elites = sum(
            1 for p in path
            if p.get("type") == "elite" and int(p.get("floor", 99)) <= 17
        )
        act1_rests = sum(
            1 for p in path
            if p.get("type") == "rest" and int(p.get("floor", 99)) <= 17
        )
        if act1_elites >= 3 and act1_rests < act1_elites:
            flags.append("greedy_path")

    # --- assemble summary --------------------------------------------------
    summary: dict[str, Any] = {
        "character": run_data.get("character", ""),
        "floor_reached": run_data.get("floor_reached", 0),
        "killed_by": run_data.get("killed_by", ""),
        "final_deck_size": len(cards),
        "relic_count": len(relics),
        "elite_count": elite_count,
        "boss_count": boss_count,
        "lowest_hp_floor": lowest_floor,
        "possible_risk_flags": flags,
    }

    logger.info("Summary: %s", json.dumps(summary, ensure_ascii=False))
    return summary


# ===================================================================
# CLI entry point (python backend/run_parser.py <path>)
# ===================================================================

def main() -> None:
    """CLI: parse a single run file and print its summary.

    Usage::

        python backend/run_parser.py backend/mock_data/runs/mock-001-low-hp-elite.json
    """
    if len(sys.argv) < 2:
        print("Usage:  python backend/run_parser.py <path_to_run.json>")
        sys.exit(1)

    file_path = sys.argv[1]

    # 1. Load
    try:
        run_data = load_run(file_path)
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {file_path}: {exc}")
        sys.exit(1)

    # 2. Validate
    issues = validate_run(run_data)
    if issues:
        print("\n[WARN] Validation issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n[OK] Validation passed.")

    # 3. Summarize
    summary = summarize_run(run_data)
    print(f"\n=== Run Summary ===")
    print(f"  Character:      {summary['character']}")
    print(f"  Floor reached:  {summary['floor_reached']}")
    print(f"  Killed by:      {summary['killed_by']}")
    print(f"  Deck size:      {summary['final_deck_size']} cards")
    print(f"  Relics:         {summary['relic_count']}")
    print(f"  Elites fought:  {summary['elite_count']}")
    print(f"  Bosses fought:  {summary['boss_count']}")
    print(f"  Lowest HP @     floor {summary['lowest_hp_floor']}")
    print(f"  Risk flags:     {summary['possible_risk_flags']}")


if __name__ == "__main__":
    main()
