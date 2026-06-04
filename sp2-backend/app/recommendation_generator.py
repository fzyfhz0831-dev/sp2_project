from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from app.pipeline_config import (
        PIPELINE_LOG_PATH,
        RUN_ANALYSIS_PATH,
        RUN_ANALYSIS_TXT_PATH,
        RUN_RECOMMENDATIONS_PATH,
    )
    from app.utils import save_json, setup_logger
except ImportError:
    from app.pipeline_config import (
        PIPELINE_LOG_PATH,
        RUN_ANALYSIS_PATH,
        RUN_ANALYSIS_TXT_PATH,
        RUN_RECOMMENDATIONS_PATH,
    )
    from app.utils import save_json, setup_logger


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
LOGGER: logging.Logger = setup_logger(str(PIPELINE_LOG_PATH))

# ---------------------------------------------------------------------------
# Recommendation templates — keyed by problem area
# ---------------------------------------------------------------------------
# Each area maps status levels to a list of (priority, advice) pairs.
# Priority determines which fixes appear first in the report.

_RECOMMENDATIONS: dict[str, dict[str, list[tuple[int, str]]]] = {
    "deck_quality": {
        "bad": [
            (1, "Remove basic Strikes and Defends at every shop. Each basic card you draw is a card that could have been a powerful rare instead."),
            (1, "Event-based card removal (Bonfire Spirits, Designer In-Spire, etc.) is even better than shop removal — take it whenever offered."),
            (2, "Prioritise upgrades over healing at rest sites. An upgraded card is permanently better; healing is temporary."),
            (3, "In Act 1, take 2-3 good attacks before thinking about synergy. A deck that can't kill elites can't win."),
        ],
        "warning": [
            (1, "Your deck has more basic cards than ideal. Look for card-removal opportunities at the next shop or ?-event."),
            (2, "Campsites should lean toward upgrades, not rests, once your HP is above 50%."),
            (3, "Aim for at least 25-30 cards by mid-Act 2. A thin deck with basics is worse than a thick deck with good cards."),
        ],
    },
    "defense": {
        "bad": [
            (1, "Draft more block cards immediately. Without enough block, elite and boss fights will out-damage you before your scaling kicks in."),
            (1, "Upgrade your best block card as soon as possible. An upgraded block card can be 33-50% more efficient."),
            (2, "Weak is a form of block. Piercing Wail, Disarm, and similar cards effectively block for more than their face value."),
            (3, "Dexterity from Footwork or relics like Kunai turns even basic Defends into real block."),
        ],
        "warning": [
            (1, "Add 2-3 more block cards before the next boss. Block density wins long fights."),
            (2, "Upgrade at least one block card. An efficient block card saves HP every single fight."),
        ],
    },
    "scaling": {
        "bad": [
            (1, "Your deck lacks scaling — it cannot handle long fights. Draft at least one scaling power or damage-growth card immediately."),
            (1, "For The Silent: Noxious Fumes, Footwork, After Image, or Envenom. For Ironclad: Demon Form, Barricade, or Feel No Pain. For Defect: Defragment, Echo Form, or Capacitor."),
            (2, "If you cannot find scaling cards, look for alternative win conditions: infinite combos, burst damage, or heavy defense."),
            (3, "A single Catalyst without poison cards (or vice versa) is not scaling — you need the full package."),
        ],
        "warning": [
            (1, "Your deck has only one scaling card. If it's on the bottom of your draw pile, you lose. Add a second scaling option for consistency."),
            (2, "Make sure your scaling card is upgraded. Many scaling cards double in effectiveness when upgraded."),
        ],
    },
    "boss_readiness": {
        "bad": [
            (1, "Entering the boss at low HP is the #1 preventable cause of death. Path to a rest site right before the boss floor."),
            (1, "Save a block potion or a power potion for the boss fight. Potions are free actions that can swing the fight."),
            (2, "Check the boss icon on the map at the start of each act. Build with that specific boss in mind."),
        ],
        "warning": [
            (1, "Plan one rest site within the last 3 floors before the boss. Entering at full HP makes a huge difference."),
            (2, "If the boss is known to deal burst damage (Champ, Bronze Automaton), have a plan for the burst turn specifically."),
        ],
    },
    "pathing": {
        "bad": [
            (1, "Reduce the number of elites you fight each act. 2 elites per act is usually enough; 4+ is greedy and leads to chip deaths."),
            (1, "Act 2 elites (Slavers, Book of Stabbing, Gremlin Leader) are the deadliest in the game. Enter them at full HP or skip them."),
            (2, "Hallway fights give card rewards too. You don't need elites to build a strong deck."),
        ],
        "warning": [
            (1, "After a tough elite fight, take the safer path to a rest site. Chaining elites without healing is the most common cause of mid-act deaths."),
            (2, "Consider ?-event rooms as an alternative to elites. Events often give relics or card transforms without HP loss."),
        ],
    },
    "relic_synergy": {
        "bad": [
            (1, "Fight more elites. Relics are the most permanent form of power in Slay the Spire, and elites are the primary source."),
            (1, "Your deck lacks an energy relic. At the Act 1 or Act 2 boss chest, strongly consider the energy relic even if the downside is painful."),
            (2, "Visit shops when you have 200+ gold. A good relic from the shop can define a winning run."),
        ],
        "warning": [
            (1, "Look for a relic that complements your deck's strategy. Poison decks love Snecko Skull; shiv decks love Shuriken or Kunai."),
            (2, "An energy relic by Act 2 is worth more than almost any other single reward. 4 energy/turn opens up much stronger card choices."),
        ],
    },
}

# Boss-specific advice — surfaced when the analysis includes boss info.
_BOSS_ADVICE: dict[str, list[str]] = {
    "the collector": [
        "Kill torch-head minions immediately — their Mega Debuff stacks and makes all incoming damage unblockable.",
        "AoE cards (Crippling Cloud, Dagger Spray, Die Die Die) shine against The Collector.",
        "Piercing Wail resets minion strength — use it after they've been buffed.",
        "Entering at <60% HP is dangerous because the fight tests your frontloaded block.",
    ],
    "slime boss": [
        "Save high-damage attacks for the split turn. The more damage you deal, the weaker the split slimes.",
        "AoE is valuable after the split to clean up small slimes quickly.",
        "A Fire Potion or Explosive Potion timed right can trivialise the split phase.",
    ],
    "the guardian": [
        "Do NOT attack during defensive mode unless you can out-damage the thorns.",
        "Scale passively (powers, poison) during defensive phases.",
        "Block heavily during the attack turns — they hit hard but are telegraphed.",
    ],
    "hexaghost": [
        "The turn-2 Inferno attack deals damage proportional to your current HP.",
        "Counterintuitively, entering at lower HP makes this fight easier.",
        "Save a block potion for turn 2 if you're entering at high HP.",
    ],
    "bronze automaton": [
        "Each turn it steals one of your cards. Build a deck with redundancy so losing one card doesn't cripple you.",
        "The Hyper Beam on turn 6-7 is devastating — plan to block 50+ or kill before then.",
        "Status cards in your deck are reshuffled back — consider cards that benefit from status generation.",
    ],
    "the champ": [
        "Phase 1 (above 50% HP): deal chip damage. Phase 2 (below 50%): be ready to burst.",
        "The Champ cleanses all debuffs at 50% HP, so hold your big debuffs (Catalyst, etc.) for after.",
        "Execute (turn after the cleanse) hits for 30-40. Have your full block ready.",
    ],
    "time eater": [
        "12-card turn limit punishes spam decks. Play high-impact cards, not many cheap ones.",
        "Powers are still good — you just need to survive the strength gain.",
        "Plan your turns to end on the 12th card with a meaningful play.",
    ],
    "donu and deca": [
        "Focus Donu (the one that buffs strength) first. Ignore Deca's block — strength scaling is the real threat.",
        "Scaling AoE is ideal, but single-target on Donu works if you kill fast.",
        "After Donu dies, Deca alone is manageable with moderate block.",
    ],
    "awakened one": [
        "Powers played in phase 1 give the boss +Strength in phase 2. Either save powers for phase 2 or ensure you can out-scale the strength.",
        "Phase 2 hits hard every turn. Your block engine must be fully online.",
        "The cultists at the start are harmless — use them to set up powers before the real fight begins.",
    ],
}


# ===================================================================
# Recommendation builders
# ===================================================================


def _build_top_mistakes(analysis: dict[str, Any]) -> list[str]:
    """Extract the top 3 mistakes from analysis problems and evidence.

    Returns a list of human-readable mistake descriptions, ordered by
    severity (bad areas first, then sorted by score ascending).
    """
    problems: list[dict[str, Any]] = analysis.get("problems", [])
    if not problems:
        return ["No specific mistakes identified — the run was generally well-played."]

    # Sort: "bad" status first, then by score ascending (worst first).
    sorted_problems = sorted(
        problems,
        key=lambda p: (0 if p["status"] == "bad" else 1, p["score"]),
    )

    mistakes: list[str] = []
    for i, problem in enumerate(sorted_problems[:3]):
        area = problem["area"].replace("_", " ").title()
        mistakes.append(f"{area}: {problem['summary']}")

    return mistakes


def _build_boss_advice(analysis: dict[str, Any]) -> list[str]:
    """Collect boss-specific advice from the analysis evidence.

    Scans the evidence list for boss insight strings and also checks
    the boss name against the known boss-advice table.
    """
    advice: list[str] = []
    boss = analysis.get("boss", "").lower()

    # Check the known boss advice table first.
    if boss in _BOSS_ADVICE:
        advice.extend(_BOSS_ADVICE[boss])

    # Also look in the evidence for any boss-insight strings.
    for item in analysis.get("evidence", []):
        if isinstance(item, str) and item.startswith("Boss insight:"):
            insight = item.replace("Boss insight:", "").strip()
            if insight not in advice:
                advice.append(insight)

    return advice


def _build_next_run_recommendations(analysis: dict[str, Any]) -> list[str]:
    """Generate actionable advice for the next run.

    Walks each problem area and pulls relevant recommendation templates.
    """
    recommendations: list[str] = []
    seen: set[str] = set()
    problems = analysis.get("problems", [])
    scores = analysis.get("scores", {})

    # First, process areas that are explicitly flagged as problems.
    for problem in problems:
        area = problem["area"]
        status = problem["status"]
        templates = _RECOMMENDATIONS.get(area, {}).get(status, [])
        for _, advice in sorted(templates, key=lambda t: t[0]):
            if advice not in seen:
                seen.add(advice)
                recommendations.append(advice)

    # Also check areas scored "good" but with warning-level evidence.
    # Some areas might not be in the problems list but still have useful
    # tips (e.g., an area scored 71 is "good" but barely).
    for area_name, area_data in scores.items():
        if area_data["score"] < 75 and not any(
            p["area"] == area_name for p in problems
        ):
            templates = _RECOMMENDATIONS.get(area_name, {}).get("warning", [])
            for _, advice in sorted(templates, key=lambda t: t[0]):
                if advice not in seen:
                    seen.add(advice)
                    recommendations.append(advice)

    # If nothing was found, give a generic encouraging message.
    if not recommendations:
        recommendations.append(
            "Your build decisions were solid — focus on refining execution "
            "(potion timing, turn-by-turn micro-decisions) rather than "
            "changing your draft strategy."
        )

    return recommendations


def _build_priority_fixes(
    analysis: dict[str, Any],
    recommendations: list[str],
) -> list[str]:
    """Distil the most urgent 3-5 fixes from all recommendations.

    These are the first things a player should try in their next run.
    """
    fixes: list[str] = []
    problems = analysis.get("problems", [])

    # Sort problems: "bad" first, then by lowest score.
    sorted_problems = sorted(
        problems,
        key=lambda p: (0 if p["status"] == "bad" else 1, p["score"]),
    )

    # Take the first recommendation for each problem area as a priority fix.
    for problem in sorted_problems[:5]:
        area = problem["area"]
        status = problem["status"]
        templates = _RECOMMENDATIONS.get(area, {}).get(status, [])
        if templates:
            # Pick the highest-priority (lowest number) advice.
            best = min(templates, key=lambda t: t[0])
            if best[1] not in fixes:
                fixes.append(best[1])

    if not fixes:
        fixes.append(
            "Your run was well-played. Focus on potion usage and turn "
            "optimisation to push from 'good' to 'great'."
        )

    return fixes[:5]


def _build_summary(analysis: dict[str, Any]) -> str:
    """Write a one-paragraph summary of the run analysis."""
    character = analysis.get("character", "Unknown")
    floor = analysis.get("floor", 0)
    boss = analysis.get("boss", "unknown boss")
    main_reason = analysis.get("main_loss_reason", "unknown").replace("_", " ")
    scores = analysis.get("scores", {})

    # Compute overall (simple average).
    if scores:
        overall = round(sum(a["score"] for a in scores.values()) / len(scores))
    else:
        overall = 0

    # Count problems by severity.
    problems = analysis.get("problems", [])
    bad_count = sum(1 for p in problems if p["status"] == "bad")
    warn_count = sum(1 for p in problems if p["status"] == "warning")

    # Determine the weakest area.
    weakest = min(scores.items(), key=lambda kv: kv[1]["score"]) if scores else ("unknown", {"score": 0})

    return (
        f"{character} died on floor {floor} to {boss}. "
        f"The primary cause was {main_reason}. "
        f"Overall deck/build score: {overall}/100. "
        f"The weakest area was {weakest[0].replace('_', ' ')} "
        f"(score {weakest[1]['score']}/100). "
        f"{bad_count} critical issue(s) and {warn_count} warning(s) were found."
    )


def _format_scores(scores: dict[str, dict[str, Any]]) -> str:
    """Render the six area scores as a compact text block."""
    lines: list[str] = []
    for area in ("deck_quality", "defense", "scaling",
                 "boss_readiness", "pathing", "relic_synergy"):
        data = scores.get(area)
        if data is None:
            continue
        bar = _score_bar(data["score"])
        label = area.replace("_", " ").title()
        lines.append(f"  {label:<20} {bar} {data['score']}/100  ({data['status']})")
    return "\n".join(lines)


def _score_bar(score: int, width: int = 15) -> str:
    """Draw a simple ASCII bar for the score.

    Example: score=80 → "[████████████░░░]"
    """
    filled = round(score / 100 * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _format_list(items: list[str], prefix: str = "•") -> str:
    """Format a list of strings as bullet points."""
    if not items:
        return f"  {prefix} (none)"
    return "\n".join(f"  {prefix} {item}" for item in items)


# ===================================================================
# Report formatter — text output
# ===================================================================


def _render_text_report(analysis: dict[str, Any], machine: dict[str, Any]) -> str:
    """Build the full human-readable text report."""
    character = analysis.get("character", "Unknown")
    floor = analysis.get("floor", 0)
    boss = analysis.get("boss", "Unknown Boss")
    generated = analysis.get("generated_at", "")

    lines: list[str] = []
    # --- Header ----------------------------------------------------------
    lines.append("=" * 64)
    lines.append("  SLAY THE SPIRE 2 — RUN DOCTOR LOSS REVIEW")
    lines.append("=" * 64)
    lines.append(f"  Character:    {character}")
    lines.append(f"  Floor:        {floor}")
    lines.append(f"  Boss:         {boss}")
    lines.append(f"  Generated:    {generated}")
    lines.append("")

    # --- Summary ---------------------------------------------------------
    lines.append("-" * 64)
    lines.append("  SUMMARY")
    lines.append("-" * 64)
    lines.append(f"  {machine['summary']}")
    lines.append("")

    # --- Scores ----------------------------------------------------------
    lines.append("-" * 64)
    lines.append("  AREA SCORES")
    lines.append("-" * 64)
    scores = analysis.get("scores", {})
    lines.append(_format_scores(scores))
    lines.append("")

    # --- Top Mistakes ----------------------------------------------------
    lines.append("-" * 64)
    lines.append("  TOP MISTAKES")
    lines.append("-" * 64)
    lines.append(_format_list(machine["top_mistakes"]))
    lines.append("")

    # --- Boss Advice -----------------------------------------------------
    lines.append("-" * 64)
    lines.append("  BOSS-SPECIFIC ADVICE")
    lines.append("-" * 64)
    lines.append(_format_list(machine["boss_advice"]))
    lines.append("")

    # --- Next-Run Recommendations ----------------------------------------
    lines.append("-" * 64)
    lines.append("  NEXT-RUN RECOMMENDATIONS")
    lines.append("-" * 64)
    lines.append(_format_list(machine["next_run_recommendations"]))
    lines.append("")

    # --- Priority Fixes --------------------------------------------------
    lines.append("-" * 64)
    lines.append("  PRIORITY FIXES (try these first)")
    lines.append("-" * 64)
    for i, fix in enumerate(machine["priority_fixes"], 1):
        lines.append(f"  {i}. {fix}")
    lines.append("")

    # --- Evidence --------------------------------------------------------
    lines.append("-" * 64)
    lines.append("  SUPPORTING EVIDENCE")
    lines.append("-" * 64)
    evidence = analysis.get("evidence", [])
    if evidence:
        for item in evidence:
            lines.append(f"  - {item}")
    else:
        lines.append("  (no evidence recorded)")
    lines.append("")

    # --- Footer ----------------------------------------------------------
    lines.append("=" * 64)
    lines.append("  End of report. Good luck on your next run!")
    lines.append("=" * 64)

    return "\n".join(lines)


def _write_text_report(text: str) -> None:
    """Write the plain-text report to disk using UTF-8."""
    try:
        RUN_ANALYSIS_TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUN_ANALYSIS_TXT_PATH.write_text(text, encoding="utf-8")
        LOGGER.info("Text report written to %s", RUN_ANALYSIS_TXT_PATH)
    except OSError as exc:
        LOGGER.error("Failed to write text report to %s: %s", RUN_ANALYSIS_TXT_PATH, exc)
        raise


# ===================================================================
# Public entry point
# ===================================================================


def run() -> dict[str, Any] | None:
    """Generate recommendations and write both the text and JSON reports.

    Reads ``data/run_analysis.json``, builds human-readable and
    machine-readable recommendations, and saves:
    - ``data/run_analysis.txt`` — human-readable loss review
    - ``data/run_recommendations.json`` — structured recommendation data

    Returns the machine-readable dict, or ``None`` when the input is
    missing.
    """
    LOGGER.info("Recommendation generator started")

    # --- 1. Guard: missing input ---------------------------------------
    if not RUN_ANALYSIS_PATH.exists():
        LOGGER.warning("SKIPPED_CONFIG missing %s", RUN_ANALYSIS_PATH)
        print(f"SKIPPED: {RUN_ANALYSIS_PATH} not found — nothing to recommend on.")
        return None

    # --- 2. Load analysis ----------------------------------------------
    try:
        with RUN_ANALYSIS_PATH.open("r", encoding="utf-8") as fh:
            analysis: dict[str, Any] = json.load(fh)
    except json.JSONDecodeError as exc:
        LOGGER.error("Failed to decode JSON from %s: %s", RUN_ANALYSIS_PATH, exc)
        print(f"ERROR: {RUN_ANALYSIS_PATH} contains invalid JSON.")
        return None
    except OSError as exc:
        LOGGER.error("Failed to read %s: %s", RUN_ANALYSIS_PATH, exc)
        print(f"ERROR: cannot read {RUN_ANALYSIS_PATH}.")
        return None

    # --- 3. Build recommendations --------------------------------------
    top_mistakes = _build_top_mistakes(analysis)
    boss_advice = _build_boss_advice(analysis)
    next_run_recs = _build_next_run_recommendations(analysis)
    priority_fixes = _build_priority_fixes(analysis, next_run_recs)
    summary = _build_summary(analysis)

    machine: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "top_mistakes": top_mistakes,
        "boss_advice": boss_advice,
        "next_run_recommendations": next_run_recs,
        "priority_fixes": priority_fixes,
    }

    # --- 4. Write text report ------------------------------------------
    text_report = _render_text_report(analysis, machine)
    _write_text_report(text_report)

    # --- 5. Write machine-readable JSON --------------------------------
    save_json(machine, RUN_RECOMMENDATIONS_PATH)

    LOGGER.info(
        "Recommendation generator completed — %s mistakes, %s fixes",
        len(top_mistakes),
        len(priority_fixes),
    )
    print(
        f"Recommendations generated: {len(priority_fixes)} priority fixes, "
        f"{len(boss_advice)} boss tips. "
        f"Output → {RUN_ANALYSIS_TXT_PATH}, {RUN_RECOMMENDATIONS_PATH}"
    )

    return machine


# ---------------------------------------------------------------------------
# Direct execution:  python backend/recommendation_generator.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
