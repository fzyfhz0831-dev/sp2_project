"""
rule_analyzer.py — Rule-based gameplay analysis for Slay the Spire runs.

Applies deterministic rules to parsed run JSON before AI summarization,
producing structured findings: problems, strengths, warnings, suggestions.

Integrates with the API endpoint via :func:`analyze_run_rules` so that
the AI only needs to summarize and explain the detected issues naturally.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from app.knowledge_loader import (
        get_card,
        get_relic,
        get_boss,
        get_archetypes_for_character,
        is_knowledge_available,
    )
except ImportError:
    # Graceful fallback when knowledge_loader is not importable.
    def get_card(name: str) -> Any: return None
    def get_relic(name: str) -> Any: return None
    def get_boss(name: str) -> Any: return None
    def get_archetypes_for_character(character: str) -> Any: return []
    def is_knowledge_available() -> bool: return False

logger = logging.getLogger("rule_analyzer")

# =============================================================================
# Card knowledge lookup tables
# =============================================================================

# Cards that provide block (beyond basic Defend).
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

# Cards that provide scaling — damage/block that grows over time.
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

# Cards that provide card draw or deck manipulation.
_DRAW_CARDS: dict[str, set[str]] = {
    "the silent": {
        "acrobatics", "backflip", "calculated gamble", "expertise",
        "prepared", "reflex", "tactician", "adrenaline",
        "escape plan", "dagger throw",
    },
    "ironclad": {
        "battle trance", "offering", "dark embrace", "pommel strike",
        "burning pact", "warcry",
    },
    "defect": {
        "coolheaded", "skim", "compile driver", "seek",
        "fission", "reboot", "heatsinks",
    },
    "watcher": {
        "cut through fate", "scrawl", "rushdown", "empty mind",
        "inner peace", "sanctity",
    },
}

# Cards that cost 2+ energy (expensive).
_EXPENSIVE_CARDS: set[str] = {
    "dash", "leg sweep", "crippling cloud", "predator",
    "flame barrier", "impervious", "shockwave", "clothesline",
    "uppercut", "carnage",
    "glacier", "reinforced body", "echo form", "creative ai",
    "electrodynamics", "meteor strike", "sunder",
    "wish", "worship", "blasphemy", "ragnarok",
    "die die die", "unload", "storm of steel",
    "bludgeon", "barricade", "juggernaut", "demonic form",
    "wraith form", "nightmare", "corpse explosion",
    "wreath of flame", "equilibrium",
}

# Energy relics.
_ENERGY_RELICS: set[str] = {
    "coffee dripper", "cursed key", "fusion hammer",
    "philosopher's stone", "runic dome", "sozu", "busted crown",
    "velvet choker", "slaver's collar", "nuclear battery",
    "hovering kite", "violet lotus", "mark of pain",
}

# Energy utility relics.
_ENERGY_UTILITY_RELICS: set[str] = {
    "happy flower", "sundial", "lantern", "nunchaku",
    "ancient tea set", "art of war", "mummified hand",
}

# Scaling-support relics.
_SCALING_RELICS: set[str] = {
    "snecko skull", "specimen", "twisted funnel",
    "brimstone", "champions belt",
    "data disk", "gold plated cables", "inserter",
    "damaru", "violet lotus",
    "kunai", "shuriken", "ornamental fan", "girya", "vajra",
}

# Relics that help with defense/HP.
_DEFENSIVE_RELICS: set[str] = {
    "anchor", "horn cleat", "captain's wheel", "fossilized helix",
    "incense burner", "tungsten rod", "torii", "self-forming clay",
    "blood vial", "eternal feather", "meat on the bone",
    "pantograph", "singing bowl", "cleric face",
    "bronze scales", "mercury hourglass",
}

# =============================================================================
# Constants
# =============================================================================

ACT_1_MAX_FLOOR = 17
ACT_2_MAX_FLOOR = 33

MIN_BLOCK_RATIO = 0.22
MIN_DRAW_CARDS = 2
HIGH_COST_MAX_RATIO = 0.30
MAX_BASIC_RATIO = 0.25
MIN_SCALING_ACT2 = 2
MIN_SCALING_ACT3 = 3
MIN_HP_RATIO_BOSS = 0.55
MAX_ELITES_PER_ACT = 3
DECK_CONSISTENCY_MIN = 15  # want at least 15 non-basic cards by Act 2
MAX_DECK_BLOAT = 35

# =============================================================================
# Internal helpers
# =============================================================================


def _normalize_card_list(cards: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize cards into (compact deck list, flat name list).

    Handles both flat-string card lists and dict-with-count decks.
    """
    compact: list[dict[str, Any]] = []
    flat_names: list[str] = []

    for card in cards:
        if isinstance(card, str):
            name = card.rstrip("+")
            upgraded = card.endswith("+")
            compact.append({"name": name, "upgraded": upgraded, "count": 1})
            flat_names.append(name.lower())
        elif isinstance(card, dict):
            name = str(card.get("name") or card.get("card") or "").strip()
            if not name:
                continue
            name = name.rstrip("+")
            count = int(card.get("count", 1))
            upgraded = bool(card.get("upgraded", card.get("upgrade", False)))
            compact.append({"name": name, "upgraded": upgraded, "count": count})
            flat_names.extend([name.lower()] * count)
        else:
            name = str(card).strip().rstrip("+")
            compact.append({"name": name, "upgraded": False, "count": 1})
            flat_names.append(name.lower())

    return compact, flat_names


def _normalize_path(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize path data from various formats into a standard list of steps."""
    path = run.get("path") or []
    if not isinstance(path, list):
        return []

    normalized: list[dict[str, Any]] = []
    for i, step in enumerate(path):
        if isinstance(step, dict):
            ns = dict(step)
        else:
            ns = {"result": str(step)}
        ns.setdefault("floor", i + 1)
        ns.setdefault("type", "combat")
        if "hp_after" not in ns and "hp" in ns:
            ns["hp_after"] = ns["hp"]
        normalized.append(ns)
    return normalized


def _card_count(deck: list[dict[str, Any]]) -> int:
    return sum(c.get("count", 1) for c in deck)


def _basic_card_names() -> set[str]:
    return {"strike", "defend", "survivor", "neutralize", "bash",
            "zap", "dualcast", "eruption", "vigilance", "ascender's bane"}


def _get_act(floor: int) -> int:
    if floor <= ACT_1_MAX_FLOOR:
        return 1
    if floor <= ACT_2_MAX_FLOOR:
        return 2
    return 3


# =============================================================================
# Rule analysis functions — each returns (problems, strengths, warnings, suggestions)
# =============================================================================


def _rule_low_defense_scaling(
    character: str,
    deck: list[dict[str, Any]],
    flat_names: list[str],
    floor: int,
    relics: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: does the deck have enough block, and can that block scale?"""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    char_key = character.lower()
    total = _card_count(deck)
    block_set = _BLOCK_CARDS.get(char_key, set())
    block_count = sum(1 for n in flat_names if n in block_set or n == "defend")
    block_ratio = block_count / max(total, 1)

    if block_ratio < MIN_BLOCK_RATIO:
        problems.append(
            f"Low defense: only {block_count}/{total} cards provide block "
            f"({block_ratio:.0%}) — under the {MIN_BLOCK_RATIO:.0%} minimum"
        )
        if block_set:
            suggestions.append(
                f"Add 2-3 more block cards ({char_key.title()}-specific: "
                f"{', '.join(sorted(list(block_set)[:4]))})"
            )
        else:
            suggestions.append(
                "Add 2-3 more block cards (e.g., Shrug It Off, Backflip, Glacier, Protect)"
            )
    elif block_ratio >= 0.35:
        strengths.append(
            f"Strong defense: {block_count}/{total} block cards ({block_ratio:.0%})"
        )

    # Check block upgrade coverage
    block_card_entries = [c for c in deck if c["name"].lower() in block_set or c["name"].lower() == "defend"]
    block_upgraded = sum(c.get("count", 1) for c in block_card_entries if c.get("upgraded"))
    block_total = sum(c.get("count", 1) for c in block_card_entries)
    if block_total >= 3 and block_upgraded < block_total * 0.3:
        warnings.append(
            f"Only {block_upgraded}/{block_total} block cards are upgraded — "
            f"upgraded block is significantly more efficient"
        )
        suggestions.append("Prioritize upgrading key block cards at campfires")

    # Check if defense relics are present
    relics_lower = [r.lower() for r in relics]
    has_def_relic = any(r in _DEFENSIVE_RELICS for r in relics_lower)
    if block_ratio < MIN_BLOCK_RATIO and not has_def_relic:
        warnings.append("No defensive relics to compensate for light block")
    elif has_def_relic:
        strengths.append("Defensive relics help mitigate damage")

    return problems, strengths, warnings, suggestions


def _rule_expensive_cards(
    deck: list[dict[str, Any]],
    flat_names: list[str],
    floor: int,
    relics: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: too many 2+ cost cards without energy support?"""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    total = _card_count(deck)
    expensive_count = sum(
        c.get("count", 1) for c in deck
        if c["name"].lower() in _EXPENSIVE_CARDS
    )
    expensive_ratio = expensive_count / max(total, 1)

    relics_lower = [r.lower() for r in relics]
    has_energy_relic = any(r in _ENERGY_RELICS for r in relics_lower)
    has_energy_util = any(r in _ENERGY_UTILITY_RELICS for r in relics_lower)

    if expensive_ratio > HIGH_COST_MAX_RATIO and not (has_energy_relic or has_energy_util):
        problems.append(
            f"Energy hungry: {expensive_count}/{total} cards cost 2+ energy "
            f"({expensive_ratio:.0%}) with no energy relic to support them"
        )
        suggestions.append(
            "Pick an energy relic at the next boss, or remove some 2-cost cards"
        )
    elif expensive_ratio > HIGH_COST_MAX_RATIO and has_energy_relic:
        warnings.append(
            f"{expensive_count}/{total} expensive cards ({expensive_ratio:.0%}) — "
            f"manageable with energy relic but be careful on draw order"
        )
    elif expensive_ratio <= 0.15 and total >= 10:
        strengths.append("Energy-efficient deck with mostly 0-1 cost cards")

    # Check for too many 3-cost cards
    very_expensive = sum(
        c.get("count", 1) for c in deck
        if c["name"].lower() in {
            "demon form", "echo form", "wraith form", "bludgeon",
            "wish", "meteor strike", "omega",
        }
    )
    if very_expensive >= 2 and not has_energy_relic:
        warnings.append(
            f"{very_expensive} very expensive cards (3+ cost) without energy relic"
        )
        suggestions.append("Without extra energy, limit 3-cost cards to at most 1")

    return problems, strengths, warnings, suggestions


def _rule_insufficient_draw(
    character: str,
    deck: list[dict[str, Any]],
    flat_names: list[str],
    floor: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: does the deck have enough card draw to be consistent?"""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    char_key = character.lower()
    draw_set = _DRAW_CARDS.get(char_key, set())
    draw_found = [n for n in flat_names if n in draw_set]
    unique_draw = len(set(draw_found))
    total_draw = len(draw_found)
    total = _card_count(deck)
    act = _get_act(floor)

    if act >= 2 and unique_draw < MIN_DRAW_CARDS:
        problems.append(
            f"Insufficient card draw: only {unique_draw} unique draw card(s) "
            f"in Act {act} — deck will be inconsistent"
        )
        suggestions.append(
            f"Add card draw: {', '.join(sorted(list(draw_set)[:4]))} "
            f"or similar for {char_key.title()}"
        )
    elif unique_draw >= 3:
        strengths.append(
            f"Good card draw: {unique_draw} unique draw cards, {total_draw} total copies"
        )
    elif unique_draw == 1 and total_draw == 1 and act >= 2:
        warnings.append(
            f"Only 1 copy of a single draw card — draw may be unreliable"
        )
        suggestions.append("Add at least one more draw card for consistency")

    # Very large deck without draw
    if total > MAX_DECK_BLOAT and total_draw < 3:
        warnings.append(
            f"Deck of {total} cards with only {total_draw} draw sources — "
            f"key cards will be hard to find"
        )
        suggestions.append("Either trim deck below 30 cards or add more draw")

    return problems, strengths, warnings, suggestions


def _rule_weak_boss_preparation(
    character: str,
    deck: list[dict[str, Any]],
    flat_names: list[str],
    floor: int,
    boss: str,
    path: list[dict[str, Any]],
    max_hp: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: is the deck prepared for the boss encounter?"""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    char_key = character.lower()
    act = _get_act(floor)
    scaling_set = _SCALING_CARDS.get(char_key, set())
    scaling_found = list(set(n for n in flat_names if n in scaling_set))

    # Boss scaling check
    if act >= 2 and len(scaling_found) < MIN_SCALING_ACT2:
        problems.append(
            f"Weak boss preparation: only {len(scaling_found)} scaling card(s) "
            f"for Act {act} boss — need {MIN_SCALING_ACT2 if act==2 else MIN_SCALING_ACT3}+"
        )
        suggestions.append(
            f"Prioritize scaling cards before the boss: "
            f"{', '.join(sorted(list(scaling_set)[:4]))}"
        )
    elif len(scaling_found) >= MIN_SCALING_ACT3:
        strengths.append(
            f"Strong boss scaling suite: {len(scaling_found)} unique scaling cards"
        )

    # HP before boss check
    boss_steps = [s for s in path if s.get("type") == "boss"]
    if boss_steps:
        last_boss = boss_steps[-1]
        boss_idx = path.index(last_boss)
        hp_before = path[boss_idx - 1].get("hp_after", max_hp) if boss_idx > 0 else max_hp
        if hp_before < max_hp * MIN_HP_RATIO_BOSS:
            problems.append(
                f"Entered {boss} at {hp_before}/{max_hp} HP "
                f"({hp_before/max(max_hp,1):.0%}) — wanted ≥ {MIN_HP_RATIO_BOSS:.0%}"
            )
            suggestions.append("Plan pathing to reach the boss with higher HP")
        elif hp_before >= max_hp * 0.85:
            strengths.append(f"Entered boss fight at near-full HP ({hp_before}/{max_hp})")

    # Specific boss tips
    boss_lower = boss.lower()
    _BOSS_TIPS: dict[str, str] = {
        "slime boss": "Front-load damage during the split; AoE helps clean up slimes",
        "the guardian": "Scale during defensive phases; don't attack into thorns",
        "hexaghost": "Lower HP reduces Inferno burn — don't overheal before this fight",
        "bronze automaton": "Draft extra cards — it steals one per turn",
        "the champ": "Scale to burst from 50% HP to 0 before Execute triggers",
        "the collector": "Kill torch-head minions fast — their Mega Debuff stacks",
        "time eater": "Avoid 12-card turns; favor high-impact over spam cards",
        "donu and deca": "Kill Donu first; scaling AoE is very strong here",
        "awakened one": "Hold powers for phase 2 or outscale the strength gain",
    }
    if boss_lower in _BOSS_TIPS:
        suggestions.append(f"Boss tip for {boss}: {_BOSS_TIPS[boss_lower]}")

    return problems, strengths, warnings, suggestions


def _rule_low_relic_synergy(
    character: str,
    deck: list[dict[str, Any]],
    flat_names: list[str],
    floor: int,
    relics: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: relics supporting the deck's game plan?"""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    char_key = character.lower()
    relics_lower = [r.lower() for r in relics]
    relic_count = len(relics)
    act = _get_act(floor)

    # Relic count benchmark
    expected = max(1, floor // 2)
    if relic_count < expected * 0.5:
        warnings.append(
            f"Low relic count: {relic_count} by floor {floor} "
            f"(expect ~{expected}) — take more elites or visit shops"
        )
        suggestions.append("Consider taking an extra elite path for relic rewards")
    elif relic_count >= expected * 1.2:
        strengths.append(f"Good relic collection: {relic_count} relics")

    # Energy economy
    has_energy = any(r in _ENERGY_RELICS for r in relics_lower)
    has_util = any(r in _ENERGY_UTILITY_RELICS for r in relics_lower)
    if act >= 2 and not has_energy and not has_util:
        problems.append("No energy relic by Act 2+ — 3 energy/turn may be insufficient")
        suggestions.append("Prioritize an energy boss relic if offered")
    elif has_energy:
        strengths.append("Energy relic present — energy economy is solid")

    # Scaling synergy
    scaling_set = _SCALING_CARDS.get(char_key, set())
    has_scaling_cards = any(n in scaling_set for n in flat_names)
    has_scaling_relic = any(r in _SCALING_RELICS for r in relics_lower)
    if has_scaling_cards and not has_scaling_relic:
        warnings.append("Deck has scaling cards but no scaling-support relics")
    elif has_scaling_cards and has_scaling_relic:
        strengths.append("Scaling cards are backed by scaling relics — good synergy")

    return problems, strengths, warnings, suggestions


def _rule_poor_hp_management(
    path: list[dict[str, Any]],
    max_hp: int,
    floor: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: HP management through the run — rests, elite HP drops, trends."""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    if not path:
        return problems, strengths, warnings, suggestions

    # Check for sharp HP drops at elite fights
    sharp_drops: list[int] = []
    for i, step in enumerate(path):
        if step.get("type") != "elite":
            continue
        prev_hp = path[i - 1].get("hp_after", max_hp) if i > 0 else max_hp
        hp_after = step.get("hp_after", max_hp)
        if prev_hp > 0 and (prev_hp - hp_after) / prev_hp > 0.40:
            sharp_drops.append(step.get("floor", i + 1))

    if len(sharp_drops) >= 2:
        problems.append(
            f"Sharp HP losses after elites on floors {sharp_drops} — "
            f"pathing too aggressive for deck's current strength"
        )
        suggestions.append("Take fewer elites or rest more between elite fights")
    elif sharp_drops:
        warnings.append(f"Sharp HP loss after elite on floor {sharp_drops[0]}")

    # Check rest site usage
    rests = [s for s in path if s.get("type") == "rest"]
    heal_rests = sum(
        1 for r in rests
        if r.get("hp_after", 0) > r.get("hp_before", 0) + 5
    )
    if len(rests) >= 3 and heal_rests > len(rests) / 2:
        warnings.append(
            f"{heal_rests}/{len(rests)} campfires spent resting instead of upgrading"
        )
        suggestions.append("Upgrade key cards at campfires; heal only when necessary")
    elif len(rests) >= 2 and heal_rests <= len(rests) / 2:
        strengths.append("Campfires were used efficiently — prioritizing upgrades")

    # Check HP trend in last 5 combats
    combats = [s for s in path if s.get("type") in ("combat", "elite")]
    if len(combats) >= 5:
        last5 = combats[-5:]
        hp_values = [s.get("hp_after", max_hp) for s in last5]
        if hp_values and max(hp_values) - min(hp_values) > max_hp * 0.4:
            warnings.append("HP swung dramatically in late-game — inconsistent defense")

    return problems, strengths, warnings, suggestions


def _rule_risky_pathing(
    path: list[dict[str, Any]],
    floor: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: path choices — elite density, rest spacing, greedy patterns."""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    if not path:
        return problems, strengths, warnings, suggestions

    # Count elites per act
    act1_elites = sum(1 for s in path if s.get("type") == "elite" and s.get("floor", 0) <= ACT_1_MAX_FLOOR)
    act2_elites = sum(1 for s in path if s.get("type") == "elite" and ACT_1_MAX_FLOOR < s.get("floor", 0) <= ACT_2_MAX_FLOOR)
    act1_rests = sum(1 for s in path if s.get("type") == "rest" and s.get("floor", 0) <= ACT_1_MAX_FLOOR)

    if act1_elites > MAX_ELITES_PER_ACT:
        problems.append(
            f"Risky pathing: {act1_elites} elites in Act 1 "
            f"(recommend ≤ {MAX_ELITES_PER_ACT})"
        )
        suggestions.append("Take 1-2 elites max in Act 1 unless deck is very strong")

    if act2_elites > MAX_ELITES_PER_ACT:
        problems.append(
            f"Risky pathing: {act2_elites} elites in Act 2 — "
            f"Act 2 elites are especially dangerous"
        )
        suggestions.append("Avoid Act 2 elites unless you have strong AoE and block")

    # Consecutive elites without rest
    consecutive = 0
    for s in path:
        if s.get("type") == "elite":
            consecutive += 1
            if consecutive >= 2:
                warnings.append("Fought consecutive elites without resting between")
                break
        elif s.get("type") == "rest":
            consecutive = 0

    # Balanced pathing
    if act1_elites <= 2 and act2_elites <= 2 and act1_rests >= 1:
        strengths.append("Sensible elite/rest balance across acts")

    return problems, strengths, warnings, suggestions


def _rule_low_deck_consistency(
    deck: list[dict[str, Any]],
    flat_names: list[str],
    floor: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Check: deck consistency — size, basic ratio, upgrade coverage, bloat."""
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    total = _card_count(deck)
    act = _get_act(floor)
    basic_names = _basic_card_names()

    # Basic card ratio
    basic_count = sum(1 for n in flat_names if n in basic_names)
    basic_ratio = basic_count / max(total, 1)
    if basic_ratio > MAX_BASIC_RATIO:
        problems.append(
            f"Low consistency: {basic_count}/{total} cards are basic starters "
            f"({basic_ratio:.0%}) — they dilute every draw"
        )
        suggestions.append("Remove basic Strikes/Defends at shops to improve consistency")
    elif basic_ratio <= 0.15 and total >= 12:
        strengths.append(f"Deck is lean: only {basic_count} basic cards ({basic_ratio:.0%})")

    # Deck size — too small for act
    if act >= 2 and total < DECK_CONSISTENCY_MIN:
        warnings.append(
            f"Deck has only {total} cards in Act {act} — "
            f"may lack options against varied threats"
        )
    elif total > MAX_DECK_BLOAT:
        warnings.append(
            f"Deck is bloated at {total} cards — key cards appear less often"
        )
        suggestions.append("Skip card rewards more often; aim for 20-30 cards")
    elif DECK_CONSISTENCY_MIN <= total <= 30:
        strengths.append(f"Deck size ({total} cards) is in a healthy range")

    # Upgrade coverage
    upgraded = sum(c.get("count", 1) for c in deck if c.get("upgraded"))
    upgrade_ratio = upgraded / max(total, 1)
    if act >= 2 and upgrade_ratio < 0.35:
        warnings.append(
            f"Only {upgraded}/{total} cards upgraded ({upgrade_ratio:.0%}) — "
            f"missed upgrade opportunities"
        )
        suggestions.append("Prioritize campfire upgrades over healing")
    elif upgrade_ratio >= 0.50:
        strengths.append(f"Good upgrade coverage: {upgraded}/{total} upgraded ({upgrade_ratio:.0%})")

    return problems, strengths, warnings, suggestions


# =============================================================================
# Knowledge-enhanced analysis
# =============================================================================


def _analyze_knowledge_insights(
    character: str,
    flat_names: list[str],
    relics: list[str],
    boss: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Cross-reference the deck/relics/boss against the knowledge base.

    Returns insights beyond what the pure rule-based checks detect:
    - Card-specific risk notes from the knowledge base
    - Relic synergy insights
    - Boss-specific counter-strategies
    - Archetype matching and missing core card suggestions
    """
    problems: list[str] = []
    strengths: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    if not is_knowledge_available():
        return problems, strengths, warnings, suggestions

    # ── 1. Card risk notes ───────────────────────────────────────────
    seen_cards: set[str] = set()
    for name in flat_names:
        if name in seen_cards:
            continue
        seen_cards.add(name)
        card = get_card(name)
        if card:
            risk = card.get("risk_notes")
            if risk:
                warnings.append(f"[{name}]: {risk}")

    # ── 2. Relic synergy insights ────────────────────────────────────
    relic_names_lower = [r.lower() for r in relics]
    for relic_name in relics:
        relic = get_relic(relic_name)
        if relic:
            syn_tags = relic.get("synergy_tags", [])
            # Check if deck has matching synergy cards
            matched: list[str] = []
            for tag in syn_tags:
                for card_name in flat_names:
                    card = get_card(card_name)
                    if card and tag in card.get("synergy_tags", []):
                        if card_name not in matched:
                            matched.append(card_name)
            if matched:
                strengths.append(
                    f"Synergy: {relic_name} works with {', '.join(matched[:3])}"
                )
            # Check relic weaknesses
            weakness = relic.get("weaknesses", [])
            if weakness:
                for w in weakness:
                    if any(kw in w.lower() for kw in ["punishes", "risky", "dangerous"]):
                        warnings.append(f"[{relic_name}]: {w}")

    # ── 3. Boss-specific threats ─────────────────────────────────────
    boss_knowledge = get_boss(boss)
    if boss_knowledge:
        risk = boss_knowledge.get("risk_notes")
        if risk:
            suggestions.append(f"Boss strategy for {boss}: {risk}")
        weaknesses = boss_knowledge.get("weaknesses", [])
        if weaknesses:
            suggestions.append(
                f"Counter {boss} with: {'; '.join(weaknesses[:2])}"
            )

    # ── 4. Archetype matching ────────────────────────────────────────
    archetypes = get_archetypes_for_character(character)
    if archetypes:
        best_match: dict[str, Any] | None = None
        best_score = 0
        for arch in archetypes:
            core = arch.get("core_cards", [])
            matched_core = sum(
                1 for c in core
                if c.lower().replace(" ", "_") in [n.lower() for n in flat_names]
                or c.lower() in [n.lower() for n in flat_names]
            )
            score = matched_core / max(len(core), 1)
            if score > best_score:
                best_score = score
                best_match = arch

        if best_match and best_score >= 0.3:
            arch_name = best_match["name"]
            if best_score >= 0.6:
                strengths.append(
                    f"Deck aligns with '{arch_name}' archetype — {best_match.get('strengths', ['Strong build'])[0]}"
                )
            else:
                missing = [
                    c for c in best_match.get("core_cards", [])
                    if c.lower() not in [n.lower() for n in flat_names]
                ]
                if missing:
                    suggestions.append(
                        f"Deck is close to '{arch_name}' archetype — "
                        f"consider adding: {', '.join(missing[:3])}"
                    )

            risk = best_match.get("risk_notes")
            if risk:
                warnings.append(f"Archetype note ({arch_name}): {risk}")

    return problems, strengths, warnings, suggestions


# =============================================================================
# Data extraction from parsed run
# =============================================================================


def _extract_run_context(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """Extract and normalize all fields needed for rule analysis."""
    # Character
    character = str(
        parsed_data.get("character")
        or parsed_data.get("player_class")
        or parsed_data.get("class")
        or "Unknown"
    )

    # Floor
    floor = parsed_data.get("floor_reached") or parsed_data.get("floor") or 0
    try:
        floor = int(floor)
    except (TypeError, ValueError):
        floor = 0

    # Boss
    bosses = parsed_data.get("bosses") or []
    if not isinstance(bosses, list):
        bosses = []
    boss = (
        parsed_data.get("boss")
        or parsed_data.get("killed_by")
        or parsed_data.get("final_boss")
        or (bosses[-1] if bosses else None)
        or "Unknown"
    )
    if isinstance(boss, list):
        boss = boss[-1] if boss else "Unknown"
    boss = str(boss)

    # Cards
    cards = parsed_data.get("cards") or parsed_data.get("deck") or parsed_data.get("master_deck") or []
    if not isinstance(cards, list):
        cards = []

    # Relics
    relics = parsed_data.get("relics") or parsed_data.get("relic_names") or []
    if not isinstance(relics, list):
        relics = []
    # Relics can be strings or dicts — normalize to strings
    relics_str: list[str] = []
    for r in relics:
        if isinstance(r, str):
            relics_str.append(r)
        elif isinstance(r, dict):
            relics_str.append(str(r.get("name") or r.get("relic") or ""))
    relics_str = [r for r in relics_str if r]

    # HP
    max_hp = parsed_data.get("max_hp") or parsed_data.get("maximum_hp") or 80
    try:
        max_hp = int(max_hp)
    except (TypeError, ValueError):
        max_hp = 80

    current_hp = parsed_data.get("hp") or parsed_data.get("current_hp") or parsed_data.get("final_hp")
    try:
        current_hp = int(current_hp) if current_hp is not None else 0
    except (TypeError, ValueError):
        current_hp = 0

    # Path
    path = _normalize_path(parsed_data)

    # Victory
    victory = parsed_data.get("victory") or parsed_data.get("won") or parsed_data.get("is_victory")
    if victory is not None:
        victory = bool(victory)
    else:
        victory = current_hp > 0 if current_hp else None

    return {
        "character": character,
        "floor": floor,
        "boss": boss,
        "cards_raw": cards,
        "relics": relics_str,
        "max_hp": max_hp,
        "current_hp": current_hp,
        "path": path,
        "victory": victory,
    }


# =============================================================================
# Public entry point
# =============================================================================


def analyze_run_rules(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """Run all rule-based checks on a parsed run and return structured findings.

    Parameters
    ----------
    parsed_data : dict
        Output of :func:`run_parser.parse_run_data` (the API endpoint path).

    Returns
    -------
    dict
        Structured findings::

            {
                "problems": [...],
                "strengths": [...],
                "warnings": [...],
                "suggestions": [...],
                "run_context": {character, floor, boss, ...},
                "analysis_quality": "rule_based",
            }
    """
    ctx = _extract_run_context(parsed_data)
    deck, flat_names = _normalize_card_list(ctx["cards_raw"])

    all_problems: list[str] = []
    all_strengths: list[str] = []
    all_warnings: list[str] = []
    all_suggestions: list[str] = []

    # Run every rule
    rules = [
        _rule_low_defense_scaling(ctx["character"], deck, flat_names, ctx["floor"], ctx["relics"]),
        _rule_expensive_cards(deck, flat_names, ctx["floor"], ctx["relics"]),
        _rule_insufficient_draw(ctx["character"], deck, flat_names, ctx["floor"]),
        _rule_weak_boss_preparation(ctx["character"], deck, flat_names, ctx["floor"],
                                    ctx["boss"], ctx["path"], ctx["max_hp"]),
        _rule_low_relic_synergy(ctx["character"], deck, flat_names, ctx["floor"], ctx["relics"]),
        _rule_poor_hp_management(ctx["path"], ctx["max_hp"], ctx["floor"]),
        _rule_risky_pathing(ctx["path"], ctx["floor"]),
        _rule_low_deck_consistency(deck, flat_names, ctx["floor"]),
        # Knowledge-base enhanced analysis
        _analyze_knowledge_insights(ctx["character"], flat_names, ctx["relics"], ctx["boss"]),
    ]

    for problems, strengths, warnings, suggestions in rules:
        all_problems.extend(problems)
        all_strengths.extend(strengths)
        all_warnings.extend(warnings)
        all_suggestions.extend(suggestions)

    # Deduplicate suggestions (keep order)
    seen_suggestions: set[str] = set()
    unique_suggestions: list[str] = []
    for s in all_suggestions:
        if s not in seen_suggestions:
            seen_suggestions.add(s)
            unique_suggestions.append(s)

    # Build run context summary
    run_context = {
        "character": ctx["character"],
        "floor": ctx["floor"],
        "boss": ctx["boss"],
        "deck_size": _card_count(deck),
        "relic_count": len(ctx["relics"]),
        "victory": ctx["victory"],
    }

    logger.info(
        "Rule analysis complete: %d problems, %d strengths, %d warnings, %d suggestions",
        len(all_problems), len(all_strengths), len(all_warnings), len(unique_suggestions),
    )

    return {
        "problems": all_problems,
        "strengths": all_strengths,
        "warnings": all_warnings,
        "suggestions": unique_suggestions,
        "run_context": run_context,
        "analysis_quality": "rule_based",
    }
