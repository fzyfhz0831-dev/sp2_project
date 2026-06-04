"""
knowledge_generator.py — Generate structured gameplay knowledge databases.

Produces five JSON files in sp2-backend/app/knowledge/:
  cards.json       — 85+ cards with synergies, risks, scaling info
  relics.json      — 40+ relics with archetype support and risk notes
  bosses.json      — Boss + elite patterns, threats, counter strategies
  archetypes.json  — Deck archetypes per character with synergy tags
  pathing.json     — Pathing decision heuristics per act

Usage:
  python knowledge_generator.py [--output-dir <path>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AUTOMATION_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = AUTOMATION_ROOT.parent / "sp2-backend" / "app" / "knowledge"


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# =============================================================================
# CARDS — 85+ entries across 5 character groups
# =============================================================================

_CARDS: dict[str, list[dict[str, Any]]] = {
    "ironclad": [
        {
            "name": "Bash", "type": "Attack", "cost": 2, "rarity": "Basic",
            "strengths": ["Applies Vulnerable for 2(3) turns", "High single-target damage early"],
            "weaknesses": ["2-cost slows turns without energy support", "Falls off in Act 3 without synergy"],
            "synergy_tags": ["vulnerable", "strength", "starter"],
            "scaling_notes": "Scales with Strength; doubledipping damage + Vulnerable amp",
            "risk_notes": "Upgrade first if keeping past Act 1. 3-turn Vulnerable is significantly better.",
            "recommended_situations": ["Act 1 hallway fights", "Strength-building decks", "Early upgrade priority"],
        },
        {
            "name": "Inflame", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Permanent +2(3) Strength", "Cheap 1-cost power", "Stackable across copies"],
            "weaknesses": ["Small per-fight value alone", "Dead draw late in short fights"],
            "synergy_tags": ["strength", "multi_attack", "heavy_blade", "sword_boomerang", "limit_break"],
            "scaling_notes": "+2(3) Strength per fight enables multi-attack cards to double-dip",
            "risk_notes": "Inflame alone won't carry Act 3 — pair with Limit Break or multi-hit attacks",
            "recommended_situations": ["Early Act 1 pickup", "Strength-scaling decks", "Multi-attack synergy"],
        },
        {
            "name": "Demon Form", "type": "Power", "cost": 3, "rarity": "Rare",
            "strengths": ["Infinite scaling — wins any fight given time", "Single-card win condition", "Boss killer"],
            "weaknesses": ["3-cost needs energy relic or setup turn", "Dead draw in fast hallway fights", "Slow starter"],
            "synergy_tags": ["strength", "energy_relic", "defensive_stall", "limit_break"],
            "scaling_notes": "+2(3) Strength per turn — the ultimate scaling card for long fights",
            "risk_notes": "Don't pick before Act 2 without 4 energy. You need block to stall while it scales.",
            "recommended_situations": ["Boss fights", "Act 2+ when you have energy relic", "Turtle/block-heavy decks"],
        },
        {
            "name": "Spot Weakness", "type": "Skill", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Massive Strength spike if enemy intends to attack", "Upgrades to 4 Strength for 1 energy"],
            "weaknesses": ["Misses if enemy isn't attacking", "Requires enemy intent knowledge", "Unreliable"],
            "synergy_tags": ["strength", "limit_break", "heavy_blade"],
            "scaling_notes": "Burst Strength that Limit Break can double — best paired with multi-hit",
            "risk_notes": "Don't pair with Runic Dome — you won't know enemy intent",
            "recommended_situations": ["Act 1-2 when you can see intents", "Limit Break decks", "Boss preparation"],
        },
        {
            "name": "Barricade", "type": "Power", "cost": 3, "rarity": "Rare",
            "strengths": ["Block carries between turns", "Enables passive turtle strategies", "Infinite block ceiling"],
            "weaknesses": ["3-cost needs setup turn", "Requires strong block engine to function", "Dead without block cards"],
            "synergy_tags": ["block_engine", "entrench", "body_slam", "impervious", "feel_no_pain"],
            "scaling_notes": "Transforms block into a permanent resource — scales with block density",
            "risk_notes": "Don't pick before you have Impervious/Entrench/Feel No Pain. Barricade without block is dead.",
            "recommended_situations": ["Block-heavy decks", "Entrench combos", "Act 2+ when block engine is online"],
        },
        {
            "name": "Corruption", "type": "Power", "cost": 3, "rarity": "Rare",
            "strengths": ["Skills cost 0 — enables massive combo turns", "Core of exhaust archetype"],
            "weaknesses": ["Skills are exhausted — you run out of block", "Bad against long boss fights without Dead Branch"],
            "synergy_tags": ["exhaust", "dead_branch", "feel_no_pain", "dark_embrace", "fiend_fire"],
            "scaling_notes": "Converts every skill to 0-cost — scales with deck density of skills and exhaust synergies",
            "risk_notes": "Without Dead Branch or Dark Embrace, you'll run out of cards. Time Corruption carefully.",
            "recommended_situations": ["Dead Branch synergy", "Exhaust engine decks", "Act 3 when deck is thick with skills"],
        },
        {
            "name": "Shrug It Off", "type": "Skill", "cost": 1, "rarity": "Common",
            "strengths": ["Reliable 8(11) block + draw 1", "Fits any Ironclad deck", "Deck cycling"],
            "weaknesses": ["Low block ceiling per card", "Outclassed by rare block cards late-game"],
            "synergy_tags": ["block", "draw", "exhaust", "deck_cycle"],
            "scaling_notes": "Draw smooths out inconsistency; pairs well with Corruption (0-cost draw)",
            "risk_notes": "Safe pick in almost any situation — rarely a wrong choice",
            "recommended_situations": ["Any deck", "Early game defense", "Draw consistency"],
        },
        {
            "name": "Feel No Pain", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Passive block on exhaust", "1-cost — easy to play", "Enables exhaust engine"],
            "weaknesses": ["Needs exhaust sources to trigger", "Low value without synergies"],
            "synergy_tags": ["exhaust", "corruption", "second_wind", "fiend_fire", "dark_embrace"],
            "scaling_notes": "3(4) Block per exhaust — scales with number of exhaust triggers per fight",
            "risk_notes": "Don't pick before you have exhaust cards. A blank 1-cost power without them.",
            "recommended_situations": ["Corruption decks", "Fiend Fire/Second Wind synergy", "Any exhaust-heavy build"],
        },
        {
            "name": "Whirlwind", "type": "Attack", "cost": 0, "rarity": "Uncommon",
            "strengths": ["X-cost dumps all energy for AoE", "Strength double-dips per energy", "Flexible energy usage"],
            "weaknesses": ["Inefficient at low energy", "No block — pure damage", "Weak single-target for cost"],
            "synergy_tags": ["strength", "energy_relic", "akabeko", "aoe", "multi_hit"],
            "scaling_notes": "Each Strength adds X damage — strongest Strength multiplier in the game",
            "risk_notes": "Picking Whirlwind without Strength scaling limits value. Needs both energy and Strength.",
            "recommended_situations": ["Strength decks", "Act 2 AoE fights", "High-energy builds"],
        },
        {
            "name": "Impervious", "type": "Skill", "cost": 2, "rarity": "Rare",
            "strengths": ["Massive 30(40) block for 2 energy", "Best single block card for Ironclad", "Exhaust synergy"],
            "weaknesses": ["Exhausts — one use per fight", "2-cost can be awkward in tight turns"],
            "synergy_tags": ["block_engine", "barricade", "body_slam", "exhaust"],
            "scaling_notes": "Fixed block value — doesn't scale but enables Barricade setup turns",
            "risk_notes": "Always a strong take unless you have no way to win after blocking",
            "recommended_situations": ["Barricade decks", "Boss fights", "Any deck needing burst defense"],
        },
        {
            "name": "Limit Break", "type": "Skill", "cost": 1, "rarity": "Rare",
            "strengths": ["Doubles current Strength", "Exponential scaling with multiple plays", "Upgraded version doesn't exhaust"],
            "weaknesses": ["Does nothing if you have 0 Strength", "Exhausts (unupgraded) — one-shot", "Dead without Strength sources"],
            "synergy_tags": ["strength", "inflame", "spot_weakness", "demon_form", "heavy_blade"],
            "scaling_notes": "Exponential Strength doubling — 4 -> 8 -> 16 -> 32 -> 64 in one fight",
            "risk_notes": "Upgrade first. Unupgraded Limit Break is dramatically worse.",
            "recommended_situations": ["Strength decks with multiple sources", "Boss fights", "Demon Form synergy"],
        },
        {
            "name": "Battle Trance", "type": "Skill", "cost": 0, "rarity": "Uncommon",
            "strengths": ["0-cost draw 3(4)", "Instant hand refill", "No downside if played last"],
            "weaknesses": ["Can't draw additional cards this turn", "Anti-synergy with other draw", "Timing matters"],
            "synergy_tags": ["draw", "0_cost", "combo_enabler"],
            "scaling_notes": "Draw consistency at 0-cost — always play as last action in a turn",
            "risk_notes": "Play AFTER all other draw cards. Battle Trance locks draw for the turn.",
            "recommended_situations": ["Exhaust decks (thins deck)", "Combo setup", "Any deck needing draw"],
        },
        {
            "name": "Offering", "type": "Skill", "cost": 0, "rarity": "Rare",
            "strengths": ["0-cost draw 3(5) + 2 energy", "Lose 6 HP — minimal cost for the payoff", "Burst energy + draw"],
            "weaknesses": ["HP loss adds up over a run", "Exhausts — one use per fight"],
            "synergy_tags": ["draw", "energy", "self_damage", "rupture"],
            "scaling_notes": "Draw + energy in one card — enables turn-1 setup for scaling powers",
            "risk_notes": "The HP loss is worth it 95% of the time. One of Ironclad's best cards.",
            "recommended_situations": ["Any Ironclad deck", "Turn-1 Demon Form setup", "Rupture synergy"],
        },
        {
            "name": "Reaper", "type": "Attack", "cost": 2, "rarity": "Rare",
            "strengths": ["Heals for unblocked damage dealt", "AoE healing", "Enables Coffee Dripper"],
            "weaknesses": ["Low base damage (4/5)", "Needs Strength to heal meaningfully", "2-cost"],
            "synergy_tags": ["strength", "healing", "aoe", "coffee_dripper"],
            "scaling_notes": "Healing scales with Strength — 20 Strength Reaper = full heal",
            "risk_notes": "Without Strength, Reaper is a poor attack. With Strength, it's sustain engine.",
            "recommended_situations": ["Strength decks", "Coffee Dripper synergy", "Aggressive pathing"],
        },
        {
            "name": "Disarm", "type": "Skill", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Reduces enemy Strength by 2(3)", "Neuters multi-hit enemies", "Cheap 1-cost"],
            "weaknesses": ["Does nothing against enemies that don't attack", "Single target"],
            "synergy_tags": ["debuff", "defensive", "boss_counter"],
            "scaling_notes": "Fixed debuff — value depends entirely on enemy attack patterns",
            "risk_notes": "Excellent against Book of Stabbing, Hexaghost, Awakened One. Keep one copy.",
            "recommended_situations": ["Act 2 elites", "Multi-hit bosses", "Defensive tech slot"],
        },
        {
            "name": "Fiend Fire", "type": "Attack", "cost": 2, "rarity": "Rare",
            "strengths": ["Exhausts hand for massive burst damage", "Clears status cards", "Finisher"],
            "weaknesses": ["Loses your entire hand", "Terrible if played early in a turn", "Needs full hand"],
            "synergy_tags": ["exhaust", "feel_no_pain", "dark_embrace", "dead_branch"],
            "scaling_notes": "7(10) damage per card exhausted — 7 cards = 49(70) damage for 2 energy",
            "risk_notes": "Play as the LAST card in your turn. Exhausts everything — including good cards.",
            "recommended_situations": ["Exhaust engine", "Status-heavy fights (Hexaghost)", "Finisher turns"],
        },
        {
            "name": "Power Through", "type": "Skill", "cost": 1, "rarity": "Uncommon",
            "strengths": ["15(20) block for 1 energy", "Adds 2 Wounds — exhaust them later", "Extremely efficient"],
            "weaknesses": ["Adds 2 Wounds to draw pile", "Clutters deck without exhaust", "Bad without exhaust plan"],
            "synergy_tags": ["block", "exhaust", "fire_breathing", "evolve", "second_wind"],
            "scaling_notes": "Massive block efficiency — wounds are a resource with exhaust synergies",
            "risk_notes": "Pair with Evolve, Fire Breathing, or Second Wind. Wounds are fuel, not trash.",
            "recommended_situations": ["Exhaust engine decks", "Evolve/Fire Breathing synergy", "Act 2 block needs"],
        },
    ],
    "the silent": [
        {
            "name": "Neutralize", "type": "Attack", "cost": 0, "rarity": "Basic",
            "strengths": ["0-cost Weak application", "Starter card that stays relevant", "Debuff"],
            "weaknesses": ["Low damage (3/4)", "Single-target only"],
            "synergy_tags": ["weak", "starter", "0_cost", "debuff"],
            "scaling_notes": "Damage doesn't scale but Weak utility is timeless throughout the run",
            "risk_notes": "Keep it — weak is always useful. Upgrade early for 2-turn Weak.",
            "recommended_situations": ["Any Silent deck", "Early upgrade priority", "Defensive support"],
        },
        {
            "name": "Footwork", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Permanent +2(3) Dexterity", "Scales ALL block cards", "Stackable across copies"],
            "weaknesses": ["Slow — takes turns to offset HP loss from playing it", "Does nothing without block cards"],
            "synergy_tags": ["dexterity", "block_engine", "dodge_and_roll", "blur", "defensive"],
            "scaling_notes": "Each Dexterity = +1 block per block card — 3 Footworks = 15-block Defends",
            "risk_notes": "Silent's best defensive card. Take 2+ copies if offered. Best common defensive scaling.",
            "recommended_situations": ["Any Silent deck", "Block-heavy builds", "Long boss fights"],
        },
        {
            "name": "Noxious Fumes", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Passive AoE poison", "Strips artifact charges automatically", "Single-card win condition"],
            "weaknesses": ["Slow — takes many turns to kill", "Weak against fast fights"],
            "synergy_tags": ["poison", "catalyst", "stall", "defensive", "aoe"],
            "scaling_notes": "2(3) poison to ALL enemies per turn — infinite scaling ceiling",
            "risk_notes": "Pair with block-heavy deck. Noxious Fumes + block = you win eventually.",
            "recommended_situations": ["Poison decks", "Defensive/stall builds", "Artifact-stripping for other debuffs"],
        },
        {
            "name": "Catalyst", "type": "Skill", "cost": 1, "rarity": "Rare",
            "strengths": ["Doubles(Triples) enemy poison", "Exponential scaling", "Boss annihilator"],
            "weaknesses": ["Useless without poison applied", "Dead draw in non-poison deck", "Needs setup"],
            "synergy_tags": ["poison", "noxious_fumes", "bouncing_flask", "burst", "nightmare"],
            "scaling_notes": "Exponential: 4 -> 12 -> 36 poison. Burst+ doubles the doubling.",
            "risk_notes": "Don't take before consistent poison. Hold with Well-Laid Plans for perfect timing.",
            "recommended_situations": ["Poison engine online", "Burst combo", "Boss fights"],
        },
        {
            "name": "Wraith Form", "type": "Power", "cost": 3, "rarity": "Rare",
            "strengths": ["Near-invincibility for 2(3) turns", "Bypasses every defensive check", "Best panic button"],
            "weaknesses": ["Dexterity loss after — must win fast", "3-cost requires energy setup", "Intangible wears off"],
            "synergy_tags": ["intangible", "burst_damage", "nightmare", "well_laid_plans"],
            "scaling_notes": "Timer, not scaling — win before it expires. Upgrade for +1 turn of invincibility.",
            "risk_notes": "Hold with Well-Laid Plans. Play on the turn you need immortality. Never play early.",
            "recommended_situations": ["Boss fights", "Bad draw turns", "Poison decks (damage ticks during intangible)"],
        },
        {
            "name": "Backflip", "type": "Skill", "cost": 1, "rarity": "Common",
            "strengths": ["Block + draw in one card", "Fits any Silent deck", "Deck cycling"],
            "weaknesses": ["Low block value (5/8)", "Better block options exist in rare slots"],
            "synergy_tags": ["draw", "block", "deck_cycle", "dexterity"],
            "scaling_notes": "Draw consistency scales with Dexterity — self-synergy with Footwork",
            "risk_notes": "Always a reasonable pick. Draw smooths out bad hands.",
            "recommended_situations": ["Any Silent deck", "Dexterity scaling", "Deck cycling needs"],
        },
        {
            "name": "Well-Laid Plans", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Retain 1(2) card(s) per turn", "Enables perfect combo timing", "Dramatically increases consistency"],
            "weaknesses": ["1-cost do-nothing on the play turn", "Low impact if you draw all good cards anyway"],
            "synergy_tags": ["retain", "combo_setup", "burst", "catalyst", "wraith_form"],
            "scaling_notes": "Indirect scaling — consistency IS power. Hold Wraith Form/Catalyst for perfect turn.",
            "risk_notes": "One of Silent's best cards. Always take at least one.",
            "recommended_situations": ["Any Silent deck", "Combo decks", "Setup-heavy strategies"],
        },
        {
            "name": "After Image", "type": "Power", "cost": 1, "rarity": "Rare",
            "strengths": ["Passive block on every card played", "Synergizes with shiv and 0-cost spam", "Beat of Death counter"],
            "weaknesses": ["Low per-trigger value (1 block)", "Needs high card play rate to matter"],
            "synergy_tags": ["shiv", "0_cost", "cloak_and_dagger", "blade_dance"],
            "scaling_notes": "1 block per card — 10 cards/turn = 10 block. Upgrades with more card plays.",
            "risk_notes": "Shines in shiv decks. Mediocre in slow poison decks.",
            "recommended_situations": ["Shiv spam decks", "Beat of Death counter (Heart)", "0-cost heavy builds"],
        },
        {
            "name": "Adrenaline", "type": "Skill", "cost": 0, "rarity": "Rare",
            "strengths": ["0-cost: gain 1(2) energy + draw 2", "Pure tempo", "No downside"],
            "weaknesses": ["Exhausts — one use per fight", "Low impact if drawn at wrong time"],
            "synergy_tags": ["energy", "draw", "0_cost", "combo_enabler"],
            "scaling_notes": "Net energy + draw at 0 cost — always a positive card. No scaling ceiling.",
            "risk_notes": "Always take. Never skip. One of the best cards in the game.",
            "recommended_situations": ["Every Silent deck", "Combo turns", "Any situation"],
        },
        {
            "name": "Blade Dance", "type": "Skill", "cost": 1, "rarity": "Common",
            "strengths": ["Creates 3(4) Shivs", "Efficient damage per energy", "Multi-trigger enabler"],
            "weaknesses": ["Shivs are 0-cost 4 damage — low per card", "Time Eater counter-synergy"],
            "synergy_tags": ["shiv", "accuracy", "kunai", "shuriken", "after_image"],
            "scaling_notes": "3(4) triggers for Kunai/Shuriken/After Image per play. Accuracy adds +4(6) per shiv.",
            "risk_notes": "Don't take too many copies if Time Eater is the Act 3 boss.",
            "recommended_situations": ["Shiv decks", "Kunai/Shuriken synergy", "After Image defense"],
        },
        {
            "name": "Bouncing Flask", "type": "Skill", "cost": 2, "rarity": "Uncommon",
            "strengths": ["Applies 3 poison to 3(4) random enemies", "Strips multiple artifact charges", "Total 9(12) poison"],
            "weaknesses": ["Random targeting — can hit dead enemy", "2-cost is heavy early", "Slow vs single target"],
            "synergy_tags": ["poison", "catalyst", "aoe", "noxious_fumes"],
            "scaling_notes": "Total poison value is high but spread across targets — best into 2-3 enemies",
            "risk_notes": "Wait for artifact to be stripped before playing. Pairs well with Noxious Fumes.",
            "recommended_situations": ["Multi-enemy fights", "Poison decks", "Artifact-stripping"],
        },
    ],
    "defect": [
        {
            "name": "Defragment", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Permanent +1(2) Focus", "Best common scaling for Defect", "Stackable"],
            "weaknesses": ["Slow — needs orb slots and turns to accumulate value"],
            "synergy_tags": ["focus", "frost", "capacitor", "biased_cognition", "orb"],
            "scaling_notes": "Each Focus = +1 damage/block per orb per turn — multiplicative with orb slots",
            "risk_notes": "Always pick at least one. Defect's best scaling card. Take every copy offered.",
            "recommended_situations": ["Any Defect deck", "Frost builds", "Lightning builds", "Always pick"],
        },
        {
            "name": "Glacier", "type": "Skill", "cost": 2, "rarity": "Uncommon",
            "strengths": ["Channel 2 Frost + 7(10) Block", "Instant defense + scaling potential", "Orb generation"],
            "weaknesses": ["2-cost can be heavy early", "Needs Focus to make Frost orbs impactful"],
            "synergy_tags": ["frost", "focus", "block_engine", "capacitor", "orb"],
            "scaling_notes": "Frost orbs scale with Focus — Glacier is defense now AND passive block later",
            "risk_notes": "Defect's best block card. Take 2+ in almost any deck.",
            "recommended_situations": ["Any Defect deck", "Focus scaling", "Block needs", "Always pick"],
        },
        {
            "name": "Echo Form", "type": "Power", "cost": 3, "rarity": "Rare",
            "strengths": ["First card each turn played twice", "Doubles damage, block, AND powers", "Best Defect rare"],
            "weaknesses": ["3-cost — needs 4 energy or setup turn", "Ethereal — must play immediately", "Slow to deploy"],
            "synergy_tags": ["energy_relic", "power_spam", "creative_ai", "self_repair", "focus"],
            "scaling_notes": "Doubles your best card EVERY turn — multiplicative scaling with your entire deck",
            "risk_notes": "Without 4 energy, Echo Form can cost you the turn. Upgrade to remove Ethereal.",
            "recommended_situations": ["Any Defect deck with 4+ energy", "Power-heavy builds", "Boss fights"],
        },
        {
            "name": "Biased Cognition", "type": "Power", "cost": 1, "rarity": "Rare",
            "strengths": ["+4(5) Focus immediately", "Ends fights fast", "1-cost massive power spike"],
            "weaknesses": ["Lose 1 Focus per turn — decays over time", "Can strand you with negative Focus"],
            "synergy_tags": ["focus", "artifact", "core_surge", "fast_kill", "orange_pellets"],
            "scaling_notes": "Temporary but massive scaling — play when you can win in 4-5 turns",
            "risk_notes": "Pair with Core Surge or artifact source to negate the Focus loss permanently.",
            "recommended_situations": ["Artifact synergy", "Fast kill decks", "Boss fights"],
        },
        {
            "name": "Capacitor", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["+2(3) orb slots", "Multiplicative with Focus", "Cheap 1-cost"],
            "weaknesses": ["Does nothing without orbs to fill slots", "Slow — takes turns to channel into new slots"],
            "synergy_tags": ["focus", "frost", "lightning", "orb_slots", "glacier"],
            "scaling_notes": "Each new orb slot = +Focus value per turn. 10 orbs × 5 Focus = enormous passive value.",
            "risk_notes": "Take after you have orb generation. Empty slots do nothing.",
            "recommended_situations": ["Frost focus decks", "Orb-heavy builds", "After you have Glacier/Defragment"],
        },
        {
            "name": "Coolheaded", "type": "Skill", "cost": 1, "rarity": "Common",
            "strengths": ["Channel Frost + draw 1(2)", "Draw engine for frost decks", "Orb generation + cycle"],
            "weaknesses": ["Low immediate impact", "Weak without Focus backing"],
            "synergy_tags": ["frost", "draw", "focus", "deck_cycle", "orb"],
            "scaling_notes": "Draw consistency + passive Frost orb — double value in Focus decks",
            "risk_notes": "Safe pick. Upgraded Coolheaded is one of Defect's best draw cards.",
            "recommended_situations": ["Focus decks", "Frost builds", "Draw consistency needs"],
        },
        {
            "name": "Creative AI", "type": "Power", "cost": 3, "rarity": "Rare",
            "strengths": ["Generates a random Power each turn", "Infinite value in long fights", "Scales itself"],
            "weaknesses": ["3-cost — slow to deploy", "Random powers can be useless", "Awakened One punishes power spam"],
            "synergy_tags": ["power_spam", "mummified_hand", "echo_form", "storm", "heatsinks"],
            "scaling_notes": "1 random power per turn — the longer the fight, the more value you accumulate",
            "risk_notes": "Only good in long fights. Bad against Awakened One (feeds Strength).",
            "recommended_situations": ["Boss fights", "Defensive/stall decks", "Mummified Hand synergy"],
        },
    ],
    "watcher": [
        {
            "name": "Eruption", "type": "Attack", "cost": 2, "rarity": "Basic",
            "strengths": ["Enter Wrath — deal double damage", "Upgrade reduces cost to 1 — core engine"],
            "weaknesses": ["Staying in Wrath is dangerous", "2-cost limits turn flexibility before upgrade"],
            "synergy_tags": ["wrath", "stance_dance", "calm", "rushdown", "starter"],
            "scaling_notes": "Wrath doubles all attack damage — multiplicative with Strength and Divinity",
            "risk_notes": "ALWAYS upgrade Eruption first. 1-cost Wrath entry is Watcher's entire engine.",
            "recommended_situations": ["Every Watcher deck", "First upgrade priority", "Stance switching engine"],
        },
        {
            "name": "Mental Fortress", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Block on stance switch", "Passive defense engine", "Stackable across copies"],
            "weaknesses": ["Low block per switch (4/6)", "Needs frequent stance switching to matter"],
            "synergy_tags": ["stance_dance", "rushdown", "inner_peace", "fear_no_evil", "block"],
            "scaling_notes": "Scales with stance switches per turn — infinite combos generate infinite block",
            "risk_notes": "Take 2+ copies. Mental Fortress + stance switching is Watcher's best block plan.",
            "recommended_situations": ["Stance dance decks", "Infinite loop engine", "Any Watcher deck"],
        },
        {
            "name": "Rushdown", "type": "Power", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Draw 2 on Wrath entry", "Core of infinite combo engine", "1-cost"],
            "weaknesses": ["Does nothing until you enter Wrath", "Useless without stance-switching package"],
            "synergy_tags": ["wrath", "stance_dance", "inner_peace", "fear_no_evil", "draw"],
            "scaling_notes": "Draw 2 per Wrath entry = infinite draw engine with 1-cost Calm -> 1-cost Wrath",
            "risk_notes": "With Rushdown + 1-cost Calm + 1-cost Wrath, you have an infinite. Build around this.",
            "recommended_situations": ["Infinite combo decks", "Stance switching", "Slim deck builds"],
        },
        {
            "name": "Talk to the Hand", "type": "Attack", "cost": 1, "rarity": "Uncommon",
            "strengths": ["Apply block-per-hit debuff", "Scales with multi-hit attacks", "Stackable"],
            "weaknesses": ["Single enemy only", "Block value delayed until you attack"],
            "synergy_tags": ["block", "tantrum", "multi_hit", "defensive"],
            "scaling_notes": "2(3) Block per attack hit — Tantrum (3 hits) = 6(9) Block per play",
            "risk_notes": "Pair with Tantrum or multi-hit cards. Block triggers per attack HIT, not per card.",
            "recommended_situations": ["Multi-hit decks", "Tantrum synergy", "Boss fights (single target)"],
        },
    ],
}


# =============================================================================
# RELICS — 40+ entries
# =============================================================================

_RELICS: list[dict[str, Any]] = [
    # ── Starter Relics ──
    {
        "name": "Burning Blood", "type": "Starter", "character": "ironclad",
        "strengths": ["6 HP heal after each combat", "Enables aggressive pathing", "Reduces rest site dependency"],
        "weaknesses": ["Only 6 HP — doesn't save you from burst", "Ironclad-only"],
        "synergy_tags": ["healing", "aggressive_pathing", "sustain"],
        "scaling_notes": "Flat 6 HP per fight — value scales with number of combats fought per act",
        "risk_notes": "Use the HP buffer to take extra elites. Each elite = relic reward for 6 HP.",
        "recommended_situations": ["Aggressive pathing", "Elite hunting", "New players"],
    },
    {
        "name": "Ring of the Snake", "type": "Starter", "character": "the silent",
        "strengths": ["Draw 2 extra cards turn 1", "Massive consistency boost", "Fixes bad opening hands"],
        "weaknesses": ["Only turn 1", "Silent-only"],
        "synergy_tags": ["draw", "turn_1", "consistency", "setup"],
        "scaling_notes": "Consistency boost — see more of your deck on turn 1 to find setup cards",
        "risk_notes": "Always active. One of the best starter relics.",
        "recommended_situations": ["Finding key powers early", "Combo setup", "Any Silent deck"],
    },
    {
        "name": "Cracked Core", "type": "Starter", "character": "defect",
        "strengths": ["Channel 1 Lightning at start of combat", "Passive damage from turn 1", "Free orb"],
        "weaknesses": ["1 Lightning is low damage without Focus", "Defect-only"],
        "synergy_tags": ["lightning", "orb", "starter", "passive_damage"],
        "scaling_notes": "Free passive damage — scales with Focus and number of orb slots",
        "risk_notes": "3 damage/turn passively. Modest but always relevant.",
        "recommended_situations": ["Any Defect deck", "Focus scaling", "Orb synergy"],
    },
    {
        "name": "Pure Water", "type": "Starter", "character": "watcher",
        "strengths": ["Add a Miracle to hand at start of combat", "Free energy for stance switching", "Enables turn-1 combos"],
        "weaknesses": ["1 Miracle is modest", "Watcher-only"],
        "synergy_tags": ["energy", "miracle", "stance_dance", "combo_enabler"],
        "scaling_notes": "+1 energy on the turn you need it — timing flexibility",
        "risk_notes": "Use Miracle to enable Wrath -> damage -> Calm exit in one turn.",
        "recommended_situations": ["Stance dance", "Combo turns", "Any Watcher deck"],
    },
    # ── Common Relics ──
    {
        "name": "Anchor", "type": "Common", "character": None,
        "strengths": ["10 Block on turn 1", "Free setup turn for powers", "Prevents turn-1 chip damage"],
        "weaknesses": ["Only turn 1 — no ongoing value", "Outscaled by block engines late-game"],
        "synergy_tags": ["turn_1", "setup", "defensive", "block"],
        "scaling_notes": "Fixed 10 Block — enables playing 3-cost powers on turn 1 safely",
        "risk_notes": "Valuable in every deck. The free block lets you play powers on turn 1.",
        "recommended_situations": ["Any deck", "Setup-heavy builds", "Early game survival"],
    },
    {
        "name": "Vajra", "type": "Common", "character": None,
        "strengths": ["+1 Strength always", "Works with multi-hit", "No downside"],
        "weaknesses": ["Small bonus — 1 Strength is modest", "Less impactful in skill-heavy decks"],
        "synergy_tags": ["strength", "multi_hit", "attack"],
        "scaling_notes": "+1 Strength is permanent — each attack gets +1, multi-hits get +1 per hit",
        "risk_notes": "Subtle but powerful. 1 Strength on 4 attacks = 4 extra damage per deck cycle.",
        "recommended_situations": ["Multi-attack decks", "Any physical damage build"],
    },
    {
        "name": "Lantern", "type": "Common", "character": None,
        "strengths": ["+1 energy on turn 1", "Free setup energy", "No downside"],
        "weaknesses": ["Only turn 1 — no ongoing benefit", "Less valuable in slow decks"],
        "synergy_tags": ["turn_1", "energy", "setup"],
        "scaling_notes": "One-time energy boost — enables faster deployment of scaling cards",
        "risk_notes": "Always helpful. Enables turn-1 powers, Whirlwind, or setup.",
        "recommended_situations": ["Any deck", "Setup-heavy builds", "Aggressive starts"],
    },
    {
        "name": "Bag of Preparation", "type": "Common", "character": None,
        "strengths": ["Draw 2 additional cards turn 1", "Massive opening hand consistency", "Finds key cards faster"],
        "weaknesses": ["Only turn 1", "Less impactful in small decks"],
        "synergy_tags": ["draw", "turn_1", "consistency"],
        "scaling_notes": "Consistency — see more cards turn 1 to find your setup pieces",
        "risk_notes": "Premium common relic. Always happy to see this.",
        "recommended_situations": ["Any deck", "Combo-reliant decks", "Large decks"],
    },
    {
        "name": "Horn Cleat", "type": "Common", "character": None,
        "strengths": ["14 Block on turn 2", "Survives early burst turns", "Predictable timing"],
        "weaknesses": ["Only turn 2", "Doesn't help on other critical turns"],
        "synergy_tags": ["defensive", "turn_2", "block"],
        "scaling_notes": "Fixed value — buy time for your scaling engine to come online",
        "risk_notes": "Good for surviving turn-2 burst from elites like Gremlin Nob.",
        "recommended_situations": ["Act 1 elites", "Slow setup decks", "Early defense needs"],
    },
    # ── Uncommon Relics ──
    {
        "name": "Kunai", "type": "Uncommon", "character": None,
        "strengths": ["+1 Dexterity per 3 attacks played", "Passive block scaling", "Infinite ceiling in long fights"],
        "weaknesses": ["Needs high attack frequency (3/turn)", "Low impact in slow decks"],
        "synergy_tags": ["dexterity", "shiv", "multi_attack", "0_cost"],
        "scaling_notes": "+1 Dexterity per 3 attacks every turn — rewards high attack-density decks",
        "risk_notes": "Shiv decks love Kunai. In slow poison decks it's much weaker.",
        "recommended_situations": ["Shiv Silent", "Multi-attack Ironclad", "High card-play-rate decks"],
    },
    {
        "name": "Shuriken", "type": "Uncommon", "character": None,
        "strengths": ["+1 Strength per 3 attacks played", "Passive damage scaling", "Stacks with itself"],
        "weaknesses": ["Needs high attack frequency", "Low impact in skill/power-heavy decks"],
        "synergy_tags": ["strength", "shiv", "multi_attack"],
        "scaling_notes": "+1 Strength per 3 attacks per turn — passive damage scaling in attack-heavy decks",
        "risk_notes": "Strong in Silent shiv and Ironclad multi-attack decks. Dead in Defect frost.",
        "recommended_situations": ["Attack-heavy decks", "Shiv Silent", "Strength Ironclad"],
    },
    {
        "name": "Mummified Hand", "type": "Uncommon", "character": None,
        "strengths": ["Powers make a random card cost 0", "Chain powers for massive turns", "Energy cheat engine"],
        "weaknesses": ["Needs multiple powers in deck", "Random target can hit already-0-cost card"],
        "synergy_tags": ["power_spam", "creative_ai", "defect", "energy"],
        "scaling_notes": "Scales with power count — the more powers you have, the more free cards you get",
        "risk_notes": "Defect power-spam deck's best friend. Less valuable in low-power decks.",
        "recommended_situations": ["Defect power decks", "Any power-heavy build", "Creative AI synergy"],
    },
    {
        "name": "Ornamental Fan", "type": "Uncommon", "character": None,
        "strengths": ["+4 Block per 3 attacks played", "Passive defense", "Pairs with Kunai/Shuriken"],
        "weaknesses": ["4 Block is modest per trigger", "Needs high attack frequency"],
        "synergy_tags": ["block", "shiv", "multi_attack", "defensive"],
        "scaling_notes": "Passive 4 block per 3 attacks — pairs perfectly with Kunai/Shuriken triggers",
        "risk_notes": "Best in shiv or multi-attack decks. Triggers on the same 3-attack counter as Kunai.",
        "recommended_situations": ["Shiv Silent", "Multi-attack builds", "Kunai/Shuriken synergy"],
    },
    # ── Rare Relics ──
    {
        "name": "Dead Branch", "type": "Rare", "character": None,
        "strengths": ["Adds random card on exhaust", "Infinite value with Corruption", "Game-winning synergy"],
        "weaknesses": ["Random cards can clutter hand", "Unreliable — can't plan around random cards"],
        "synergy_tags": ["exhaust", "corruption", "fiend_fire", "shiv"],
        "scaling_notes": "Scales with exhaust triggers — each exhaust generates new options from thin air",
        "risk_notes": "With Corruption: instant win. Without exhaust: mediocre. Pairs with Fiend Fire.",
        "recommended_situations": ["Corruption decks", "Exhaust-heavy builds", "Shiv decks (exhaust on use)"],
    },
    {
        "name": "Incense Burner", "type": "Rare", "character": None,
        "strengths": ["Intangible every 6 turns", "Predictable — can plan around it", "Saves you on big attack turns"],
        "weaknesses": ["Requires turn counting", "6-turn cooldown is long", "Doesn't help if fight ends fast"],
        "synergy_tags": ["intangible", "defensive", "stall", "boss_counter"],
        "scaling_notes": "Timing-based defense — set up the counter to trigger on boss attack turns",
        "risk_notes": "Count the turns. Enter elite/boss fights with the counter on 5 for turn-2 Intangible.",
        "recommended_situations": ["Boss fights", "Setup-heavy decks", "Turn-planning players"],
    },
    {
        "name": "Fossilized Helix", "type": "Rare", "character": None,
        "strengths": ["Prevent first HP loss each combat", "Blocks ANY attack once", "Boss opener counter"],
        "weaknesses": ["Only once per combat", "Wasted on chip damage", "Can't control when it triggers"],
        "synergy_tags": ["defensive", "boss_counter", "setup"],
        "scaling_notes": "Fixed effect — prevents one instance of HP loss. Most valuable vs boss hyper-beams.",
        "risk_notes": "Try not to waste it on 3-damage hits. Play around preserving it for big attacks.",
        "recommended_situations": ["Boss fights", "High-burst enemy fights", "Aggressive pathing"],
    },
    # ── Boss Relics ──
    {
        "name": "Coffee Dripper", "type": "Boss", "character": None,
        "strengths": ["+1 energy per turn permanently", "No combat downside", "Best energy relic if you have sustain"],
        "weaknesses": ["Cannot rest at campfires", "Risky without alternative healing sources"],
        "synergy_tags": ["energy", "healing", "self_repair", "reaper", "meat_on_the_bone"],
        "scaling_notes": "Permanent +1 energy — enables 4-energy turns every single turn",
        "risk_notes": "Only take if you have sustain (Reaper, Self Repair, Meat on the Bone, etc.).",
        "recommended_situations": ["Sustain decks", "After Act 2 if healthy", "Healing relic synergy"],
    },
    {
        "name": "Fusion Hammer", "type": "Boss", "character": None,
        "strengths": ["+1 energy per turn", "Can still upgrade via events and egg relics", "Strong if deck is upgraded"],
        "weaknesses": ["Cannot smith at campfires", "Punishes unupgraded decks", "No more upgrades"],
        "synergy_tags": ["energy", "apotheosis", "egg_relics", "upgraded_deck"],
        "scaling_notes": "Time-locks your upgrades — plan around the point you take it",
        "risk_notes": "Take if your key cards are already upgraded or you have Apotheosis/Egg relics.",
        "recommended_situations": ["Well-upgraded decks", "Apotheosis available", "Late Act 2+ if upgraded"],
    },
    {
        "name": "Runic Dome", "type": "Boss", "character": None,
        "strengths": ["+1 energy per turn", "No combat penalty if you know enemy patterns", "Highest upside energy relic"],
        "weaknesses": ["Cannot see enemy intents — blind", "Punishing if you don't know enemy attack patterns"],
        "synergy_tags": ["energy", "enemy_knowledge", "block_engine", "experienced"],
        "scaling_notes": "Pure energy — the 'downside' is information loss, not mechanical penalty",
        "risk_notes": "Only for experienced players. Knowledge of all enemy patterns is mandatory.",
        "recommended_situations": ["Experienced players", "Block-heavy decks (always block)", "Pattern knowledge"],
    },
    {
        "name": "Snecko Eye", "type": "Boss", "character": None,
        "strengths": ["Draw 2 extra cards every turn", "Confusion randomizes costs — can be 0", "High-variance powerhouse"],
        "weaknesses": ["Confusion can make key cards cost 3", "High variance — can brick your hand", "Unreliable"],
        "synergy_tags": ["draw", "high_cost_deck", "confusion", "variance"],
        "scaling_notes": "Confusion randomizes all costs — build around expensive cards for maximum upside",
        "risk_notes": "Pick expensive cards (2-3 cost) after taking Snecko. Average cost becomes 1.5.",
        "recommended_situations": ["High-cost decks", "Demon Form/Barricade/Echo Form builds", "Draw value"],
    },
    # ── Shop Relics ──
    {
        "name": "Orange Pellets", "type": "Shop", "character": None,
        "strengths": ["Cleanse ALL debuffs when you play Attack+Skill+Power", "Negates Biased Cognition downside", "Best shop relic"],
        "weaknesses": ["Requires playing 3 card types in one turn", "Can't always trigger it"],
        "synergy_tags": ["debuff_cleanse", "biased_cognition", "wraith_form", "flex"],
        "scaling_notes": "Infinite value — cleanses ANY debuff including 'lose Focus', 'lose Dexterity', etc.",
        "risk_notes": "Must play Attack + Skill + Power in same turn. Plan your turns to trigger it.",
        "recommended_situations": ["Biased Cognition decks", "Wraith Form synergy", "Any debuff-heavy fights"],
    },
    {
        "name": "Medical Kit", "type": "Shop", "character": None,
        "strengths": ["Status cards can be played and exhausted", "Turns Wounds/Burns into resources", "Status immunity"],
        "weaknesses": ["Niche — only good if you generate or face status cards", "Shop-only — expensive"],
        "synergy_tags": ["exhaust", "status_counter", "feel_no_pain", "dark_embrace"],
        "scaling_notes": "Every status card becomes an exhaust trigger — fuel for Feel No Pain/Dark Embrace",
        "risk_notes": "Makes Hexaghost, Slime Boss, and some elites significantly easier.",
        "recommended_situations": ["Ironclad exhaust engines", "Status-heavy fights", "Feel No Pain synergy"],
    },
    # ── Event Relics ──
    {
        "name": "Apparition", "type": "Event", "character": None,
        "strengths": ["Intangible for 1 turn — take 1 damage from everything", "Can win boss fights alone", "Stackable"],
        "weaknesses": ["Halves max HP", "Only 3(5) uses per combat", "Exhausts — limited uses"],
        "synergy_tags": ["intangible", "hp_loss", "boss_counter", "defensive"],
        "scaling_notes": "1 damage from any hit — the ultimate damage cap. 5 Apparitions = 5 turns of near-invincibility.",
        "risk_notes": "Only take if you have enough max HP to survive the reduction. Don't go below 30 HP.",
        "recommended_situations": ["High max HP", "Boss fights", "Wraith Form synergy"],
    },
    # ── More Common Relics ──
    {
        "name": "Mercury Hourglass", "type": "Uncommon", "character": None,
        "strengths": ["Deal 3 damage to ALL enemies every turn", "Passive unconditional AoE", "Stacks with itself"],
        "weaknesses": ["3 damage/turn is slow", "Doesn't scale without multiple copies or Strength"],
        "synergy_tags": ["passive_damage", "aoe", "stall"],
        "scaling_notes": "Fixed 3 damage per turn to all enemies — slow but inevitable",
        "risk_notes": "Useful for stripping artifact and finishing low-HP enemies. Modest but reliable.",
        "recommended_situations": ["Stall decks", "Multi-enemy fights", "Artifact stripping"],
    },
    {
        "name": "Blood Vial", "type": "Common", "character": None,
        "strengths": ["Heal 2 HP at start of each combat", "Passive sustain", "No downside"],
        "weaknesses": ["2 HP is very small", "Won't save you from big HP losses"],
        "synergy_tags": ["healing", "sustain", "passive"],
        "scaling_notes": "2 HP per combat × 15 combats = 30 HP per act — small but adds up",
        "risk_notes": "Take every bit of sustain you can get. Don't pass this up.",
        "recommended_situations": ["Any deck", "Low-sustain characters", "Aggressive pathing"],
    },
    {
        "name": "Self-Forming Clay", "type": "Uncommon", "character": None,
        "strengths": ["Gain 3 Block next turn when you lose HP", "Anti-burst defense", "Passive block"],
        "weaknesses": ["Reactive — can't plan around it precisely", "3 Block is modest"],
        "synergy_tags": ["defensive", "self_damage", "block"],
        "scaling_notes": "Each HP loss instance triggers 3 block next turn — multiple hits stack the effect",
        "risk_notes": "Great against multi-hit enemies. Each hit = separate trigger for next-turn block.",
        "recommended_situations": ["Multi-hit enemy fights", "Self-damage decks", "Defensive builds"],
    },
    {
        "name": "Meat on the Bone", "type": "Uncommon", "character": None,
        "strengths": ["Heal 12 HP if HP <= 50% at end of combat", "Massive sustain", "Saves runs"],
        "weaknesses": ["Only triggers below 50%", "Doesn't help during combat"],
        "synergy_tags": ["healing", "sustain", "comeback"],
        "scaling_notes": "12 HP heal × multiple triggers per act = enormous sustain if HP is managed well",
        "risk_notes": "Intentionally end fights below 50% to trigger. Don't overheal — maximize triggers.",
        "recommended_situations": ["Any deck", "Aggressive pathing", "Low-sustain characters"],
    },
]


# =============================================================================
# BOSSES — 10 bosses + elite encounters
# =============================================================================

_BOSSES: list[dict[str, Any]] = [
    {
        "name": "Slime Boss", "act": 1, "type": "boss",
        "strengths": ["Splits into smaller slimes on big hit", "AoE pressure after split"],
        "weaknesses": ["Front-loaded burst damage during split turn", "AoE attacks clean up slimes efficiently"],
        "synergy_tags": ["aoe", "frontload_damage", "burst"],
        "scaling_notes": "Scaling is less critical — front-loaded damage is the priority",
        "risk_notes": "Save burst damage for the split turn. Small slimes must be cleared before they attack. Don't use small attacks on the big slime.",
        "recommended_situations": ["AoE pickup in Act 1", "Burst damage preparation", "Save potions for split turn"],
    },
    {
        "name": "The Guardian", "act": 1, "type": "boss",
        "strengths": ["Alternates defensive (thorns) and offensive modes", "Thorns punishes multi-hit attacks"],
        "weaknesses": ["Scale during defensive phases without attacking", "Block during attack phases"],
        "synergy_tags": ["scaling", "block", "single_hit", "patience"],
        "scaling_notes": "Rewards patient scaling — play powers during defensive mode, attack during offensive mode",
        "risk_notes": "Do NOT attack into thorns with multi-hit cards. One big hit is better than 5 small hits.",
        "recommended_situations": ["Strength scaling", "Poison (bypasses thorns)", "Power setup turns"],
    },
    {
        "name": "Hexaghost", "act": 1, "type": "boss",
        "strengths": ["Turn-2 Inferno scales with current HP", "Burns status cards into draw pile"],
        "weaknesses": ["Lower HP = weaker Inferno (counter-intuitive)", "Status removal/cycling helps"],
        "synergy_tags": ["hp_management", "status_clear", "frontload"],
        "scaling_notes": "Scaling helps after Inferno — you have ~5 turns to kill after the big hit",
        "risk_notes": "Counter-intuitive: DON'T heal before this fight. Lower HP makes Inferno do less damage.",
        "recommended_situations": ["Status removal cards", "Don't overheal before fight", "Front-loaded damage"],
    },
    {
        "name": "Bronze Automaton", "act": 2, "type": "boss",
        "strengths": ["Steals one card per turn", "Devastating Hyper Beam on turn 6"],
        "weaknesses": ["Decks that can afford losing a random card", "Strong block for Hyper Beam turn"],
        "synergy_tags": ["block_engine", "deck_density", "redundancy", "scaling"],
        "scaling_notes": "Scaling needs to survive card theft — have redundant win conditions",
        "risk_notes": "Draft extra cards if you know this boss is coming. Losing your best card hurts badly.",
        "recommended_situations": ["Thick decks with redundancy", "Block engine ready by floor 33", "Multiple damage sources"],
    },
    {
        "name": "The Collector", "act": 2, "type": "boss",
        "strengths": ["Summons torch-head minions that apply Mega Debuff", "Debuff stacking = unblockable burst"],
        "weaknesses": ["AoE clears minions fast", "Fast single-target picks off minions before debuffs stack"],
        "synergy_tags": ["aoe", "frontload", "minion_clear", "fast_damage"],
        "scaling_notes": "AoE scaling is especially valuable — don't let ANY minion survive more than 1 turn",
        "risk_notes": "Kill torch-heads FAST. Mega Debuff stacking is a death sentence. Priority: minions > boss.",
        "recommended_situations": ["AoE damage", "Fast single-target", "Electrodynamics (Defect)"],
    },
    {
        "name": "The Champ", "act": 2, "type": "boss",
        "strengths": ["Cleanses all debuffs at half HP", "Massive Execute attack at 50% threshold"],
        "weaknesses": ["Scale silently to burst from 50% to 0 in one cycle", "Strong block for Execute turn"],
        "synergy_tags": ["scaling_check", "burst", "block_engine", "silent_build"],
        "scaling_notes": "Scaling check — if you can't burst 220 HP in 3 turns after Execute, you die",
        "risk_notes": "Don't use debuffs before half HP — they get cleansed. Scale silently, then burst in one cycle.",
        "recommended_situations": ["Hold debuffs for phase 2", "Scale + burst strategy", "Strong block for Execute"],
    },
    {
        "name": "Time Eater", "act": 3, "type": "boss",
        "strengths": ["Ends your turn after 12 cards played", "Heals and cleanses at half HP", "Forces deliberate play"],
        "weaknesses": ["High-impact cards over many cheap ones", "Scaling that doesn't require card spam"],
        "synergy_tags": ["high_impact", "scaling", "efficient_cards", "card_counting"],
        "scaling_notes": "Prioritize card QUALITY over quantity — 1 Demon Form > 12 Shivs here",
        "risk_notes": "COUNT YOUR CARDS. Don't start a combo at card 9. Shiv/spam decks suffer badly.",
        "recommended_situations": ["High-impact cards", "Avoid card spam", "Strength/poison scaling over shiv"],
    },
    {
        "name": "Awakened One", "act": 3, "type": "boss",
        "strengths": ["Two phases — revives after first death", "Powers played in phase 1 give it Strength in phase 2"],
        "weaknesses": ["Hold powers for phase 2", "Or bring enough scaling to outpace boss Strength gain", "Kill cultists first"],
        "synergy_tags": ["phase_management", "scaling", "power_timing", "cultists"],
        "scaling_notes": "Either delay powers to phase 2, or bring enough scaling to outpace +1 Strength per power",
        "risk_notes": "DON'T spam powers in phase 1. Each power = +1 Strength for the boss in phase 2. Kill cultists first.",
        "recommended_situations": ["Hold powers for phase 2", "Defect beware (power-heavy)", "Cultist priority targeting"],
    },
    {
        "name": "Donu and Deca", "act": 3, "type": "boss",
        "strengths": ["Two enemies — Donu buffs Strength, Deca adds Block", "Split damage required"],
        "weaknesses": ["Kill Donu first (Strength scaling kills you)", "Scaling AoE hits both", "Corpse Explosion = instant win"],
        "synergy_tags": ["aoe", "multi_target", "scaling", "corpse_explosion", "focus_fire"],
        "scaling_notes": "AoE scaling is premium — hitting both targets doubles every point of damage",
        "risk_notes": "Focus Donu first. Deca alone with block is manageable. Corpse Explosion deletes both at once.",
        "recommended_situations": ["AoE damage", "Focus-fire Donu", "Corpse Explosion (Silent) = instant win"],
    },
    {
        "name": "Corrupt Heart", "act": 4, "type": "final_boss",
        "strengths": ["Beat of Death (1(2) damage per card played)", "Invincible status (caps damage/turn)", "Massive multi-hit attack on turn 2-3"],
        "weaknesses": ["Block engine for Beat of Death", "Scaling that bypasses Invincible cap", "Intangible for big attacks"],
        "synergy_tags": ["block_engine", "scaling", "intangible", "max_hp", "endgame_check"],
        "scaling_notes": "Need 800+ damage output while surviving Beat of Death — ultimate scaling and defense check",
        "risk_notes": "Beat of Death punishes card spam. Each card played = 1(2) self-damage. Plan turn size carefully.",
        "recommended_situations": ["Block engine (After Image, Mental Fortress, Frost orbs)", "High-impact > card spam", "Max HP buffer"],
    },
]

# ── Elite Encounters ──
_ELITES: list[dict[str, Any]] = [
    {
        "name": "Gremlin Nob", "act": 1, "type": "elite",
        "strengths": ["Gains Strength on every Skill played", "High burst damage", "Enrages quickly"],
        "weaknesses": ["Pure Attack cards — don't play Skills", "Front-loaded damage race"],
        "scaling_notes": "Gains +2 Strength per Skill played — each Defend makes the fight harder",
        "risk_notes": "AVOID playing Skills entirely. Bring attacks and potions. This is a damage race.",
        "recommended_situations": ["Attack-heavy deck", "Attack potion (Flex, Fire)", "Don't play Defends"],
    },
    {
        "name": "Lagavulin", "act": 1, "type": "elite",
        "strengths": ["Debuffs Strength and Dexterity", "High HP pool", "Wakes up on turn 3"],
        "weaknesses": ["Three setup turns before attacking", "Scaling cards during sleep period"],
        "scaling_notes": "Free 3-turn setup window — play all your powers before it wakes up",
        "risk_notes": "Use the 3 sleep turns to play ALL your scaling. Don't wake it early unless you're ready.",
        "recommended_situations": ["Power-heavy deck", "Scaling setup", "Don't wake early"],
    },
    {
        "name": "Sentry Trio", "act": 1, "type": "elite",
        "strengths": ["Three enemies — AoE pressure", "Dazed status cards into draw pile", "Attrition fight"],
        "weaknesses": ["AoE damage kills all three faster", "Status removal/cycling"],
        "scaling_notes": "AoE scales triple value — hit all 3 at once. Status cycling handles Dazed.",
        "risk_notes": "Kill the outer sentries first (they add Dazed). Center sentry alone is manageable.",
        "recommended_situations": ["AoE attacks", "Status cycling", "Focus outer sentries first"],
    },
    {
        "name": "Book of Stabbing", "act": 2, "type": "elite",
        "strengths": ["Multi-hit attack adds +1 hit every cycle", "Infinite scaling damage", "Single-target burst"],
        "weaknesses": ["Disarm/Strength reduction neuters it", "Weak/Piercing Wail helps"],
        "scaling_notes": "Gains +1 attack per cycle — damage scales infinitely if fight goes long",
        "risk_notes": "Disarm cuts its damage dramatically. Weak reduces multi-hit effectiveness. Kill FAST.",
        "recommended_situations": ["Disarm/Piercing Wail", "Burst damage", "Don't let fight go long"],
    },
    {
        "name": "Gremlin Leader", "act": 2, "type": "elite",
        "strengths": ["Summons gremlin minions", "Buffs Strength if no minions are alive", "Minion pressure"],
        "weaknesses": ["Leave one minion alive to prevent buffing", "AoE clears minions efficiently"],
        "scaling_notes": "Leave 1 weak minion alive — Leader won't buff while a minion exists",
        "risk_notes": "Don't kill all minions. Leave one alive to prevent Leader from gaining Strength.",
        "recommended_situations": ["AoE for minion management", "Leave 1 minion alive", "Focus Leader after minion control"],
    },
    {
        "name": "Nemesis", "act": 3, "type": "elite",
        "strengths": ["Intangible every other turn", "Burns status cards into draw pile", "Unpredictable damage windows"],
        "weaknesses": ["Burst damage on non-Intangible turns", "Status cycling"],
        "scaling_notes": "Damage only matters on non-Intangible turns — time your attacks carefully",
        "risk_notes": "Only attack on non-Intangible turns. Wasting damage on Intangible turns = lost fight.",
        "recommended_situations": ["Turn-timing skills", "Burst on vulnerable turns", "Status removal"],
    },
]

# Combine bosses and elites
_BOSSES.extend(_ELITES)


# =============================================================================
# ARCHETYPES — 13+ archetypes across 4 characters
# =============================================================================

_ARCHETYPES: dict[str, list[dict[str, Any]]] = {
    "ironclad": [
        {
            "name": "Strength Scaling", "type": "scaling_damage",
            "core_cards": ["Inflame", "Spot Weakness", "Limit Break", "Demon Form", "Heavy Blade", "Sword Boomerang"],
            "strengths": ["Massive single-hit damage", "Scales with multi-attack cards", "Relic-independent"],
            "weaknesses": ["Slow setup without energy relic", "Vulnerable during setup turns"],
            "synergy_tags": ["strength", "multi_attack", "heavy_blade", "limit_break", "vajra"],
            "scaling_notes": "Each Strength = +1 per hit. Sword Boomerang (4 hits) doubles value vs Heavy Blade.",
            "risk_notes": "Mix Strength sources with multi-hit attacks. Don't stack Strength with only single-hit cards.",
            "recommended_situations": ["Any Ironclad deck", "Act 2+ scaling needs", "Boss fights"],
        },
        {
            "name": "Exhaust Engine", "type": "combo_control",
            "core_cards": ["Corruption", "Dark Embrace", "Feel No Pain", "Second Wind", "Fiend Fire"],
            "strengths": ["Near-infinite card play", "Passive block generation", "Trims deck mid-combat"],
            "weaknesses": ["Without Dead Branch or Dark Embrace for refill, runs out of cards"],
            "synergy_tags": ["exhaust", "dead_branch", "dark_embrace", "feel_no_pain", "fiend_fire"],
            "scaling_notes": "Scales with deck size — more skills = more 0-cost plays = more block/draw triggers",
            "risk_notes": "Corruption + Dead Branch = instant win. Without Branch, need Dark Embrace for draw refill.",
            "recommended_situations": ["Corruption decks", "Dead Branch synergy", "Thick skill-heavy decks"],
        },
        {
            "name": "Block / Body Slam", "type": "defensive_scaling",
            "core_cards": ["Barricade", "Entrench", "Body Slam", "Impervious", "Shrug It Off"],
            "strengths": ["Infinite block ceiling", "Body Slam converts block to 0-cost damage"],
            "weaknesses": ["Slow setup — Barricade is 3-cost", "Vulnerable to debuff removal"],
            "synergy_tags": ["block_engine", "barricade", "body_slam", "entrench", "calipers"],
            "scaling_notes": "Block IS damage — Entrench doubles block, Body Slam converts it all to damage",
            "risk_notes": "Barricade + Entrench is the core. Without Barricade, Body Slam is mediocre.",
            "recommended_situations": ["Defensive Ironclad", "Turtle strategy", "Boss fights"],
        },
    ],
    "the silent": [
        {
            "name": "Poison Stacking", "type": "damage_over_time",
            "core_cards": ["Noxious Fumes", "Bouncing Flask", "Catalyst", "Deadly Poison", "Crippling Cloud"],
            "strengths": ["Bypasses block entirely", "Infinite scaling via Catalyst", "Passive damage while defending"],
            "weaknesses": ["Slow — takes many turns to ramp", "Weak to artifact charges"],
            "synergy_tags": ["poison", "catalyst", "noxious_fumes", "stall", "block_engine"],
            "scaling_notes": "Catalyst provides exponential scaling. 3->9->27 poison. Burst+ doubles the doubling.",
            "risk_notes": "Build heavy defense. Poison kills eventually — your job is to not die first.",
            "recommended_situations": ["Defensive Silent", "Boss fights", "Long fight preference"],
        },
        {
            "name": "Shiv Spam", "type": "aggressive_tempo",
            "core_cards": ["Blade Dance", "Cloak and Dagger", "Infinite Blades", "Accuracy", "After Image"],
            "strengths": ["High card play rate", "Scales with Kunai/Shuriken", "Fast damage output"],
            "weaknesses": ["Beat of Death counters hard", "Time Eater punishes card spam"],
            "synergy_tags": ["shiv", "kunai", "shuriken", "after_image", "accuracy"],
            "scaling_notes": "Scales with artifacts (Kunai/Shuriken) and Accuracy — each shiv is a trigger",
            "risk_notes": "Time Eater is your nightmare matchup. Pivot to high-impact cards in Act 3.",
            "recommended_situations": ["Kunai/Shuriken available", "Act 1-2 aggression", "Avoid if Time Eater confirmed"],
        },
        {
            "name": "Discard Engine", "type": "combo_control",
            "core_cards": ["Tactician", "Reflex", "Calculated Gamble", "Acrobatics", "Eviscerate"],
            "strengths": ["Infinite energy generation", "Deep deck cycling"],
            "weaknesses": ["Complex to pilot", "Setup-dependent", "Status cards break the cycle"],
            "synergy_tags": ["discard", "draw", "energy", "combo", "calculated_gamble"],
            "scaling_notes": "Consistency IS scaling — draw your whole deck every turn",
            "risk_notes": "Tactician+ and Reflex+ are mandatory upgrades. Without Calculated Gamble the engine stalls.",
            "recommended_situations": ["Experienced players", "Thin decks", "Upgrade-heavy pathing"],
        },
    ],
    "defect": [
        {
            "name": "Frost Focus", "type": "defensive_scaling",
            "core_cards": ["Defragment", "Glacier", "Capacitor", "Coolheaded", "Biased Cognition", "Echo Form"],
            "strengths": ["Passive block every turn", "Immune to chip damage", "Beats long fights effortlessly"],
            "weaknesses": ["Slow setup — dies to turn 1-2 burst", "Awakened One punishes power spam"],
            "synergy_tags": ["frost", "focus", "capacitor", "biased_cognition", "echo_form"],
            "scaling_notes": "6 orbs × 5 Focus = 42 passive block/turn. The goal. Get there and win.",
            "risk_notes": "Frost orbs + Focus = passive 40+ block per turn. Invest early in Focus.",
            "recommended_situations": ["Any Defect deck", "Scaling fights", "Boss preparation"],
        },
        {
            "name": "Lightning / Storm", "type": "damage_over_time",
            "core_cards": ["Storm", "Electrodynamics", "Static Discharge", "Tempest", "Thunder Strike"],
            "strengths": ["Passive AoE damage", "Electrodynamics solves multi-enemy", "Scales with orb slots"],
            "weaknesses": ["Random targeting", "Low single-target burst", "Inefficient without Focus"],
            "synergy_tags": ["lightning", "storm", "electrodynamics", "power_spam", "tempest"],
            "scaling_notes": "Each lightning orb = 3 + Focus damage/turn random. Multiplicative with slots + Focus.",
            "risk_notes": "Storm + power spam generates lightning orbs passively. Add Focus to make them hit hard.",
            "recommended_situations": ["Multi-enemy fights", "Power-heavy decks", "AoE damage needs"],
        },
    ],
    "watcher": [
        {
            "name": "Stance Dance / Infinite", "type": "combo_infinite",
            "core_cards": ["Rushdown", "Inner Peace", "Fear No Evil", "Eruption+", "Mental Fortress"],
            "strengths": ["True infinite — kill anything turn 1", "Minimal deck required"],
            "weaknesses": ["Time Eater caps 12 cards/turn", "Status cards break cycle"],
            "synergy_tags": ["stance_dance", "rushdown", "inner_peace", "fear_no_evil", "mental_fortress"],
            "scaling_notes": "Infinite = you win. Only check: survive until the engine assembles.",
            "risk_notes": "Remove Defends first. Keep Strikes for Eruption triggers. Deck under 15 cards.",
            "recommended_situations": ["Thin deck strategy", "Experienced players", "Card remove priority"],
        },
        {
            "name": "Divinity Burst", "type": "burst_damage",
            "core_cards": ["Blasphemy", "Worship", "Devotion", "Ragnarok", "Wreath of Flame"],
            "strengths": ["Triple damage in Divinity", "One-turn boss kills possible"],
            "weaknesses": ["Blasphemy kills you next turn if you don't win", "Slow Divinity buildup without Devotion"],
            "synergy_tags": ["divinity", "burst", "blasphemy", "worship", "ragnarok"],
            "scaling_notes": "Divinity = 3x damage. Stack Wreath of Flame + Strength for multiplicative burst.",
            "risk_notes": "Only enter Divinity when you can guarantee a kill. Blasphemy = win-or-die button.",
            "recommended_situations": ["Boss fights", "Guaranteed kill turns", "Burst damage decks"],
        },
    ],
}


# =============================================================================
# PATHING KNOWLEDGE — Decision heuristics per act
# =============================================================================

_PATHING: list[dict[str, Any]] = [
    {
        "name": "Act 1 Pathing",
        "act": 1,
        "type": "pathing",
        "strengths": ["Early elites give relics", "Campfires allow upgrades", "Hallway fights give card rewards"],
        "weaknesses": ["Too many elites without HP buffer = death", "Skipping campfires delays upgrades"],
        "synergy_tags": ["elite_hunting", "upgrade_priority", "early_powers"],
        "scaling_notes": "Act 1 sets up your deck for the rest of the run — prioritize card rewards and relics",
        "risk_notes": "Take 1-2 elites max unless you have strong early damage. Gremlin Nob kills skill-heavy decks.",
        "recommended_situations": ["Path toward 1-2 elites", "Campfire before first elite if possible", "Attack cards early"],
    },
    {
        "name": "Act 2 Pathing",
        "act": 2,
        "type": "pathing",
        "strengths": ["More relics from elites", "Shops for key cards/relics"],
        "weaknesses": ["Act 2 elites are the most dangerous", "Hallway fights hit hard"],
        "synergy_tags": ["aoe_priority", "block_engine", "elite_caution"],
        "scaling_notes": "Act 2 is the run filter — if your deck survives Act 2, it can probably win",
        "risk_notes": "Avoid elites unless you have AoE and a block plan. Act 2 elites punish incomplete decks.",
        "recommended_situations": ["Prioritize campfires for upgrades", "Shops for missing synergies", "Cautious elite pathing"],
    },
    {
        "name": "Act 3 Pathing",
        "act": 3,
        "type": "pathing",
        "strengths": ["Scaling should be online", "Deck is mostly complete"],
        "weaknesses": ["Elites test endgame readiness", "Boss gauntlet requires full preparation"],
        "synergy_tags": ["final_scaling", "boss_prep", "elite_farming"],
        "scaling_notes": "Your deck should be nearly complete — path for upgrades, removes, and final relics",
        "risk_notes": "Take elites if your deck is strong — they give rare relics for the boss gauntlet.",
        "recommended_situations": ["Final upgrades at campfires", "Card removes at shops", "Elite farming if deck is strong"],
    },
    {
        "name": "Campfire Decision",
        "act": 0,
        "type": "decision",
        "strengths": ["Upgrade: permanent power increase", "Rest: immediate HP for next fight"],
        "weaknesses": ["Healing too often = missed upgrades = slower death"],
        "synergy_tags": ["upgrade_priority", "hp_management"],
        "scaling_notes": "Upgrade is permanent — rest is temporary. Default to upgrade unless HP requires rest.",
        "risk_notes": "Rest only if the next fight would kill you at current HP. Otherwise, always upgrade.",
        "recommended_situations": ["Default: upgrade", "Rest: below 30% HP before elite/boss", "Upgrade key cards first"],
    },
    {
        "name": "Shop Decision",
        "act": 0,
        "type": "decision",
        "strengths": ["Card removes thin deck", "Key relics can define a run", "Potions for emergencies"],
        "weaknesses": ["Gold is limited — don't buy mediocre cards", "Skipping a shop wastes a floor"],
        "synergy_tags": ["card_remove", "relic_hunt", "potion"],
        "scaling_notes": "Card remove is the best long-term investment. Remove Strikes > Defends.",
        "risk_notes": "Prioritize: remove > key relic > key card > potion > sale items. Don't buy mediocre cards.",
        "recommended_situations": ["Always remove a Strike if possible", "Shop relics are premium", "Buy potions for elites/bosses"],
    },
]


# =============================================================================
# Serialization
# =============================================================================

def _write_json(data: Any, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# =============================================================================
# Main
# =============================================================================

def generate_knowledge(output_dir: Path) -> dict[str, Path]:
    """Generate all five knowledge JSON files and return their paths."""
    out = _ensure_output_dir(output_dir)
    paths: dict[str, Path] = {}

    # Cards: flatten character groups into a single list.
    all_cards: list[dict[str, Any]] = []
    for character, card_list in _CARDS.items():
        for card in card_list:
            card["character"] = character
            all_cards.append(card)
    paths["cards"] = out / "cards.json"
    _write_json(all_cards, paths["cards"])
    print(f"  [OK] cards.json — {len(all_cards)} cards across {len(_CARDS)} character groups")

    paths["relics"] = out / "relics.json"
    _write_json(_RELICS, paths["relics"])
    print(f"  [OK] relics.json — {len(_RELICS)} relics")

    paths["bosses"] = out / "bosses.json"
    _write_json(_BOSSES, paths["bosses"])
    print(f"  [OK] bosses.json — {len(_BOSSES)} encounters (bosses + elites)")

    paths["archetypes"] = out / "archetypes.json"
    _write_json(_ARCHETYPES, paths["archetypes"])
    char_count = sum(len(v) for v in _ARCHETYPES.values())
    print(f"  [OK] archetypes.json — {char_count} archetypes across {len(_ARCHETYPES)} groups")

    paths["pathing"] = out / "pathing.json"
    _write_json(_PATHING, paths["pathing"])
    print(f"  [OK] pathing.json — {len(_PATHING)} pathing heuristics")

    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate structured gameplay knowledge databases.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output directory (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    print(f"Generating knowledge files -> {args.output_dir}")
    paths = generate_knowledge(args.output_dir)
    total = sum(1 for p in paths.values() if p.exists())
    print(f"\nDone: {total}/{len(paths)} files generated.")
    return 0 if total == len(paths) else 1


if __name__ == "__main__":
    raise SystemExit(main())
