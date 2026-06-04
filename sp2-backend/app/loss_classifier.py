from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

try:
    from app.pipeline_config import (
        LOSS_CLASSIFICATION_PATH,
        NORMALIZED_RUN_PATH,
        PIPELINE_LOG_PATH,
    )
    from app.utils import save_json, setup_logger
except ImportError:
    from app.pipeline_config import LOSS_CLASSIFICATION_PATH, NORMALIZED_RUN_PATH, PIPELINE_LOG_PATH
    from app.utils import save_json, setup_logger


# ---------------------------------------------------------------------------
# Logger — same pipeline log as the rest of the project
# ---------------------------------------------------------------------------
LOGGER: logging.Logger = setup_logger(str(PIPELINE_LOG_PATH))

# ---------------------------------------------------------------------------
# Loss categories this classifier can detect
# ---------------------------------------------------------------------------
CATEGORIES: tuple[str, ...] = (
    "deck_problem",
    "pathing_problem",
    "boss_preparation_problem",
    "scaling_problem",
    "defense_problem",
    "energy_problem",
    "card_pick_problem",
    "relic_synergy_problem",
)

# --- Card knowledge: scaling cards per character -----------------------
# These are cards that make you stronger as the fight goes on — poison
# stacking, strength gain, focus gain, mantra, etc.  Without at least
# a couple of these by late Act 2 / early Act 3, long fights (especially
# bosses) will out-scale you.
_SCALING_CARDS: dict[str, set[str]] = {
    "the silent": {
        "noxious fumes", "catalyst", "footwork", "after image",
        "thousand cuts", "envenom", "wraith form", "phantasmal killer",
        "blade dance", "accuracy", "terror", "well-laid plans",
        "corpse explosion",
    },
    "ironclad": {
        "demon form", "barricade", "juggernaut", "feel no pain",
        "dark embrace", "corruption", "inflame", "spot weakness",
        "rupture", "evolve", "fire breathing",
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

# Block cards (excluding the basic Defend) for each character.
_EXTRA_BLOCK_CARDS: dict[str, set[str]] = {
    "the silent": {
        "survivor", "dodge and roll", "backflip", "leg sweep",
        "blur", "piercing wail", "escape plan", "deflect",
    },
    "ironclad": {
        "shrug it off", "flame barrier", "ghostly armor",
        "power through", "impervious", "second wind", "rage",
    },
    "defect": {
        "charge battery", "glacier", "reinforced body",
        "leap", "force field", "cold snap", "coolheaded",
    },
    "watcher": {
        "protect", "deceive reality", "sanctity", "perseverance",
        "halt", "wave of the hand",
    },
}

# Scaling-adjacent relics that help long fights.
_SCALING_RELICS: set[str] = {
    "snecko skull", "specimen", "twisted funnel",
    "brimstone", "champions belt",
    "data disk", "gold plated cables", "inserter",
    "damaru", "violet lotus",
    "kunai", "shuriken", "ornamental fan", "girya", "vajra",
}

# Energy relics / energy-generating relics.
_ENERGY_RELICS: set[str] = {
    "coffee dripper", "cursed key", "fusion hammer", "philosopher's stone",
    "runic dome", "sozu", "busted crown", "velvet choker",
    "happy flower", "sundial", "lantern", "nunchaku",
    "ancient tea set", "art of war",
}

# Energy-generating or cost-reducing cards.
_ENERGY_CARDS: set[str] = {
    "adrenaline", "tactician", "concentrate", "prepared",
    "offering", "bloodletting", "seeing red",
    "turbo", "double energy", "aggregate", "recycle",
    "miracle", "deceive reality", "sash whip",
}

# --- Constants for scoring thresholds ----------------------------------
ELITE_HP_DROP_RATIO = 0.40         # hp_after < 40% of previous means *big* drop
HIGH_FLOOR_THRESHOLD = 17          # floors >= 17 considered Act 2+
BASIC_CARD_LIMIT = 5               # more than 5 Strike/Defend is a red flag
SMALL_DECK_THRESHOLD = 15          # decks smaller than this by Act 2 are suspect
MIN_SCALING_CARDS = 2              # want at least this many scaling cards by Act 2+
BLOCK_RATIO_THRESHOLD = 0.25       # fewer than 25% block cards is light
HIGH_COST_RATIO = 0.30             # >30% of cards costing 2+ is heavy
MIN_RELICS_PER_ACT = 4             # relics per act benchmark
MANY_ELITES_THRESHOLD = 3          # more than this many elites in one act

# Score thresholds when choosing main vs secondary reasons.
MAIN_REASON_MIN_SCORE = 0.20
SECONDARY_REASON_MIN_SCORE = 0.10
CONFIDENCE_BASE = 0.50
CONFIDENCE_DELTA_PER_EXTRA = 0.08


# ===================================================================
# Internal analysis helpers — each returns (score: float, evidence: list[str])
# ===================================================================


def _card_names(deck: list[dict[str, Any]]) -> list[str]:
    """Expand the compact deck list into a flat list of card *names*.

    Example: [{"name":"Strike","count":4}] → ["Strike","Strike","Strike","Strike"]
    """
    flat: list[str] = []
    for card in deck:
        flat.extend([card["name"]] * card.get("count", 1))
    return flat


def _basic_card_count(deck: list[dict[str, Any]]) -> int:
    """Return the total number of Strike + Defend cards in the deck."""
    total = 0
    for card in deck:
        if card["name"].lower() in ("strike", "defend"):
            total += card.get("count", 1)
    return total


def _check_deck_problem(
    run: dict[str, Any],
    deck: list[dict[str, Any]],
    flat_names: list[str],
) -> tuple[float, list[str]]:
    """Too many basic cards or a suspiciously small deck for the floor."""
    score = 0.0
    evidence: list[str] = []

    basic_count = _basic_card_count(deck)
    floor = run["floor"]

    # Still carrying many basic Strike/Defend cards deep into a run.
    if basic_count > BASIC_CARD_LIMIT:
        score += 0.30
        evidence.append(
            f"Deck still contains {basic_count} basic Strike/Defend cards "
            f"by floor {floor} — these dilute draws"
        )

    # Deck is very small for late-game fights.
    total_cards = sum(c.get("count", 1) for c in deck)
    if floor >= HIGH_FLOOR_THRESHOLD and total_cards < SMALL_DECK_THRESHOLD:
        score += 0.25
        evidence.append(
            f"Deck has only {total_cards} cards by floor {floor} "
            f"(minimum ~{SMALL_DECK_THRESHOLD} expected for Act 2+)"
        )

    return score, evidence


def _check_pathing_problem(run: dict[str, Any]) -> tuple[float, list[str]]:
    """Sharp HP drops after elites, or entering the boss on low HP."""
    score = 0.0
    evidence: list[str] = []
    path: list[dict[str, Any]] = run["path"]

    elite_hp_drops: list[dict[str, Any]] = []

    # Walk the path looking for elite floors with big HP losses.
    for i, step in enumerate(path):
        if step["type"] != "elite":
            continue
        prev_hp = path[i - 1]["hp_after"] if i > 0 else run["max_hp"]
        hp_after = step["hp_after"]
        drop_ratio = (prev_hp - hp_after) / max(prev_hp, 1)
        if drop_ratio > ELITE_HP_DROP_RATIO:
            elite_hp_drops.append(
                {"floor": step["floor"], "prev_hp": prev_hp, "hp_after": hp_after}
            )

    if len(elite_hp_drops) >= 2:
        score += 0.30
        floors_str = ", ".join(str(d["floor"]) for d in elite_hp_drops)
        evidence.append(
            f"Sharp HP losses after elites on floors {floors_str} "
            f"— pathing may be too aggressive"
        )
    elif len(elite_hp_drops) == 1:
        score += 0.15
        d = elite_hp_drops[0]
        evidence.append(
            f"Sharp HP loss after elite on floor {d['floor']} "
            f"({d['prev_hp']} → {d['hp_after']})"
        )

    # Entering the final boss with dangerously low HP.
    # Find the last boss-floor step (the one where the player died).
    boss_steps = [s for s in path if s["type"] == "boss"]
    if boss_steps:
        # Check HP before the last boss fight.
        last_boss = boss_steps[-1]
        boss_idx = path.index(last_boss)
        hp_before_boss = path[boss_idx - 1]["hp_after"] if boss_idx > 0 else run["max_hp"]
        if hp_before_boss < run["max_hp"] * 0.50:
            score += 0.20
            evidence.append(
                f"Entered boss fight on floor {last_boss['floor']} "
                f"with only {hp_before_boss}/{run['max_hp']} HP"
            )

    return score, evidence


def _check_boss_preparation_problem(
    run: dict[str, Any],
    flat_names: list[str],
) -> tuple[float, list[str]]:
    """Deck lacks scaling or a block plan for the boss fight."""
    score = 0.0
    evidence: list[str] = []
    character = run["character"].lower()
    boss = run["boss"].lower()

    scaling_set = _SCALING_CARDS.get(character, set())
    flat_lower = [n.lower() for n in flat_names]

    scaling_found = [n for n in flat_lower if n in scaling_set]
    if len(set(scaling_found)) < MIN_SCALING_CARDS:
        score += 0.30
        evidence.append(
            f"Only {len(set(scaling_found))} scaling card(s) found "
            f"({', '.join(scaling_found) if scaling_found else 'none'}) — "
            f"boss fights demand scaling"
        )

    # Check block plan — does the deck have extra block cards?
    block_set = _EXTRA_BLOCK_CARDS.get(character, set())
    block_found = [n for n in flat_lower if n in block_set]
    if len(set(block_found)) < 2:
        score += 0.20
        evidence.append(
            f"Only {len(set(block_found))} non-basic block card(s) in deck "
            f"— insufficient block plan for {boss}"
        )

    return score, evidence


def _check_scaling_problem(
    run: dict[str, Any],
    deck: list[dict[str, Any]],
    flat_names: list[str],
) -> tuple[float, list[str]]:
    """High floor but small deck and/or no scaling cards at all."""
    score = 0.0
    evidence: list[str] = []
    floor = run["floor"]
    character = run["character"].lower()

    total_cards = sum(c.get("count", 1) for c in deck)
    scaling_set = _SCALING_CARDS.get(character, set())
    flat_lower = [n.lower() for n in flat_names]
    scaling_found = set(n for n in flat_lower if n in scaling_set)

    # Reaching Act 2+ with a very small deck means you can't keep up
    # with enemy HP scaling.
    if floor >= HIGH_FLOOR_THRESHOLD and total_cards < SMALL_DECK_THRESHOLD:
        score += 0.35
        evidence.append(
            f"Reached floor {floor} with only {total_cards} cards — "
            f"enemy HP scaling outpaces a small deck"
        )

    if not scaling_found:
        score += 0.35
        evidence.append(
            f"No scaling cards detected for {character.title()} "
            f"by floor {floor}"
        )
    elif len(scaling_found) == 1:
        score += 0.15
        evidence.append(
            f"Only one scaling card ({next(iter(scaling_found))}) "
            f"— unreliable draw when it matters most"
        )

    return score, evidence


def _check_defense_problem(
    deck: list[dict[str, Any]],
    flat_names: list[str],
) -> tuple[float, list[str]]:
    """Too few block cards for the deck size."""
    score = 0.0
    evidence: list[str] = []
    total_cards = sum(c.get("count", 1) for c in deck)
    flat_lower = [n.lower() for n in flat_names]

    # Count anything that looks like a block card.
    all_block_keywords: set[str] = {"defend"}
    for block_set in _EXTRA_BLOCK_CARDS.values():
        all_block_keywords.update(block_set)

    block_count = sum(1 for n in flat_lower if n in all_block_keywords)
    block_ratio = block_count / max(total_cards, 1)

    if block_ratio < BLOCK_RATIO_THRESHOLD:
        score += 0.25
        evidence.append(
            f"Only {block_count}/{total_cards} cards provide block "
            f"({block_ratio:.0%}) — below {BLOCK_RATIO_THRESHOLD:.0%} minimum"
        )

    return score, evidence


def _check_energy_problem(
    run: dict[str, Any],
    flat_names: list[str],
) -> tuple[float, list[str]]:
    """Too many high-cost cards without energy relics or generators."""
    score = 0.0
    evidence: list[str] = []
    relics = [r.lower() for r in run.get("relics", [])]
    flat_lower = [n.lower() for n in flat_names]

    # Count 2+ cost cards (Slay the Spire convention — "X", "2", "3", …).
    high_cost_count = 0
    for card in run["deck"]:
        name = card["name"].lower()
        if name in ("strike", "defend", "survivor", "neutralize", "zap",
                     "dualcast", "eruption", "vigilance", "ascender's bane"):
            continue  # these are free or 1-cost starter cards
        # Cards known to cost 2+ are checked by name — this is simple
        # heuristic: skip the ambiguous ones and look at energy relics.
        # For now, use a coarse check: many cards in the deck may be 2-cost
        # if relics suggest an energy-hungry build.
    # We approximate: count cards commonly known as 2+ cost.
    _known_high_cost: set[str] = {
        "dash", "leg sweep", "crippling cloud", "predator",
        "flame barrier", "impervious", "shockwave",
        "glacier", "reinforced body", "echo form",
        "wish", "worship", "blasphemy",
    }
    for card in run["deck"]:
        if card["name"].lower() in _known_high_cost:
            high_cost_count += card.get("count", 1)

    total_cards = sum(c.get("count", 1) for c in run["deck"])
    if total_cards > 0 and (high_cost_count / total_cards) > HIGH_COST_RATIO:
        score += 0.20
        evidence.append(
            f"{high_cost_count}/{total_cards} cards are 2+ cost "
            f"— deck may be energy-starved"
        )

    # No energy relics at all.
    has_energy_relic = any(r in _ENERGY_RELICS for r in relics)
    if not has_energy_relic:
        score += 0.15
        evidence.append(
            "No energy relic or energy-generating relic found"
        )

    # No energy-generating cards.
    energy_cards_found = [n for n in flat_lower if n in _ENERGY_CARDS]
    if not energy_cards_found and high_cost_count > 3:
        score += 0.10
        evidence.append(
            "No energy-generating cards to support high-cost picks"
        )

    return score, evidence


def _check_card_pick_problem(
    run: dict[str, Any],
    deck: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    """Too many unupgraded cards or failed card-removal opportunities."""
    score = 0.0
    evidence: list[str] = []
    floor = run["floor"]

    # Count unupgraded non-basic cards.
    unupgraded = 0
    total = 0
    for card in deck:
        count = card.get("count", 1)
        total += count
        if not card.get("upgraded", False):
            # Don't count Ascender's Bane (it cannot be upgraded).
            if card["name"].lower() != "ascender's bane":
                unupgraded += count

    if total > 0 and floor >= HIGH_FLOOR_THRESHOLD:
        unupgraded_ratio = unupgraded / total
        if unupgraded_ratio > 0.60:
            score += 0.25
            evidence.append(
                f"{unupgraded}/{total} cards are unupgraded "
                f"({unupgraded_ratio:.0%}) by floor {floor} — "
                f"missed upgrade opportunities"
            )

    return score, evidence


def _check_relic_synergy_problem(
    run: dict[str, Any],
    flat_names: list[str],
) -> tuple[float, list[str]]:
    """Relics don't support the deck archetype; or too few relics."""
    score = 0.0
    evidence: list[str] = []
    relics = run.get("relics", [])
    floor = run["floor"]
    character = run["character"].lower()
    flat_lower = [n.lower() for n in flat_names]

    # Relic count benchmark: roughly 1 relic per 2 floors is reasonable.
    expected_relics = max(1, floor // 2)
    if len(relics) < expected_relics * 0.5:
        score += 0.20
        evidence.append(
            f"Only {len(relics)} relics by floor {floor} "
            f"(expect ~{expected_relics}) — fewer rewards from elites/events"
        )

    # Does the deck have scaling cards but no scaling relics?
    scaling_set = _SCALING_CARDS.get(character, set())
    has_scaling_cards = any(n in scaling_set for n in flat_lower)
    relics_lower = [r.lower() for r in relics]
    has_scaling_relic = any(r in _SCALING_RELICS for r in relics_lower)

    if has_scaling_cards and not has_scaling_relic:
        score += 0.15
        evidence.append(
            "Deck has scaling cards but no scaling-support relics"
        )

    return score, evidence


# ===================================================================
# Orchestrator — runs every check and picks the best explanation
# ===================================================================


def _classify(run: dict[str, Any]) -> dict[str, Any]:
    """Run all rule-based checks and aggregate the results.

    Returns a dictionary matching the output schema:
    {main_loss_reason, secondary_reasons, confidence, evidence}
    """
    deck: list[dict[str, Any]] = run.get("deck", [])
    flat_names = _card_names(deck)

    # Run every checker — each returns (score, evidence_list).
    results: dict[str, tuple[float, list[str]]] = {
        "deck_problem": _check_deck_problem(run, deck, flat_names),
        "pathing_problem": _check_pathing_problem(run),
        "boss_preparation_problem": _check_boss_preparation_problem(run, flat_names),
        "scaling_problem": _check_scaling_problem(run, deck, flat_names),
        "defense_problem": _check_defense_problem(deck, flat_names),
        "energy_problem": _check_energy_problem(run, flat_names),
        "card_pick_problem": _check_card_pick_problem(run, deck),
        "relic_synergy_problem": _check_relic_synergy_problem(run, flat_names),
    }

    # Sort categories by score (highest first).
    ranked = sorted(results.items(), key=lambda item: item[1][0], reverse=True)

    # The top category becomes the main reason.
    main_category, (main_score, main_evidence) = ranked[0]

    # Secondary reasons: any other category above the secondary threshold.
    secondary: list[str] = []
    all_evidence: list[str] = list(main_evidence)
    for cat, (sc, ev) in ranked[1:]:
        if sc >= SECONDARY_REASON_MIN_SCORE:
            secondary.append(cat)
            all_evidence.extend(ev)

    # Confidence: base value, boosted when the main reason clearly
    # outpaces the second, penalised when everything is ambiguous.
    second_score = ranked[1][1][0] if len(ranked) > 1 else 0.0
    delta = main_score - second_score
    confidence = min(0.95, CONFIDENCE_BASE + delta + len(secondary) * CONFIDENCE_DELTA_PER_EXTRA)
    confidence = max(0.25, confidence)  # don't go below 0.25
    confidence = round(confidence, 2)

    # If no evidence was gathered at all, mark it as uncertain.
    if main_score < MAIN_REASON_MIN_SCORE:
        main_category = "insufficient_data"
        confidence = 0.25
        all_evidence.append(
            "Not enough signals to confidently classify the loss — "
            "consider adding more detailed path or combat data"
        )

    return {
        "main_loss_reason": main_category,
        "secondary_reasons": secondary,
        "confidence": confidence,
        "evidence": all_evidence,
    }


# ===================================================================
# Public entry point
# ===================================================================


def run() -> dict[str, Any] | None:
    """Classify the player's loss and write the result to disk.

    Reads ``data/normalized_run.json``, applies rule-based checks, and
    saves the classification to ``data/loss_classification.json``.

    Returns the classification dict, or ``None`` when the input is missing.
    """
    LOGGER.info("Loss classifier started")

    # --- 1. Guard: missing input ---------------------------------------
    if not NORMALIZED_RUN_PATH.exists():
        LOGGER.warning("SKIPPED_CONFIG missing %s", NORMALIZED_RUN_PATH)
        print(f"SKIPPED: {NORMALIZED_RUN_PATH} not found — nothing to classify.")
        return None

    # --- 2. Load the normalised run ------------------------------------
    try:
        with NORMALIZED_RUN_PATH.open("r", encoding="utf-8") as fh:
            run_data: dict[str, Any] = json.load(fh)
    except json.JSONDecodeError as exc:
        LOGGER.error("Failed to decode JSON from %s: %s", NORMALIZED_RUN_PATH, exc)
        print(f"ERROR: {NORMALIZED_RUN_PATH} contains invalid JSON.")
        return None
    except OSError as exc:
        LOGGER.error("Failed to read %s: %s", NORMALIZED_RUN_PATH, exc)
        print(f"ERROR: cannot read {NORMALIZED_RUN_PATH}.")
        return None

    # --- 3. Classify ---------------------------------------------------
    classification = _classify(run_data)

    # --- 4. Persist ----------------------------------------------------
    save_json(classification, LOSS_CLASSIFICATION_PATH)
    LOGGER.info(
        "Loss classifier completed — main_reason=%s confidence=%s",
        classification["main_loss_reason"],
        classification["confidence"],
    )
    print(
        f"Loss classified: {classification['main_loss_reason']} "
        f"(confidence {classification['confidence']:.0%}). "
        f"Output → {LOSS_CLASSIFICATION_PATH}"
    )

    return classification


# ---------------------------------------------------------------------------
# Direct execution:  python backend/loss_classifier.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
