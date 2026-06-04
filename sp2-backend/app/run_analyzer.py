from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from app.pipeline_config import (
        LATEST_INSIGHTS_PATH,
        LOSS_CLASSIFICATION_PATH,
        NORMALIZED_RUN_PATH,
        PIPELINE_LOG_PATH,
        RUN_ANALYSIS_PATH,
    )
    from app.utils import save_json, setup_logger
except ImportError:
    from app.pipeline_config import (
        LATEST_INSIGHTS_PATH,
        LOSS_CLASSIFICATION_PATH,
        NORMALIZED_RUN_PATH,
        PIPELINE_LOG_PATH,
        RUN_ANALYSIS_PATH,
    )
    from app.utils import save_json, setup_logger


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
LOGGER: logging.Logger = setup_logger(str(PIPELINE_LOG_PATH))

# ---------------------------------------------------------------------------
# Analysis area identifiers
# ---------------------------------------------------------------------------
AREAS: tuple[str, ...] = (
    "deck_quality",
    "defense",
    "scaling",
    "boss_readiness",
    "pathing",
    "relic_synergy",
)

# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------
GOOD_THRESHOLD = 70   # score >= 70 → "good"
WARN_THRESHOLD = 40   # 40 <= score < 70 → "warning"; below 40 → "bad"

# Deck quality constants
MIN_DECK_SIZE_ACT1 = 12
MIN_DECK_SIZE_ACT2 = 18
MAX_BASIC_RATIO = 0.25       # at most 25% basic cards is healthy
MAX_UNUPGRADED_RATIO = 0.50  # at most 50% unupgraded by Act 2+

# Defense constants
MIN_BLOCK_RATIO = 0.25       # at least 25% of deck should be block
MIN_BLOCK_UPGRADED = 0.30    # aim for 30% of block cards upgraded

# Scaling constants
MIN_SCALING_CARDS_ACT1 = 1
MIN_SCALING_CARDS_ACT2 = 2
MIN_SCALING_CARDS_ACT3 = 3

# Boss readiness constants
MIN_HP_RATIO_BOSS = 0.60     # want >= 60% HP when entering a boss

# Pathing constants
MAX_ELITES_PER_ACT = 3       # more than 3 elites per act is aggressive
MIN_HP_AFTER_REST = 0.75     # resting should bring HP above 75%

# Relic constants
MIN_RELICS_PER_ACT = 4
ENERGY_RELIC_IDEAL = 1       # want at least 1 energy relic by Act 2


# ===================================================================
# Card / game knowledge lookup tables
# ===================================================================

# Cards that provide block (other than basic Defend).
_BLOCK_CARDS: dict[str, set[str]] = {
    "the silent": {
        "survivor", "dodge and roll", "backflip", "leg sweep",
        "blur", "piercing wail", "escape plan", "deflect",
    },
    "ironclad": {
        "shrug it off", "flame barrier", "ghostly armor",
        "power through", "impervious", "second wind", "rage",
        "feel no pain",
    },
    "defect": {
        "charge battery", "glacier", "reinforced body",
        "leap", "force field", "cold snap", "coolheaded",
        "boot sequence",
    },
    "watcher": {
        "protect", "deceive reality", "sanctity", "perseverance",
        "halt", "wave of the hand",
    },
}

# Cards that provide scaling (damage that grows over time).
_SCALING_CARDS: dict[str, set[str]] = {
    "the silent": {
        "noxious fumes", "catalyst", "footwork", "after image",
        "thousand cuts", "envenom", "wraith form", "phantasmal killer",
        "accuracy", "terror", "well-laid plans", "corpse explosion",
    },
    "ironclad": {
        "demon form", "barricade", "juggernaut", "feel no pain",
        "dark embrace", "corruption", "inflame", "spot weakness",
        "rupture", "evolve", "fire breathing", "limit break",
    },
    "defect": {
        "echo form", "creative ai", "defragment", "capacitor",
        "biased cognition", "loop", "consume", "storm",
        "static discharge", "heatsinks",
    },
    "watcher": {
        "devotion", "fasting", "wish", "blasphemy", "worship",
        "mental fortress", "rushdown", "talk to the hand",
    },
}

# Energy relics — relics that give extra energy per turn.
_ENERGY_RELICS: set[str] = {
    "coffee dripper", "cursed key", "fusion hammer",
    "philosopher's stone", "runic dome", "sozu", "busted crown",
    "velvet choker",
}

# Energy utility relics — ones that help with energy in other ways.
_ENERGY_UTILITY_RELICS: set[str] = {
    "happy flower", "sundial", "lantern", "nunchaku",
    "ancient tea set", "art of war",
}

# Scaling-support relics.
_SCALING_RELICS: set[str] = {
    "snecko skull", "specimen", "twisted funnel",
    "brimstone", "champions belt",
    "data disk", "gold plated cables", "inserter",
    "damaru", "violet lotus",
    "kunai", "shuriken", "ornamental fan", "girya", "vajra",
}

# Boss-specific advice — known threats to watch for.
_BOSS_THREATS: dict[str, str] = {
    "the collector": (
        "The Collector summons torch-head minions that apply Mega Debuff. "
        "If you can't clear them quickly the debuff stacking leads to "
        "unblockable burst damage. AoE or fast single-target damage helps."
    ),
    "slime boss": (
        "Slime Boss splits into smaller slimes. Front-loaded damage "
        "during the split turn is critical, and AoE helps clean up."
    ),
    "the guardian": (
        "The Guardian alternates between defensive mode (thorns) and "
        "attack mode. Scale during defensive phases, block during attacks."
    ),
    "hexaghost": (
        "Hexaghost's turn-2 Inferno scales with your current HP. "
        "Entering at lower HP makes the attack weaker — counterintuitively "
        "you don't always want to heal before this fight."
    ),
    "bronze automaton": (
        "Bronze Automaton steals one card per turn and has a devastating "
        "Hyper Beam. Build a deck that can afford losing a random card."
    ),
    "the champ": (
        "The Champ cleanses debuffs and executes a huge attack at half HP. "
        "Scale to the point you can burst from 50% to 0 in one cycle."
    ),
    "time eater": (
        "Time Eater ends your turn after 12 cards. Avoid spam-heavy decks; "
        "prioritise high-impact cards over many cheap ones."
    ),
    "donu and deca": (
        "Donu buffs Strength and Deca adds Block. Kill Donu first "
        "unless Deca is about to block. Scaling AoE is very valuable."
    ),
    "awakened one": (
        "The Awakened One has two phases. Powers played in phase 1 give "
        "it Strength in phase 2 — either hold powers for phase 2 or "
        "ensure you can out-scale the strength gain."
    ),
}


# ===================================================================
# Internal helpers
# ===================================================================


def _parse_iso_timestamp(value: Any) -> str:
    """Parse various timestamp formats into an ISO 8601 string."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        return value
    return datetime.now(timezone.utc).isoformat()


def _expand_deck(deck: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand a compact deck list into one entry per card copy.

    Example: [{"name": "Strike", "count": 4}] → four separate entries.
    """
    flat: list[dict[str, Any]] = []
    for card in deck:
        count = card.get("count", 1)
        for _ in range(count):
            flat.append(
                {"name": card["name"], "upgraded": card.get("upgraded", False)}
            )
    return flat


def _basic_card_names() -> set[str]:
    """Return the set of card names considered 'basic' (starter cards)."""
    basics = {"strike", "defend"}
    # Add character-specific basics
    basics.update({"survivor", "neutralize", "bash", "zap", "dualcast",
                    "eruption", "vigilance", "ascender's bane"})
    return basics


# ===================================================================
# Area analysis functions — each returns a score-dict
# ===================================================================


def _analyze_deck_quality(
    run: dict[str, Any],
    flat_deck: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score the overall quality of the deck — size, upgrades, basics."""
    floor = run["floor"]
    total = len(flat_deck)
    evidence: list[str] = []
    score = 100
    basic_names = _basic_card_names()

    # --- 1. Deck size -------------------------------------------------
    if floor <= 17:       # Act 1
        if total < MIN_DECK_SIZE_ACT1:
            penalty = (MIN_DECK_SIZE_ACT1 - total) * 8
            score -= min(penalty, 30)
            evidence.append(
                f"Deck has {total} cards — small for Act 1 "
                f"(recommend ≥ {MIN_DECK_SIZE_ACT1})"
            )
    else:                  # Act 2+
        if total < MIN_DECK_SIZE_ACT2:
            penalty = (MIN_DECK_SIZE_ACT2 - total) * 5
            score -= min(penalty, 25)
            evidence.append(
                f"Deck has only {total} cards by floor {floor} "
                f"(recommend ≥ {MIN_DECK_SIZE_ACT2} for Act 2+)"
            )

    # --- 2. Basic card ratio ------------------------------------------
    basic_count = sum(1 for c in flat_deck if c["name"].lower() in basic_names)
    basic_ratio = basic_count / max(total, 1)
    if basic_ratio > MAX_BASIC_RATIO:
        penalty = int((basic_ratio - MAX_BASIC_RATIO) * 100)
        score -= min(penalty, 30)
        evidence.append(
            f"{basic_count}/{total} cards are basic starters "
            f"({basic_ratio:.0%}) — these dilute every draw"
        )
    else:
        evidence.append(
            f"Basic card ratio is healthy ({basic_count}/{total} = {basic_ratio:.0%})"
        )

    # --- 3. Upgrade ratio ---------------------------------------------
    upgraded = sum(1 for c in flat_deck if c["upgraded"])
    upgraded_ratio = upgraded / max(total, 1)
    if floor >= HIGH_FLOOR_THRESHOLD and upgraded_ratio < 0.40:
        penalty = int((0.40 - upgraded_ratio) * 80)
        score -= min(penalty, 25)
        evidence.append(
            f"Only {upgraded}/{total} cards upgraded ({upgraded_ratio:.0%}) "
            f"by floor {floor} — missed upgrade opportunities"
        )
    elif upgraded_ratio >= 0.50:
        evidence.append(
            f"Solid upgrade coverage: {upgraded}/{total} upgraded ({upgraded_ratio:.0%})"
        )

    # Clamp and determine status.
    score = max(0, min(100, score))
    status = _status(score)
    return {
        "score": score,
        "status": status,
        "explanation": _deck_quality_explanation(score, total, basic_ratio, upgraded_ratio, floor),
        "evidence": evidence,
    }


def _analyze_defense(
    run: dict[str, Any],
    flat_deck: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess whether the deck can block enough damage."""
    character = run["character"].lower()
    total = len(flat_deck)
    evidence: list[str] = []
    score = 100

    block_set = _BLOCK_CARDS.get(character, set())
    # Collect all block-card entries (including basic Defend).
    block_cards = [
        c for c in flat_deck
        if c["name"].lower() in block_set or c["name"].lower() == "defend"
    ]
    block_count = len(block_cards)
    block_ratio = block_count / max(total, 1)

    # --- 1. Block ratio -----------------------------------------------
    if block_ratio < MIN_BLOCK_RATIO:
        penalty = int((MIN_BLOCK_RATIO - block_ratio) * 150)
        score -= min(penalty, 35)
        evidence.append(
            f"Only {block_count}/{total} cards provide block "
            f"({block_ratio:.0%}) — below {MIN_BLOCK_RATIO:.0%} minimum"
        )
    else:
        evidence.append(
            f"Block card count is adequate: {block_count}/{total} ({block_ratio:.0%})"
        )

    # --- 2. Block upgrades --------------------------------------------
    block_upgraded = sum(1 for c in block_cards if c["upgraded"])
    block_up_ratio = block_upgraded / max(block_count, 1)
    if block_count >= 3 and block_up_ratio < MIN_BLOCK_UPGRADED:
        penalty = int((MIN_BLOCK_UPGRADED - block_up_ratio) * 40)
        score -= min(penalty, 15)
        evidence.append(
            f"Only {block_upgraded}/{block_count} block cards upgraded "
            f"({block_up_ratio:.0%}) — upgraded block is much more efficient"
        )

    # --- 3. Block diversity -------------------------------------------
    unique_block = len(set(c["name"].lower() for c in block_cards))
    if unique_block < 2 and block_count >= 4:
        score -= 10
        evidence.append("Low block card diversity — consider more varied block sources")

    score = max(0, min(100, score))
    status = _status(score)
    return {
        "score": score,
        "status": status,
        "explanation": _defense_explanation(score, block_count, total, block_upgraded),
        "evidence": evidence,
    }


def _analyze_scaling(
    run: dict[str, Any],
    flat_deck: list[dict[str, Any]],
) -> dict[str, Any]:
    """Determine whether the deck can out-scale late-game fights."""
    character = run["character"].lower()
    floor = run["floor"]
    total = len(flat_deck)
    evidence: list[str] = []
    score = 100

    scaling_set = _SCALING_CARDS.get(character, set())
    flat_names_lower = [c["name"].lower() for c in flat_deck]
    scaling_found = [n for n in flat_names_lower if n in scaling_set]
    unique_scaling = len(set(scaling_found))
    total_scaling = len(scaling_found)

    # --- 1. Scaling card count vs act --------------------------------
    if floor <= 17:   # Act 1
        if unique_scaling < MIN_SCALING_CARDS_ACT1:
            # In Act 1 this is less critical — small penalty.
            score -= 10
            evidence.append(
                f"No scaling cards yet — reasonable for Act 1, "
                f"but start looking for {character.title()} scaling picks"
            )
    elif floor <= 25:  # Act 2
        if unique_scaling < MIN_SCALING_CARDS_ACT2:
            penalty = (MIN_SCALING_CARDS_ACT2 - unique_scaling) * 20
            score -= min(penalty, 30)
            evidence.append(
                f"Only {unique_scaling} scaling card(s) in Act 2 "
                f"— bosses will out-scale you without more"
            )
    else:              # Act 3
        if unique_scaling < MIN_SCALING_CARDS_ACT3:
            penalty = (MIN_SCALING_CARDS_ACT3 - unique_scaling) * 25
            score -= min(penalty, 40)
            evidence.append(
                f"Only {unique_scaling} scaling card(s) in Act 3 "
                f"— end-game fights require strong scaling"
            )
        elif unique_scaling >= MIN_SCALING_CARDS_ACT3:
            evidence.append(
                f"Scaling suite looks good: {unique_scaling} unique scaling cards "
                f"({total_scaling} total copies)"
            )

    # --- 2. Scaling reliability (copies vs unique) --------------------
    if unique_scaling == 1 and total_scaling == 1 and floor >= HIGH_FLOOR_THRESHOLD:
        score -= 15
        evidence.append(
            "Only one copy of a single scaling card — you risk never drawing it"
        )

    score = max(0, min(100, score))
    status = _status(score)
    return {
        "score": score,
        "status": status,
        "explanation": _scaling_explanation(score, unique_scaling, total_scaling, character, floor),
        "evidence": evidence,
    }


def _analyze_boss_readiness(run: dict[str, Any]) -> dict[str, Any]:
    """Check how prepared the player was for the final boss."""
    boss = run["boss"]
    floor = run["floor"]
    max_hp = run["max_hp"]
    path: list[dict[str, Any]] = run["path"]
    evidence: list[str] = []
    score = 100

    # --- 1. HP going into the final boss ------------------------------
    boss_steps = [s for s in path if s["type"] == "boss"]
    if boss_steps:
        last_boss = boss_steps[-1]
        boss_idx = path.index(last_boss)
        hp_before = path[boss_idx - 1]["hp_after"] if boss_idx > 0 else max_hp
        hp_ratio = hp_before / max_hp
        if hp_ratio < MIN_HP_RATIO_BOSS:
            penalty = int((MIN_HP_RATIO_BOSS - hp_ratio) * 100)
            score -= min(penalty, 25)
            evidence.append(
                f"Entered {boss} with only {hp_before}/{max_hp} HP "
                f"({hp_ratio:.0%}) — wanted ≥ {MIN_HP_RATIO_BOSS:.0%}"
            )
        else:
            evidence.append(
                f"Entered boss fight with healthy {hp_before}/{max_hp} HP "
                f"({hp_ratio:.0%})"
            )

    # --- 2. Known boss threat match -----------------------------------
    boss_lower = boss.lower()
    if boss_lower in _BOSS_THREATS:
        # We have specific advice — check if the deck addresses it.
        evidence.append(f"Boss insight: {_BOSS_THREATS[boss_lower]}")
        # No penalty; just surface the tip for human review.
    else:
        evidence.append(f"No specific boss tips recorded for {boss}.")

    score = max(0, min(100, score))
    status = _status(score)
    return {
        "score": score,
        "status": status,
        "explanation": _boss_readiness_explanation(score, boss, hp_ratio if boss_steps else 0),
        "evidence": evidence,
    }


def _analyze_pathing(run: dict[str, Any]) -> dict[str, Any]:
    """Evaluate path choices: elites, rests, HP management."""
    path: list[dict[str, Any]] = run["path"]
    floor = run["floor"]
    max_hp = run["max_hp"]
    evidence: list[str] = []
    score = 100

    # --- 1. Count elites and types per act ----------------------------
    act1_elites = sum(1 for s in path if s["type"] == "elite" and s["floor"] <= 17)
    act2_elites = sum(1 for s in path if s["type"] == "elite" and 18 <= s["floor"] <= 33)
    act3_elites = sum(1 for s in path if s["type"] == "elite" and s["floor"] > 33)

    if act1_elites > MAX_ELITES_PER_ACT:
        penalty = (act1_elites - MAX_ELITES_PER_ACT) * 10
        score -= min(penalty, 20)
        evidence.append(
            f"Act 1: {act1_elites} elites fought — more than the "
            f"recommended {MAX_ELITES_PER_ACT} may bleed too much HP"
        )
    if act2_elites > MAX_ELITES_PER_ACT:
        penalty = (act2_elites - MAX_ELITES_PER_ACT) * 10
        score -= min(penalty, 20)
        evidence.append(
            f"Act 2: {act2_elites} elites fought — Act 2 elites are "
            f"especially dangerous"
        )

    if act1_elites <= MAX_ELITES_PER_ACT and act2_elites <= MAX_ELITES_PER_ACT:
        evidence.append("Elite pathing was reasonable across acts")

    # --- 2. HP after rest sites ---------------------------------------
    rests = [s for s in path if s["type"] == "rest"]
    low_rests = 0
    for rest in rests:
        hp_after = rest["hp_after"]
        if hp_after < max_hp * MIN_HP_AFTER_REST:
            low_rests += 1
    if low_rests >= 2:
        score -= 10
        evidence.append(
            f"{low_rests} rest sites left HP below "
            f"{MIN_HP_AFTER_REST:.0%} — pathing may be too greedy"
        )

    # --- 3. Late-game HP trend ----------------------------------------
    # Check the last 5 combat/elite floors for consistent HP drain.
    combat_steps = [s for s in path if s["type"] in ("combat", "elite")]
    if len(combat_steps) >= 5:
        last5 = combat_steps[-5:]
        hp_values = [s["hp_after"] for s in last5]
        if hp_values and max(hp_values) - min(hp_values) > max_hp * 0.4:
            score -= 10
            evidence.append("HP swung wildly in late-game combats — inconsistent defense")

    score = max(0, min(100, score))
    status = _status(score)
    return {
        "score": score,
        "status": status,
        "explanation": _pathing_explanation(score, act1_elites, act2_elites),
        "evidence": evidence,
    }


def _analyze_relic_synergy(run: dict[str, Any]) -> dict[str, Any]:
    """Check whether relics support the deck's game plan."""
    relics: list[str] = run.get("relics", [])
    floor = run["floor"]
    character = run["character"].lower()
    evidence: list[str] = []
    score = 100

    relic_lower = [r.lower() for r in relics]

    # --- 1. Relic count benchmark -------------------------------------
    expected = max(1, floor // 2)
    if len(relics) < expected * 0.5:
        penalty = int((expected * 0.5 - len(relics)) * 10)
        score -= min(penalty, 20)
        evidence.append(
            f"Only {len(relics)} relics by floor {floor} "
            f"(expect ~{expected}) — fewer elites/events taken"
        )
    else:
        evidence.append(f"Relic count is on par: {len(relics)} relics by floor {floor}")

    # --- 2. Energy economy --------------------------------------------
    has_energy = any(r in _ENERGY_RELICS for r in relic_lower)
    has_utility = any(r in _ENERGY_UTILITY_RELICS for r in relic_lower)
    if floor >= 25 and not has_energy and not has_utility:
        score -= 20
        evidence.append(
            "No energy relic or energy-generating relic by Act 3 — "
            "4 energy/turn may be insufficient"
        )
    elif has_energy:
        evidence.append("Has an energy relic — energy economy is solid")
    elif has_utility:
        evidence.append("Has energy-utility relics — partial energy support")

    # --- 3. Scaling relic synergy -------------------------------------
    has_scaling_relic = any(r in _SCALING_RELICS for r in relic_lower)
    deck = run.get("deck", [])
    flat_names = []
    for card in deck:
        flat_names.extend([card["name"].lower()] * card.get("count", 1))
    scaling_set = _SCALING_CARDS.get(character, set())
    has_scaling_cards = any(n in scaling_set for n in flat_names)

    if has_scaling_cards and not has_scaling_relic:
        score -= 10
        evidence.append(
            "Deck has scaling cards but no scaling-support relics — "
            "relics could amplify the strategy"
        )
    if has_scaling_cards and has_scaling_relic:
        evidence.append("Scaling cards are backed by scaling relics — good synergy")

    score = max(0, min(100, score))
    status = _status(score)
    return {
        "score": score,
        "status": status,
        "explanation": _relic_explanation(score, len(relics), has_energy, has_scaling_relic),
        "evidence": evidence,
    }


# ===================================================================
# Explanation builders — one per area
# ===================================================================


def _status(score: int) -> str:
    """Map numeric score to a status label."""
    if score >= GOOD_THRESHOLD:
        return "good"
    if score >= WARN_THRESHOLD:
        return "warning"
    return "bad"


def _deck_quality_explanation(
    score: int, total: int, basic_ratio: float, upgraded_ratio: float, floor: int
) -> str:
    if score >= GOOD_THRESHOLD:
        return (
            f"Deck quality is solid. {total} cards with good upgrade coverage "
            f"and a healthy basic-card ratio."
        )
    if score >= WARN_THRESHOLD:
        return (
            f"Deck is acceptable but has room to improve — consider removing "
            f"more basic cards and prioritising upgrades at rest sites."
        )
    return (
        f"Deck needs significant improvement. Too many basic cards "
        f"({basic_ratio:.0%}) and/or not enough upgrades ({upgraded_ratio:.0%}) "
        f"for floor {floor}."
    )


def _defense_explanation(
    score: int, block_count: int, total: int, upgraded_block: int
) -> str:
    if score >= GOOD_THRESHOLD:
        return (
            f"Defense is solid with {block_count} block cards — "
            f"enough to handle burst turns reliably."
        )
    if score >= WARN_THRESHOLD:
        return (
            f"Defense is functional but could falter against heavy burst. "
            f"Consider adding more block or upgrading existing block cards."
        )
    return (
        f"Defense is insufficient. Only {block_count}/{total} cards provide block "
        f"— this deck will struggle against enemies with big attack turns."
    )


def _scaling_explanation(
    score: int, unique: int, total_copies: int, character: str, floor: int
) -> str:
    char_title = character.title()
    if score >= GOOD_THRESHOLD:
        return (
            f"Scaling is well-established with {unique} unique "
            f"{char_title} scaling cards — the deck can handle long fights."
        )
    if score >= WARN_THRESHOLD:
        return (
            f"Scaling is present but could be stronger. Only {unique} unique "
            f"scaling card(s) by floor {floor} — look for more."
        )
    return (
        f"Scaling is missing or nearly missing. {char_title} needs scaling "
        f"cards to beat Act {2 if floor <= 25 else 3} bosses — "
        f"prioritise these in card rewards."
    )


def _boss_readiness_explanation(score: int, boss: str, hp_ratio: float) -> str:
    if score >= GOOD_THRESHOLD:
        return (
            f"Well-prepared for {boss}. HP was healthy going into the fight, "
            f"and the deck had tools to handle the encounter."
        )
    if score >= WARN_THRESHOLD:
        return (
            f"Somewhat underprepared for {boss}. Consider saving a potion "
            f"or planning pathing to reach the boss with higher HP."
        )
    return (
        f"Entered {boss} in poor condition (HP ratio {hp_ratio:.0%}). "
        f"Better HP management or an earlier rest stop would have helped."
    )


def _pathing_explanation(score: int, act1_elites: int, act2_elites: int) -> str:
    if score >= GOOD_THRESHOLD:
        return "Pathing was sensible — good elite/rest balance across acts."
    if score >= WARN_THRESHOLD:
        return (
            f"Pathing had some risky stretches "
            f"({act1_elites} Act 1 elites, {act2_elites} Act 2 elites). "
            f"Consider taking one fewer elite or an extra rest."
        )
    return (
        f"Pathing was too aggressive. Too many elites without enough rests "
        f"led to entering fights at dangerously low HP."
    )


def _relic_explanation(
    score: int, count: int, has_energy: bool, has_scaling_relic: bool
) -> str:
    if score >= GOOD_THRESHOLD:
        return (
            f"Relic suite is strong — {count} relics with good energy "
            f"and synergy support."
        )
    if score >= WARN_THRESHOLD:
        msg = f"Relic setup is adequate with {count} relics."
        if not has_energy:
            msg += " Missing an energy relic — prioritise boss relic picks."
        return msg
    return (
        f"Relic count ({count}) is low and key synergy/energy relics "
        f"are missing. Take more elites or shop for relics."
    )


# ===================================================================
# Meta-context loader
# ===================================================================


def _load_meta_context() -> dict[str, Any] | None:
    """Load latest_insights.json if it exists, returning community data.

    Returns None when the file is missing — the analysis can still run
    without it; it just won't include community meta-context.
    """
    if not LATEST_INSIGHTS_PATH.exists():
        LOGGER.info("Meta-context not available — %s not found", LATEST_INSIGHTS_PATH)
        return None

    try:
        with LATEST_INSIGHTS_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.warning("Could not load meta-context from %s: %s", LATEST_INSIGHTS_PATH, exc)
        return None


def _extract_meta_summary(meta: dict[str, Any]) -> dict[str, Any]:
    """Pull relevant community signals out of the meta-context blob.

    This is intentionally light-weight — we extract what's useful for
    run analysis without trying to parse every field.
    """
    summary: dict[str, Any] = {}

    # Player count for Slay the Spire specifically.
    steam_data = meta.get("steam_data", [])
    for entry in steam_data:
        if isinstance(entry, dict) and entry.get("name", "").lower() == "slay the spire":
            summary["current_players"] = entry.get("player_count", 0)
            break

    # Number of Reddit posts collected (proxy for community activity).
    reddit = meta.get("reddit_posts", [])
    summary["reddit_post_count"] = len(reddit) if isinstance(reddit, list) else 0

    # Steam news count.
    news = meta.get("steam_news", [])
    summary["steam_news_count"] = len(news) if isinstance(news, list) else 0

    return summary


# ===================================================================
# Orchestrator
# ===================================================================

HIGH_FLOOR_THRESHOLD = 17  # used across several analyzers — defined at module level


def _build_analysis(
    run: dict[str, Any],
    classification: dict[str, Any] | None,
    meta_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run every area analysis and assemble the final output dict."""
    deck: list[dict[str, Any]] = run.get("deck", [])
    flat_deck = _expand_deck(deck)

    # Score each area.
    scores: dict[str, dict[str, Any]] = {
        "deck_quality": _analyze_deck_quality(run, flat_deck),
        "defense": _analyze_defense(run, flat_deck),
        "scaling": _analyze_scaling(run, flat_deck),
        "boss_readiness": _analyze_boss_readiness(run),
        "pathing": _analyze_pathing(run),
        "relic_synergy": _analyze_relic_synergy(run),
    }

    # Collect problems (areas scored "bad" or "warning").
    problems: list[dict[str, Any]] = []
    all_evidence: list[str] = []
    for area_name, area_data in scores.items():
        if area_data["status"] in ("bad", "warning"):
            problems.append({
                "area": area_name,
                "score": area_data["score"],
                "status": area_data["status"],
                "summary": area_data["explanation"],
            })
        all_evidence.extend(area_data["evidence"])

    # If classification is available, inject its reasons.
    main_reason = ""
    if classification:
        main_reason = classification.get("main_loss_reason", "")
        class_evidence = classification.get("evidence", [])
        # Merge classification evidence without duplicating.
        for item in class_evidence:
            if item not in all_evidence:
                all_evidence.append(item)

    # Build meta-context section.
    meta_context_used = meta_summary is not None
    if meta_summary:
        all_evidence.append(
            f"Meta-context: {meta_summary.get('current_players', '?')} "
            f"current players, {meta_summary.get('reddit_post_count', 0)} "
            f"Reddit posts, {meta_summary.get('steam_news_count', 0)} "
            f"Steam news items"
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "character": run.get("character", ""),
        "floor": run.get("floor", 0),
        "boss": run.get("boss", ""),
        "main_loss_reason": main_reason,
        "scores": scores,
        "problems": problems,
        "evidence": all_evidence,
        "meta_context_used": meta_context_used,
    }


# ===================================================================
# Public entry point
# ===================================================================


def run() -> dict[str, Any] | None:
    """Analyse the player's run and produce a structured report.

    Reads ``data/normalized_run.json`` and optionally
    ``data/loss_classification.json`` and ``data/latest_insights.json``,
    then writes the full analysis to ``data/run_analysis.json``.

    Returns the analysis dict, or ``None`` when the core input is missing.
    """
    LOGGER.info("Run analyzer started")

    # --- 1. Guard: missing required input ------------------------------
    if not NORMALIZED_RUN_PATH.exists():
        LOGGER.warning("SKIPPED_CONFIG missing %s", NORMALIZED_RUN_PATH)
        print(f"SKIPPED: {NORMALIZED_RUN_PATH} not found — nothing to analyze.")
        return None

    # --- 2. Load normalized run ----------------------------------------
    try:
        with NORMALIZED_RUN_PATH.open("r", encoding="utf-8") as fh:
            run_data: dict[str, Any] = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.error("Failed to read %s: %s", NORMALIZED_RUN_PATH, exc)
        print(f"ERROR: cannot read {NORMALIZED_RUN_PATH}.")
        return None

    # --- 3. Load loss classification (optional) ------------------------
    classification: dict[str, Any] | None = None
    if LOSS_CLASSIFICATION_PATH.exists():
        try:
            with LOSS_CLASSIFICATION_PATH.open("r", encoding="utf-8") as fh:
                classification = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning(
                "Could not load loss classification from %s: %s",
                LOSS_CLASSIFICATION_PATH, exc,
            )

    # --- 4. Load meta-context (optional) -------------------------------
    meta = _load_meta_context()
    meta_summary = _extract_meta_summary(meta) if meta else None

    # --- 5. Run analysis -----------------------------------------------
    analysis = _build_analysis(run_data, classification, meta_summary)

    # --- 6. Persist ----------------------------------------------------
    save_json(analysis, RUN_ANALYSIS_PATH)
    overall = _compute_overall(analysis["scores"])
    LOGGER.info(
        "Run analyzer completed — overall_score=%s problems=%s meta=%s",
        overall,
        len(analysis["problems"]),
        analysis["meta_context_used"],
    )
    print(
        f"Analysis complete: overall score {overall}/100. "
        f"{len(analysis['problems'])} problem area(s) found. "
        f"Output → {RUN_ANALYSIS_PATH}"
    )

    return analysis


def _compute_overall(scores: dict[str, dict[str, Any]]) -> int:
    """Calculate a weighted overall score from the six area scores."""
    if not scores:
        return 0

    # Equal weighting across all six areas.
    total = sum(area["score"] for area in scores.values())
    return round(total / len(scores))


# ---------------------------------------------------------------------------
# Direct execution:  python backend/run_analyzer.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
