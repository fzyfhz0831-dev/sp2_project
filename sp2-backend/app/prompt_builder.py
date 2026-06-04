"""
prompt_builder.py — Build an AI-ready review prompt from a Slay the Spire 2 run.

Functions
---------
- load_knowledge_base() -> dict
- build_review_prompt(run_summary, run_data, knowledge_base) -> dict

CLI usage
---------
    python backend/prompt_builder.py backend/mock_data/runs/mock-001-low-hp-elite.json
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
logger = logging.getLogger("prompt_builder")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_KB_DIR = Path(__file__).resolve().parent / "mock_data" / "knowledge_base"

# ---------------------------------------------------------------------------
# load_knowledge_base
# ---------------------------------------------------------------------------

def load_knowledge_base() -> dict[str, Any]:
    """Load the scraped wiki knowledge base.

    Returns a dict with keys: ``cards``, ``relics``, ``status_effects``,
    ``characters``.  Each value is a list of dicts.
    """
    kb: dict[str, Any] = {}
    for stem in ("cards", "relics", "status_effects", "characters"):
        path = _KB_DIR / f"{stem}.json"
        try:
            with path.open("r", encoding="utf-8") as fh:
                kb[stem] = json.load(fh)
            logger.info("Loaded %d %s from knowledge base.", len(kb[stem]), stem)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load %s: %s", stem, exc)
            kb[stem] = []
    return kb


# ===================================================================
# Internal analysis helpers
# ===================================================================

def _build_card_index(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a lowercased name → card-dict index for fast lookups."""
    return {c["name"].lower(): c for c in cards if "name" in c}


def _build_relic_index(relics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a lowercased name → relic-dict index."""
    return {r["name"].lower(): r for r in relics if "name" in r}


def _classify_card(cname: str, card_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return ``{type, cost, rarity}`` for a card name string.

    Falls back to keyword heuristics when the card is not in the index.
    """
    base = cname.rsplit("+", 1)[0].strip().lower()
    entry = card_index.get(base) or card_index.get(cname.lower())
    if entry:
        cost_raw = entry.get("cost", "0")
        try:
            cost = int(cost_raw)
        except (ValueError, TypeError):
            cost = 0
        return {
            "type": entry.get("type", "?"),
            "cost": cost,
            "rarity": entry.get("rarity", "?"),
        }

    # --- heuristic fallback ---
    _POWER_KW = (
        "form", "inflame", "brutality", "barricade", "corruption",
        "dark embrace", "evolve", "feel no pain", "fire breathing",
        "juggernaut", "metallicize", "rupture", "combust",
        "afterimage", "envenom", "noxious fumes", "tools of the trade",
        "well laid plans", "wraith form", "thousand cuts",
        "creative ai", "echo form", "electrodynamics", "hello world",
        "machine learning", "self repair", "storm", "capacitor",
        "defragment", "heatsinks", "loop", "infinite blades",
        "caltrops", "beacon of hope", "constellation", "empyrean",
        "oracle", "pillar of creation", "starlight beacon",
        "stellar core", "nova", "zenith", "dread presence",
        "unholy vigor", "wither", "star align", "doom clock",
        "dark ritual", "lich form", "aggression", "automation", "arsenal",
    )
    _SKILL_KW = (
        "defend", "shield", "block", "barrier", "guard", "armor", "wall",
        "footwork", "dodge", "cloak", "deflect", "escape", "backflip",
        "leg sweep", "piercing wail", "survivor", "blur", "concentrate",
        "expertise", "outmaneuver", "prepared", "reflex", "tactician",
        "acrobatics", "adrenaline", "alchemize", "apparition",
        "double energy", "equilibrium", "fission", "hologram", "reboot",
        "recycle", "seek", "turbo", "bloodletting", "burning pact",
        "offering", "second wind", "seeing red", "sentinel", "shrug",
        "cosmic shield", "twilight shield", "void step",
        "bone armor", "nether shield", "chill of the grave",
        "life drain", "reanimate", "soul bind",
    )

    low = base
    if any(kw in low for kw in _POWER_KW):
        return {"type": "Power", "cost": 2, "rarity": "?"}
    if any(kw in low for kw in _SKILL_KW):
        return {"type": "Skill", "cost": 1, "rarity": "?"}
    # Default to Attack
    return {"type": "Attack", "cost": 2, "rarity": "?"}


def _relic_effect(relic_name: str, relic_index: dict[str, dict[str, Any]]) -> str:
    """Return the effect text for a relic, or '' if unknown."""
    entry = relic_index.get(relic_name.lower())
    return entry.get("effect", "") if entry else ""


# ===================================================================
# build_review_prompt
# ===================================================================

def build_review_prompt(
    run_summary: dict[str, Any],
    run_data: dict[str, Any],
    knowledge_base: dict[str, Any],
) -> dict[str, Any]:
    """Generate a structured English review / prompt from a run.

    Parameters
    ----------
    run_summary : dict
        Output of :func:`run_parser.summarize_run`.
    run_data : dict
        The full raw run dict.
    knowledge_base : dict
        Output of :func:`load_knowledge_base`.

    Returns
    -------
    dict
        Keys: summary, main_death_reason, key_mistakes, deck_analysis,
        route_analysis, relic_analysis, next_run_advice.
    """
    # --- indexes ------------------------------------------------------------
    card_index = _build_card_index(knowledge_base.get("cards", []))
    relic_index = _build_relic_index(knowledge_base.get("relics", []))

    cards: list[str] = run_data.get("cards", [])
    relics: list[str] = run_data.get("relics", [])
    _path: list[dict[str, Any]] = run_data.get("path", [])
    character = run_data.get("character", "Unknown")
    killed_by = run_data.get("killed_by", "unknown enemy")
    floor_reached = run_data.get("floor_reached", 0)
    max_hp = int(run_data.get("max_hp", 80))
    flags: list[str] = run_summary.get("possible_risk_flags", [])

    # --- deck composition ---------------------------------------------------
    attack_cards: list[dict[str, Any]] = []
    skill_cards: list[dict[str, Any]] = []
    power_cards: list[dict[str, Any]] = []
    costs: list[int] = []

    for cname in cards:
        info = _classify_card(cname, card_index)
        info["name"] = cname
        costs.append(info["cost"])
        if info["type"] == "Attack":
            attack_cards.append(info)
        elif info["type"] == "Skill":
            skill_cards.append(info)
        elif info["type"] == "Power":
            power_cards.append(info)

    avg_cost = sum(costs) / len(costs) if costs else 0
    high_cost = [c for c in cards if _classify_card(c, card_index)["cost"] >= 3]

    # --- path analysis ------------------------------------------------------
    elites_fought: list[dict[str, Any]] = []
    rests_taken: list[dict[str, Any]] = []
    elite_entries: list[dict[str, Any]] = []
    upgrades_missed = 0

    for p in _path:
        ftype = p.get("type", "")
        if ftype == "elite":
            elites_fought.append(p)
            hp_before = p.get("hp_before", max_hp)
            elite_entries.append({"floor": p.get("floor"), "hp_before": hp_before})
        elif ftype == "rest":
            rests_taken.append(p)
            if not p.get("picked_card") and p.get("hp_before", 0) < max_hp * 0.8:
                upgrades_missed += 1

    # --- relic synergy check ------------------------------------------------
    relic_effects = {r: _relic_effect(r, relic_index) for r in relics}
    relic_notes: list[str] = []
    for rname, reffect in relic_effects.items():
        if not reffect:
            relic_notes.append(f"{rname} — (effect unknown in knowledge base)")
        elif "energy" in reffect.lower() or "gain" in reffect.lower():
            # Check if deck can use energy
            if avg_cost < 1.5:
                relic_notes.append(
                    f"{rname} provides extra energy, but your deck's average "
                    f"cost is only {avg_cost:.1f} — you may not need it."
                )
        if "block" in reffect.lower() and len(skill_cards) < 3:
            relic_notes.append(
                f"{rname} generates Block, but you have very few block cards."
            )

    # =================================================================
    # Build the review
    # =================================================================

    # --- summary ------------------------------------------------------------
    summary = (
        f"{character} died on floor {floor_reached} against {killed_by}. "
        f"The deck contained {len(cards)} cards ({len(attack_cards)} attack, "
        f"{len(skill_cards)} skill, {len(power_cards)} power) with an average "
        f"cost of {avg_cost:.1f}. "
        f"{len(relics)} relics were collected. "
        f"The run had {len(elites_fought)} elite fight(s) and "
        f"{run_summary.get('boss_count', 0)} boss fight(s)."
    )

    # --- main death reason --------------------------------------------------
    death_reasons: dict[str, str] = {
        "low_hp_before_elite": (
            f"You entered an elite fight with critically low HP "
            f"(below {max_hp // 2}). Always heal or skip the elite if your HP "
            f"is too low to survive burst damage."
        ),
        "poor_defense_hint": (
            "Your deck was heavily skewed toward attack cards with "
            "insufficient block. Without reliable defense, chip damage "
            "accumulated until a lethal turn."
        ),
        "thick_deck": (
            f"A bloated deck ({len(cards)} cards) made it impossible to draw "
            "key cards consistently. Trim your deck at shops and events."
        ),
        "died_to_elite": (
            f"You died to an elite fight ({killed_by}). Elite fights demand "
            "strong frontloaded damage and a block plan — ensure both are "
            "online before committing to an elite path."
        ),
        "no_scaling": (
            "Your deck lacked Power cards or scaling mechanics. Against "
            "longer fights, your damage output plateaued while the enemy "
            "continued to scale."
        ),
        "bad_upgrade": (
            f"You rested at {upgrades_missed} campfire(s) instead of upgrading. "
            "Prioritize upgrading your most impactful cards — healing at "
            "campfires should be a last resort, not the default."
        ),
        "greedy_path": (
            f"You fought {len(elites_fought)} elites with insufficient rests "
            "in between. A safer path with fewer elites and more campfires "
            "would have given your deck time to stabilize."
        ),
    }
    main_death_reason = " ".join(
        death_reasons[f] for f in flags if f in death_reasons
    )
    if not main_death_reason:
        main_death_reason = (
            f"{character} was defeated by {killed_by} on floor {floor_reached}. "
            "No specific risk flag was triggered; the loss may have been due to "
            "draw order, a single misplay, or enemy high-roll."
        )

    # --- key mistakes -------------------------------------------------------
    key_mistakes: list[dict[str, Any]] = []

    # HP management mistakes
    for p in elites_fought:
        hp_before = p.get("hp_before", max_hp)
        hp_after = p.get("hp_after", 0)
        hp_lost = hp_before - hp_after
        if hp_before < max_hp * 0.5:
            key_mistakes.append({
                "floor": p.get("floor"),
                "type": "hp_management",
                "detail": (
                    f"Entered elite on floor {p.get('floor')} with only "
                    f"{hp_before}/{max_hp} HP. Lost {hp_lost} HP "
                    "in this fight. Should have rested or pathed around this elite."
                ),
            })
        elif hp_lost > max_hp * 0.35:
            key_mistakes.append({
                "floor": p.get("floor"),
                "type": "elite_preparation",
                "detail": (
                    f"Lost {hp_lost} HP in the elite fight on floor "
                    f"{p.get('floor')} ({hp_before} → {hp_after}). "
                    "This indicates the deck wasn't ready for this elite — "
                    "consider drafting more frontloaded damage or block first."
                ),
            })

    # Upgrade mistakes
    if upgrades_missed >= 2 and len(rests_taken) >= 3:
        key_mistakes.append({
            "floor": "multiple",
            "type": "upgrade_priority",
            "detail": (
                f"Rested at {upgrades_missed}/{len(rests_taken)} campfires "
                "instead of upgrading. Key upgrades on high-impact cards would "
                "have provided lasting power across all subsequent fights."
            ),
        })

    # Deck-building mistakes
    if len(high_cost) > len(cards) * 0.3:
        key_mistakes.append({
            "floor": "multiple",
            "type": "deck_curve",
            "detail": (
                f"{len(high_cost)} of {len(cards)} cards cost 3+ energy. "
                "A top-heavy curve leaves you unable to play multiple cards "
                "per turn. Add more 0–1 cost cards for consistency."
            ),
        })

    if avg_cost > 2.2:
        key_mistakes.append({
            "floor": "multiple",
            "type": "energy_economy",
            "detail": (
                f"Average card cost is {avg_cost:.1f} — too high. Without "
                "energy generation or cost reduction, you regularly face "
                "turns where you can only play one card."
            ),
        })

    # Path mistakes
    rest_count = len(rests_taken)
    if len(elites_fought) >= 3 and rest_count < len(elites_fought):
        key_mistakes.append({
            "floor": "multiple",
            "type": "greedy_pathing",
            "detail": (
                f"Fought {len(elites_fought)} elites with only {rest_count} "
                "rest(s). Each elite is a significant HP tax — make sure you "
                "have enough campfires to recover between them."
            ),
        })

    # Missing block
    if len(skill_cards) < max(3, len(cards) * 0.2):
        key_mistakes.append({
            "floor": "multiple",
            "type": "no_block",
            "detail": (
                f"Only {len(skill_cards)} block/skill cards in a {len(cards)}-card "
                "deck. You cannot block reliably. Draft at least 3–5 solid "
                "block cards by mid-Act 1."
            ),
        })

    if not key_mistakes:
        key_mistakes.append({
            "floor": floor_reached,
            "type": "unclear",
            "detail": (
                "No clear mistake pattern detected. The death may have been "
                "caused by bad draw order, a critical misplay, or enemy "
                "attack RNG on the final turn."
            ),
        })

    # --- deck analysis ------------------------------------------------------
    deck_parts = []
    deck_parts.append(
        f"The {len(cards)}-card deck was built around {character}. "
    )
    if attack_cards:
        deck_parts.append(
            f"It had {len(attack_cards)} attack cards "
            f"(avg cost {sum(c['cost'] for c in attack_cards) / len(attack_cards):.1f}). "
        )
    if skill_cards:
        deck_parts.append(
            f"{len(skill_cards)} skill/block cards "
            f"(avg cost {sum(c['cost'] for c in skill_cards) / len(skill_cards):.1f}). "
        )
    if power_cards:
        names = [c["name"] for c in power_cards]
        deck_parts.append(
            f"{len(power_cards)} power card(s): {', '.join(names)}. "
        )
    else:
        deck_parts.append("No power cards — the deck had zero scaling. ")

    if high_cost:
        names = [c for c in high_cost]
        deck_parts.append(
            f"High-cost cards ({', '.join(names[:5])}"
            f"{'...' if len(names) > 5 else ''}) make the deck slow. "
        )

    deck_parts.append(
        f"Average cost: {avg_cost:.1f}. "
        f"Ideal is 1.2–1.8 with most cards at 1–2 cost and a few 0-cost cards "
        f"for free tempo."
    )
    deck_analysis = "".join(deck_parts)

    # --- route analysis -----------------------------------------------------
    route_parts = []
    act1_end = 17
    act1_elites = [p for p in elites_fought if p.get("floor", 99) <= act1_end]
    act1_rests = [p for p in rests_taken if p.get("floor", 99) <= act1_end]

    route_parts.append(
        f"The run reached floor {floor_reached}. "
        f"In Act 1 (floors 1–17): {len(act1_elites)} elite(s), "
        f"{len(act1_rests)} rest(s). "
    )

    if len(act1_elites) >= 2 and len(act1_rests) <= 1:
        route_parts.append(
            "This is an aggressive path — multiple elites with minimal "
            "recovery. A safer route would pick 1 elite and 2+ campfires "
            "in Act 1 so the deck can stabilize before taking risks. "
        )

    if floor_reached <= 17:
        route_parts.append(
            "The run ended in Act 1. Focus on frontloaded damage and one "
            "reliable block card before the first elite. "
        )
    elif floor_reached <= 33:
        route_parts.append(
            "The run reached Act 2. By this point you need AoE solutions "
            "and scaling for the boss. "
        )

    route_parts.append(
        f"Last floor type before death: {_path[-1].get('type', '?') if _path else '?'}. "
        f"Final HP was 0. "
    )
    route_analysis = "".join(route_parts)

    # --- relic analysis -----------------------------------------------------
    if relics:
        relic_lines = [f"Collected {len(relics)} relic(s):"]
        for rname in relics:
            eff = _relic_effect(rname, relic_index)
            short = (eff[:70] + "...") if len(eff) > 70 else eff
            relic_lines.append(f"  - {rname}: {short}" if short else f"  - {rname}")
        if relic_notes:
            relic_lines.append("")
            relic_lines.append("Synergy notes:")
            for note in relic_notes:
                relic_lines.append(f"  - {note}")
        relic_analysis = "\n".join(relic_lines)
    else:
        relic_analysis = "No relics collected."

    # --- next-run advice ----------------------------------------------------
    next_run_advice: list[str] = []

    if "no_scaling" in flags:
        next_run_advice.append(
            "Pick at least 2 Power cards or scaling engines by the Act 1 boss. "
            "Without scaling, your damage falls off in Act 2."
        )
    if "poor_defense_hint" in flags:
        next_run_advice.append(
            "Draft block cards early. A good rule: have at least 4 block cards "
            "by floor 8. Skipping block for more damage is a common trap."
        )
    if "thick_deck" in flags:
        next_run_advice.append(
            "Skip card rewards more often. A lean 15–20 card deck cycles key "
            "cards faster. Remove Strikes at shops."
        )
    if "bad_upgrade" in flags:
        next_run_advice.append(
            "Upgrade before resting. Ask yourself: 'Does this upgrade save me "
            "more HP over the run than this one heal of ~20 HP?' Usually, yes."
        )
    if "low_hp_before_elite" in flags:
        next_run_advice.append(
            "Never enter an elite below 50% HP. If you can't heal above that "
            "threshold, take a different path."
        )
    if "greedy_path" in flags:
        next_run_advice.append(
            "Plan your route from floor 0. Count elites, campfires, and shops. "
            "A balanced Act 1 has 1–2 elites and 2+ campfires."
        )
    if "died_to_elite" in flags:
        next_run_advice.append(
            "Prepare for elites: Gremlin Nob demands attacks (skills are dead "
            "draws), Lagavulin needs scaling, Sentries need AoE. Know which "
            "elite you might face and draft accordingly."
        )
    if avg_cost > 2.0:
        next_run_advice.append(
            "Lower your curve. Target an average card cost of 1.2–1.8. "
            "Pick 0-cost cards when offered and skip expensive cards unless "
            "they're run-defining."
        )
    if not next_run_advice:
        next_run_advice.append(
            "Review the final fight turn-by-turn. Sometimes the mistake is a "
            "single misplay — wrong target, wrong order, or a potion unused."
        )

    return {
        "summary": summary,
        "main_death_reason": main_death_reason,
        "key_mistakes": key_mistakes,
        "deck_analysis": deck_analysis,
        "route_analysis": route_analysis,
        "relic_analysis": relic_analysis,
        "next_run_advice": next_run_advice,
    }


# ===================================================================
# CLI entry point
# ===================================================================

def main() -> None:
    """CLI: load a run, build a review prompt, and print it.

    Usage::

        python backend/prompt_builder.py backend/mock_data/runs/mock-001-low-hp-elite.json
    """
    if len(sys.argv) < 2:
        print("Usage:  python backend/prompt_builder.py <path_to_run.json>")
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

    # 3. Load knowledge base
    kb = load_knowledge_base()

    # 4. Build prompt
    prompt = build_review_prompt(run_summary, run_data, kb)

    # 5. Output
    print(json.dumps(prompt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
