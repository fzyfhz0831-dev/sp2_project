"""
mock_ai_analyzer.py — Locally generate mock AI review analysis from a run.

This module simulates the output of an LLM-powered run reviewer by mapping
each possible risk flag to pre-written analysis text.  The output format is
identical to :func:`prompt_builder.build_review_prompt` so downstream
consumers can swap between the real AI prompt builder and this mock.

Functions
---------
- analyze_run_locally(run_data, run_summary) -> dict

CLI usage
---------
    python backend/mock_ai_analyzer.py backend/mock_data/runs/mock-001-low-hp-elite.json
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
logger = logging.getLogger("mock_ai_analyzer")

# ===================================================================
# Flag → analysis mapping tables
# ===================================================================

# Each risk flag maps to a pre-written analysis block with keys:
#   death_reason  — one-line death cause
#   mistake       — {type, detail} dict for key_mistakes
#   deck_note     — appended to deck_analysis
#   route_note    — appended to route_analysis
#   relic_note    — appended to relic_analysis
#   advice        — one-line next-run tip

_FLAG_ANALYSIS: dict[str, dict[str, Any]] = {
    "low_hp_before_elite": {
        "death_reason": (
            "Player entered an elite fight with critically low HP. "
            "Without enough health to absorb burst damage, the run "
            "collapsed in a single bad turn."
        ),
        "mistake": {
            "type": "hp_management",
            "detail": (
                "Entered an elite fight below 50% max HP. Elites are "
                "designed to deal heavy frontloaded damage — entering with "
                "low HP means even a single unlucky draw order can end the run. "
                "Should have rested at the previous campfire or chosen a "
                "safer path that avoided the elite."
            ),
        },
        "deck_note": (
            "The deck may have been capable, but low HP meant there was "
            "zero margin for error in the elite fight. "
        ),
        "route_note": (
            "The path led into an elite with insufficient HP. Always check "
            "your HP before committing to an elite node — if below 50%, "
            "strongly consider an alternate route. "
        ),
        "relic_note": "",
        "advice": (
            "Never enter an elite below 50% HP. If the campfire can't heal "
            "you above that threshold, take a different path — skipping one "
            "elite is better than losing the entire run."
        ),
    },
    "poor_defense_hint": {
        "death_reason": (
            "The deck was heavily skewed toward attack cards with "
            "insufficient block. Chip damage accumulated across multiple "
            "fights until a lethal turn ended the run."
        ),
        "mistake": {
            "type": "deck_balance",
            "detail": (
                "Too few block/skill cards relative to attack cards. "
                "Without reliable defense, every fight becomes a race — "
                "and the player's HP is the timer. Draft at least 4–5 "
                "solid block cards by mid-Act 1 to stabilize."
            ),
        },
        "deck_note": (
            "The deck lacked sufficient block cards. A healthy deck "
            "typically runs 30–40% defensive options to survive "
            "multi-turn fights. "
        ),
        "route_note": (
            "With a defense-light deck, hallway fights and elites become "
            "much more dangerous — every point of preventable damage "
            "shortens the run. "
        ),
        "relic_note": "",
        "advice": (
            "Draft block cards early — aim for at least 4 block cards "
            "by floor 8. Skipping block for more damage is a common trap "
            "that leads to slow HP attrition."
        ),
    },
    "thick_deck": {
        "death_reason": (
            "A bloated deck made it impossible to draw key cards "
            "consistently. Core powers and block cards were buried "
            "at the bottom of the draw pile."
        ),
        "mistake": {
            "type": "deck_bloat",
            "detail": (
                "Deck size exceeded 25 cards, diluting the draw pool. "
                "Key cards appear less frequently, making the deck "
                "inconsistent. Skip card rewards more often and remove "
                "starter cards (Strikes, Defends) at shops."
            ),
        },
        "deck_note": (
            "A large deck reduces consistency — every card added beyond "
            "~20 makes it harder to find your best cards on the turn "
            "you need them. "
        ),
        "route_note": (
            "A thick deck needs more campfire upgrades to make each "
            "card pull its weight. Consider prioritizing shops for "
            "card removal. "
        ),
        "relic_note": "",
        "advice": (
            "Skip card rewards more often. A lean 15–20 card deck cycles "
            "key cards faster and is far more consistent. Remove Strikes "
            "at shops whenever possible."
        ),
    },
    "died_to_elite": {
        "death_reason": (
            "The run ended in an elite fight. The deck was not prepared "
            "for the specific demands of that elite — frontloaded damage, "
            "AoE, or scaling."
        ),
        "mistake": {
            "type": "elite_preparation",
            "detail": (
                "Died to an elite fight. Each elite tests a specific "
                "aspect of your deck: Gremlin Nob punishes skills, "
                "Lagavulin demands scaling, Sentries need AoE. Before "
                "committing to an elite path, ensure your deck can "
                "handle the possible matchups."
            ),
        },
        "deck_note": (
            "The deck was not tuned for the elite fight that killed it. "
            "Different elites require different answers — know which "
            "elites can appear in each act and draft accordingly. "
        ),
        "route_note": (
            "The path ended at an elite. Elite fights are the biggest "
            "difficulty spikes in each act — only take them when your "
            "deck has proven itself in hallway fights. "
        ),
        "relic_note": "",
        "advice": (
            "Prepare for elites: Gremlin Nob demands attacks (skills are "
            "dead draws), Lagavulin needs scaling, Sentries need AoE. "
            "Know which elite you might face and draft accordingly."
        ),
    },
    "no_scaling": {
        "death_reason": (
            "The deck lacked scaling mechanics (Power cards or engines). "
            "Damage output plateaued while enemies continued to grow "
            "stronger each turn."
        ),
        "mistake": {
            "type": "no_scaling",
            "detail": (
                "Fewer than 2 Power cards in the deck. Without scaling, "
                "the deck's damage caps at its base output — fine for "
                "short fights, but fatal against bosses and tougher "
                "elites that grow stronger over time."
            ),
        },
        "deck_note": (
            "Zero or very few Power cards — the deck had no way to "
            "scale its output beyond base values. Bosses and late-act "
            "elites will out-scale an unscaling deck. "
        ),
        "route_note": (
            "Without scaling, boss fights become a hard DPS check. "
            "Avoid elite-heavy paths in later acts if your deck "
            "still lacks scaling by the Act 1 boss. "
        ),
        "relic_note": "",
        "advice": (
            "Pick at least 2 Power cards or scaling engines by the "
            "Act 1 boss. Without scaling, your damage falls off in "
            "Act 2 and beyond."
        ),
    },
    "bad_upgrade": {
        "death_reason": (
            "Campfires were spent healing instead of upgrading key "
            "cards. The deck fell behind the power curve as enemies "
            "scaled faster than the player's output."
        ),
        "mistake": {
            "type": "upgrade_priority",
            "detail": (
                "Healed at most campfires instead of upgrading. A heal "
                "gives ~20 HP once; an upgrade on a high-impact card "
                "saves HP in every subsequent fight. Prioritize upgrades "
                "— heal only when necessary to survive the next fight."
            ),
        },
        "deck_note": (
            "Key cards remained unupgraded because campfires were used "
            "for healing. An upgraded win-condition card provides value "
            "in every fight that follows. "
        ),
        "route_note": (
            "Too many campfires spent resting. Each campfire is an "
            "opportunity to permanently improve a card — treat healing "
            "as a fallback, not the default. "
        ),
        "relic_note": "",
        "advice": (
            "Upgrade before resting. Ask: 'Does this upgrade save me "
            "more HP over the rest of the run than this one heal of "
            "~20 HP?' Usually, the answer is yes."
        ),
    },
    "greedy_path": {
        "death_reason": (
            "The player took an overly aggressive path with too many "
            "elites and not enough campfires. HP was ground down with "
            "no opportunity to recover."
        ),
        "mistake": {
            "type": "greedy_pathing",
            "detail": (
                "Fought too many elites without adequate rests in between. "
                "Each elite is a significant HP tax — a sustainable path "
                "balances elite fights with campfires and shops for "
                "recovery and deck improvement."
            ),
        },
        "deck_note": (
            "The deck may have been reasonable, but the aggressive path "
            "gave it no time to stabilize. Even a strong deck needs "
            "campfires and shops between elite fights. "
        ),
        "route_note": (
            "The path was too greedy — too many elites, not enough "
            "recovery nodes. A safer route with fewer elites and more "
            "campfires gives the deck time to come together. "
        ),
        "relic_note": "",
        "advice": (
            "Plan your route from floor 0. Count elites, campfires, "
            "and shops. A balanced Act 1 has 1–2 elites and 2+ "
            "campfires. More elites means more relics, but only if "
            "you survive."
        ),
    },
}


# ===================================================================
# analyze_run_locally
# ===================================================================

def analyze_run_locally(
    run_data: dict[str, Any],
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    """Generate mock AI analysis from a run's risk flags.

    Each flag in ``run_summary["possible_risk_flags"]`` is mapped to
    pre-written analysis text covering the death reason, key mistakes,
    deck/route/relic commentary, and actionable advice.

    Parameters
    ----------
    run_data : dict
        The full raw run dict (as loaded by :func:`run_parser.load_run`).
    run_summary : dict
        Output of :func:`run_parser.summarize_run`.

    Returns
    -------
    dict
        Keys: summary, main_death_reason, key_mistakes, deck_analysis,
        route_analysis, relic_analysis, next_run_advice.
        Format matches :func:`prompt_builder.build_review_prompt`.
    """
    # --- extract data ---------------------------------------------------------
    character = run_data.get("character", "Unknown")
    killed_by = run_data.get("killed_by", "unknown enemy")
    floor_reached = run_data.get("floor_reached", 0)
    cards: list[str] = run_data.get("cards", [])
    relics: list[str] = run_data.get("relics", [])
    path: list[dict[str, Any]] = run_data.get("path", [])
    flags: list[str] = run_summary.get("possible_risk_flags", [])

    elite_count = run_summary.get("elite_count", 0)
    boss_count = run_summary.get("boss_count", 0)
    relic_count = run_summary.get("relic_count", len(relics))

    # --- summary --------------------------------------------------------------
    summary = (
        f"[MOCK ANALYSIS] {character} died on floor {floor_reached} "
        f"against {killed_by}. "
        f"Deck: {len(cards)} cards. "
        f"Relics: {relic_count}. "
        f"Elites fought: {elite_count}. "
        f"Bosses fought: {boss_count}. "
        f"Risk flags triggered: {', '.join(flags) if flags else 'none'}."
    )

    # --- main death reason ----------------------------------------------------
    death_reasons: list[str] = []
    mistakes: list[dict[str, Any]] = []
    deck_notes: list[str] = []
    route_notes: list[str] = []
    relic_notes: list[str] = []
    advice_items: list[str] = []

    for flag in flags:
        block = _FLAG_ANALYSIS.get(flag)
        if block is None:
            logger.warning("Unknown risk flag: %s — skipping.", flag)
            continue

        if block["death_reason"]:
            death_reasons.append(block["death_reason"])
        if block["mistake"]:
            mistakes.append(dict(block["mistake"]))
        if block["deck_note"]:
            deck_notes.append(block["deck_note"])
        if block["route_note"]:
            route_notes.append(block["route_note"])
        if block["relic_note"]:
            relic_notes.append(block["relic_note"])
        if block["advice"]:
            advice_items.append(block["advice"])

    # --- main_death_reason ----------------------------------------------------
    if death_reasons:
        main_death_reason = " ".join(death_reasons)
    else:
        main_death_reason = (
            f"{character} was defeated by {killed_by} on floor {floor_reached}. "
            "No specific risk flag was triggered — the loss may have been "
            "due to draw order, a single misplay, or enemy high-roll."
        )

    # --- key_mistakes (attach floor context) ----------------------------------
    # Try to infer a relevant floor for each mistake from the path data.
    elite_floors = [p.get("floor") for p in path if p.get("type") == "elite"]
    last_floor = path[-1].get("floor", floor_reached) if path else floor_reached

    for i, m in enumerate(mistakes):
        if m["type"] in ("hp_management", "elite_preparation") and elite_floors:
            m["floor"] = elite_floors[-1] if i < len(elite_floors) else elite_floors[0]
        elif m["type"] == "greedy_pathing":
            m["floor"] = elite_floors[-1] if elite_floors else last_floor
        elif m["type"] == "upgrade_priority":
            rest_floors = [p.get("floor") for p in path if p.get("type") == "rest"]
            m["floor"] = rest_floors[-1] if rest_floors else last_floor
        else:
            m["floor"] = last_floor

    if not mistakes:
        mistakes.append({
            "floor": floor_reached,
            "type": "unclear",
            "detail": (
                "No clear mistake pattern was detected by the mock analyzer. "
                "The death may have been caused by draw order, a critical "
                "misplay on the final turn, or enemy attack RNG."
            ),
        })

    # --- deck_analysis --------------------------------------------------------
    if deck_notes:
        deck_analysis = (
            f"[MOCK] {character} deck with {len(cards)} cards. "
            + " ".join(deck_notes)
        )
    else:
        deck_analysis = (
            f"[MOCK] {character} deck with {len(cards)} cards. "
            "No major deck-building issues flagged by the mock analyzer."
        )

    # --- route_analysis -------------------------------------------------------
    last_type = path[-1].get("type", "?") if path else "?"
    route_base = (
        f"[MOCK] Run reached floor {floor_reached}. "
        f"Last node: {last_type}. "
        f"Elites: {elite_count}, Bosses: {boss_count}. "
    )
    if route_notes:
        route_analysis = route_base + " ".join(route_notes)
    else:
        route_analysis = route_base + (
            "No major pathing issues flagged by the mock analyzer."
        )

    # --- relic_analysis -------------------------------------------------------
    if relics:
        relic_lines = [f"[MOCK] Collected {len(relics)} relic(s):"]
        for r in relics:
            relic_lines.append(f"  - {r}")
        if relic_notes:
            relic_lines.append("")
            relic_lines.append("Synergy notes:")
            for note in relic_notes:
                relic_lines.append(f"  - {note}")
        relic_analysis = "\n".join(relic_lines)
    else:
        relic_analysis = "[MOCK] No relics collected."

    # --- next_run_advice ------------------------------------------------------
    if not advice_items:
        advice_items.append(
            "Review the final fight turn-by-turn. Sometimes the mistake "
            "is a single misplay — wrong target, wrong play order, or "
            "a potion left unused."
        )

    return {
        "summary": summary,
        "main_death_reason": main_death_reason,
        "key_mistakes": mistakes,
        "deck_analysis": deck_analysis,
        "route_analysis": route_analysis,
        "relic_analysis": relic_analysis,
        "next_run_advice": advice_items,
    }


# ===================================================================
# CLI entry point
# ===================================================================

def main() -> None:
    """CLI: load a run, run mock analysis, print JSON.

    Usage::

        python backend/mock_ai_analyzer.py backend/mock_data/runs/mock-001-low-hp-elite.json
    """
    if len(sys.argv) < 2:
        print("Usage:  python backend/mock_ai_analyzer.py <path_to_run.json>")
        sys.exit(1)

    file_path = sys.argv[1]

    # 1. Load the run
    try:
        from app.run_parser_full import load_run, summarize_run
    except ImportError:
        from app.run_parser_full import load_run, summarize_run

    try:
        run_data = load_run(file_path)
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {file_path}: {exc}")
        sys.exit(1)

    # 2. Summarise
    run_summary = summarize_run(run_data)
    logger.info(
        "Run summary: %s | flags: %s",
        run_summary.get("character"),
        run_summary.get("possible_risk_flags"),
    )

    # 3. Mock analysis
    analysis = analyze_run_locally(run_data, run_summary)

    # 4. Output
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
