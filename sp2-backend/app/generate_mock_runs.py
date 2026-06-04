"""
generate_mock_runs.py — Generate 10 simulated failed Slay the Spire 2 runs.

Each run illustrates a distinct failure mode and is saved as a standalone
JSON file under backend/mock_data/runs/.
"""

from __future__ import annotations

import json
import logging
import uuid
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
logger = logging.getLogger("generate_mock_runs")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).resolve().parent / "mock_data" / "runs"

# Real card & relic names sampled from the STS2 wiki knowledge base so the
# mock data reads authentically.
IRONCLAD_CARDS = [
    "Anger", "Armaments", "Barricade", "Battle Trance", "Blood for Blood",
    "Bloodletting", "Bludgeon", "Body Slam", "Brutality", "Burning Pact",
    "Carnage", "Clash", "Cleave", "Combust", "Corruption", "Dark Embrace",
    "Disarm", "Double Tap", "Dropkick", "Dual Wield", "Entrench", "Evolve",
    "Exhume", "Feed", "Feel No Pain", "Fiend Fire", "Fire Breathing",
    "Flame Barrier", "Flex", "Ghostly Armor", "Havoc", "Headbutt",
    "Heavy Blade", "Hemokinesis", "Immolate", "Impervious", "Inflame",
    "Iron Wave", "Juggernaut", "Limit Break", "Metallicize", "Offering",
    "Perfected Strike", "Pommel Strike", "Power Through", "Pummel",
    "Rage", "Rampage", "Reaper", "Reckless Charge", "Rupture",
    "Searing Blow", "Second Wind", "Seeing Red", "Sentinel", "Sever Soul",
    "Shockwave", "Shrug It Off", "Spot Weakness", "Sword Boomerang",
    "Thunderclap", "True Grit", "Twin Strike", "Uppercut", "Warcry",
    "Whirlwind", "Wild Strike",
]

SILENT_CARDS = [
    "Acrobatics", "Adrenaline", "Afterimage", "Alchemize", "Backflip",
    "Backstab", "Bane", "Blade Dance", "Blur", "Bouncing Flask",
    "Bullet Time", "Burst", "Calculated Gamble", "Caltrops", "Catalyst",
    "Choke", "Cloak and Dagger", "Concentrate", "Corpse Explosion",
    "Crippling Cloud", "Dagger Spray", "Dagger Throw", "Dash",
    "Deadly Poison", "Deflect", "Die Die Die", "Distraction", "Dodge and Roll",
    "Doppelganger", "Endless Agony", "Envenom", "Escape Plan", "Eviscerate",
    "Expertise", "Finisher", "Flechettes", "Flying Knee", "Footwork",
    "Glass Knife", "Grand Finale", "Heel Hook", "Infinite Blades",
    "Leg Sweep", "Malaise", "Masterful Stab", "Neutralize", "Nightmare",
    "Noxious Fumes", "Outmaneuver", "Phantasmal Killer", "Piercing Wail",
    "Poisoned Stab", "Predator", "Prepared", "Quick Slash", "Reflex",
    "Riddle with Holes", "Setup", "Skewer", "Slice", "Storm of Steel",
    "Sucker Punch", "Survivor", "Tactician", "Terror", "Tools of the Trade",
    "Unload", "Well Laid Plans", "Wraith Form",
]

DEFECT_CARDS = [
    "Aggregate", "All for One", "Amplify", "Auto Shields", "Ball Lightning",
    "Barrage", "Beam Cell", "Biased Cognition", "Blizzard", "Boot Sequence",
    "Buffer", "Capacitor", "Chaos", "Chill", "Cold Snap", "Compile Driver",
    "Consume", "Coolheaded", "Core Surge", "Creative AI", "Darkness",
    "Defragment", "Doom and Gloom", "Double Energy", "Dualcast",
    "Echo Form", "Electrodynamics", "Equilibrium", "Fission", "Force Field",
    "FTL", "Fusion", "Genetic Algorithm", "Glacier", "Go for the Eyes",
    "Heatsinks", "Hello World", "Hologram", "Hyperbeam", "Impulse",
    "Leap", "Lock On", "Loop", "Machine Learning", "Melter", "Meteor Strike",
    "Multi-Cast", "Overclock", "Rainbow", "Reboot", "Rebound",
    "Recursion", "Recycle", "Reinforced Body", "Reprogram", "Rip and Tear",
    "Scrape", "Seek", "Self Repair", "Skim", "Stack", "Static Discharge",
    "Steam Barrier", "Storm", "Streamline", "Sunder", "Sweeping Beam",
    "Tempest", "Thunder Strike", "Turbo", "White Noise", "Zap",
]

REGENT_CARDS = [
    "Astral Pulse", "Beacon of Hope", "Celestial Arrow", "Constellation",
    "Cosmic Shield", "Divine Strike", "Eclipse", "Empyrean",
    "Falling Star", "Guiding Light", "Heavenly Strike", "Luminous Burst",
    "Nova", "Oracle", "Pillar of Creation", "Radiant Shield",
    "Shooting Star", "Solar Flare", "Star Align", "Star Barrage",
    "Star Chant", "Star Shower", "Starburst", "Starlight Beacon",
    "Stellar Core", "Sunflare", "Supernova", "Twilight Shield",
    "Void Step", "Zenith",
]

NECROBINDER_CARDS = [
    "Afterlife", "Banshee's Cry", "Bone Armor", "Bone Storm", "Cadaver",
    "Carrion Feast", "Chill of the Grave", "Dark Ritual", "Death Grip",
    "Death Mark", "Doom Clock", "Dread Presence", "Grave Rot",
    "Gravedigger", "Grim Harvest", "Haunting Strike", "Lich Form",
    "Life Drain", "Necrosis", "Nether Shield", "Phantom Strike",
    "Reanimate", "Shadow Bolt", "Soul Bind", "Soul Burn", "Spectral Blade",
    "Tombstone", "Unholy Vigor", "Wither", "Wraith Strike",
]

ALL_RELICS = [
    "Akabeko", "Anchor", "Ancient Tea Set", "Art of War", "Astrolabe",
    "Bag of Marbles", "Bag of Preparation", "Bird-Faced Urn", "Black Star",
    "Blood Vial", "Bloody Idol", "Blue Candle", "Boot", "Bottled Flame",
    "Bottled Lightning", "Bottled Tornado", "Brimstone", "Bronze Scales",
    "Burning Blood", "Calipers", "Calling Bell", "Captain's Wheel",
    "Centennial Puzzle", "Ceramic Fish", "Champion Belt", "Charon's Ashes",
    "Chemical X", "Cloak Clasp", "Coffee Dripper", "Cracked Core",
    "Cursed Key", "Darkstone Periapt", "Data Disk", "Dead Branch",
    "Dolly's Mirror", "Dream Catcher", "Du-Vu Doll", "Ectoplasm",
    "Emotion Chip", "Empty Cage", "Enchiridion", "Eternal Feather",
    "Face of Cleric", "Fossilized Helix", "Frozen Core", "Frozen Egg",
    "Frozen Eye", "Fusion Hammer", "Gambling Chip", "Ginger",
    "Girya", "Golden Idol", "Gremlin Horn", "Hand Drill", "Happy Flower",
    "Holy Water", "Horn Cleat", "Hovering Kite", "Ice Cream",
    "Incense Burner", "Inserter", "Juzu Bracelet", "Kunai", "Lantern",
    "Lee's Waffle", "Letter Opener", "Lizard Tail", "Magic Flower",
    "Mango", "Mark of Pain", "Maw Bank", "Meal Ticket", "Medical Kit",
    "Melange", "Membership Card", "Mercury Hourglass", "Molten Egg",
    "Mummified Hand", "Mutagenic Strength", "Necronomicon", "Neow's Lament",
    "Nilry's Codex", "Ninja Scroll", "Nuclear Battery", "Nunchaku",
    "Odd Mushroom", "Oddly Smooth Stone", "Old Coin", "Omamori",
    "Orange Pellets", "Orichalcum", "Ornamental Fan", "Orrery",
    "Pandora's Box", "Pantograph", "Paper Crane", "Paper Frog",
    "Paper Phrog", "Peace Pipe", "Pear", "Pen Nib", "Philosopher's Stone",
    "Pocketwatch", "Potion Belt", "Prayer Wheel", "Preserved Insect",
    "Prismatic Shard", "Question Card", "Red Mask", "Regal Pillow",
    "Ring of the Serpent", "Ring of the Snake", "Runic Capacitor",
    "Runic Cube", "Runic Dome", "Runic Pyramid", "Sacred Bark",
    "Self-Forming Clay", "Shovel", "Singing Bowl", "Slavers Collar",
    "Sling of Courage", "Smiling Mask", "Snake Skull", "Snecko Eye",
    "Sozu", "Spirit Poop", "Ssserpent Head", "Strange Spoon",
    "Strawberry", "Strike Dummy", "Sundial", "Symbiotic Virus",
    "Teardrop Locket", "The Courier", "The Specimen", "Thread and Needle",
    "Tingsha", "Tiny Chest", "Tiny House", "Toolbox", "Torii",
    "Tough Bandages", "Toxic Egg", "Toy Ornithopter", "Tungsten Rod",
    "Turnip", "Twisted Funnel", "Unceasing Top", "Vajra", "Velvet Choker",
    "War Paint", "Warped Tongs", "Whetstone", "White Beast Statue",
    "Wing Boots", "Wrist Blade",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(path_entry: dict[str, Any]) -> dict[str, Any]:
    """Fill in defaults for a single path entry so the caller only specifies
    the meaningful fields for that floor."""
    defaults: dict[str, Any] = {
        "floor": 0,
        "type": "combat",
        "hp_before": 0,
        "hp_after": 0,
        "picked_card": "",
        "skipped_cards": [],
        "relic_gained": "",
        "notes": "",
    }
    return {**defaults, **path_entry}


# ---------------------------------------------------------------------------
# Run builders (one per failure type)
# ---------------------------------------------------------------------------

def _run_001_low_hp_vs_elite() -> dict[str, Any]:
    """The player enters a floor-16 elite with only 24 HP and no block potions."""
    return {
        "run_id": "mock-001-low-hp-elite",
        "character": "Ironclad",
        "ascension": 5,
        "floor_reached": 16,
        "killed_by": "Gremlin Nob",
        "max_hp": 80,
        "final_hp": 0,
        "gold": 187,
        "cards": [
            "Bash", "Anger", "Cleave", "Shrug It Off",
            "Uppercut", "Twin Strike", "Armaments", "True Grit",
            "Headbutt", "Carnage", "Bloodletting", "Spot Weakness",
        ],
        "relics": [
            "Burning Blood", "Anchor", "Bag of Preparation",
            "Pen Nib", "Happy Flower",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 80, "hp_after": 76, "picked_card": "Anger", "skipped_cards": ["Iron Wave", "Flex"], "notes": "Average starting fight."}),
            _p({"floor": 2, "type": "combat", "hp_before": 82, "hp_after": 78, "picked_card": "Cleave", "skipped_cards": ["Clash"], "notes": "Took Cleave for AoE."}),
            _p({"floor": 3, "type": "event", "hp_before": 84, "hp_after": 84, "picked_card": "", "notes": "Big Fish – traded Banana for a relic."}),
            _p({"floor": 4, "type": "combat", "hp_before": 84, "hp_after": 77, "picked_card": "Shrug It Off", "skipped_cards": ["Wild Strike"], "notes": ""}),
            _p({"floor": 5, "type": "shop", "hp_before": 77, "hp_after": 77, "picked_card": "", "notes": "Bought Anchor relic, skipped cards."}),
            _p({"floor": 6, "type": "combat", "hp_before": 77, "hp_after": 71, "picked_card": "Uppercut", "skipped_cards": ["Heavy Blade", "Thunderclap"], "notes": "Uppercut is a solid pickup."}),
            _p({"floor": 7, "type": "rest", "hp_before": 71, "hp_after": 80, "notes": "Healed to full before elite."}),
            _p({"floor": 8, "type": "elite", "hp_before": 80, "hp_after": 42, "picked_card": "Headbutt", "skipped_cards": ["Body Slam", "Clothesline"], "relic_gained": "Pen Nib", "notes": "Gremlin Nob punished skill-heavy hand. Barely survived."}),
            _p({"floor": 9, "type": "combat", "hp_before": 48, "hp_after": 41, "picked_card": "Carnage", "skipped_cards": ["Searing Blow"], "notes": ""}),
            _p({"floor": 10, "type": "combat", "hp_before": 47, "hp_after": 39, "picked_card": "Bloodletting", "skipped_cards": ["Rupture", "Sentinel"], "notes": "Took Bloodletting for energy but had no sustain to offset HP loss."}),
            _p({"floor": 11, "type": "event", "hp_before": 39, "hp_after": 39, "picked_card": "", "notes": "Wheel of Change – got a Curse, skipped."}),
            _p({"floor": 12, "type": "combat", "hp_before": 39, "hp_after": 31, "picked_card": "Spot Weakness", "skipped_cards": ["Warcry"], "notes": ""}),
            _p({"floor": 13, "type": "combat", "hp_before": 37, "hp_after": 30, "picked_card": "True Grit", "skipped_cards": ["Perfected Strike"], "notes": ""}),
            _p({"floor": 14, "type": "shop", "hp_before": 30, "hp_after": 30, "notes": "Bought potion but not a block potion – Fire Potion."}),
            _p({"floor": 15, "type": "rest", "hp_before": 30, "hp_after": 55, "notes": "Healed but not enough for elite. Should have skipped elite path."}),
            _p({"floor": 16, "type": "elite", "hp_before": 55, "hp_after": 24, "picked_card": "", "relic_gained": "Happy Flower", "notes": "Gremlin Nob again. Entered with Aggression potion active, but draw was all skills. Took 31 in one turn."}),
            # Died on floor 16 — the elite fight itself
        ],
    }


def _run_002_thick_deck() -> dict[str, Any]:
    """Silent picks too many cards; the deck hits 30+ by mid-act 2 and never
    draws the key powers."""
    return {
        "run_id": "mock-002-thick-deck",
        "character": "Silent",
        "ascension": 3,
        "floor_reached": 23,
        "killed_by": "Snake Plant",
        "max_hp": 70,
        "final_hp": 0,
        "gold": 94,
        "cards": [
            "Survivor", "Neutralize", "Blade Dance", "Dagger Throw",
            "Quick Slash", "Backflip", "Bouncing Flask", "Slice",
            "Deflect", "Sucker Punch", "Dodge and Roll", "Prepared",
            "Flying Knee", "Cloak and Dagger", "Poisoned Stab",
            "Piercing Wail", "Caltrops", "Endless Agony", "Reflex",
            "Acrobatics", "Leg Sweep", "Outmaneuver", "Setup",
            "Dagger Spray", "Heel Hook", "Distraction", "Escape Plan",
            "Terror", "Infinite Blades", "Flechettes",
        ],
        "relics": [
            "Ring of the Snake", "Orichalcum", "Maw Bank",
            "Tiny Chest", "Prayer Wheel",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 70, "hp_after": 66, "picked_card": "Blade Dance", "skipped_cards": ["Deflect"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 66, "hp_after": 62, "picked_card": "Dagger Throw", "skipped_cards": ["Slice"], "notes": ""}),
            _p({"floor": 3, "type": "combat", "hp_before": 62, "hp_after": 57, "picked_card": "Quick Slash", "skipped_cards": ["Prepared"], "notes": ""}),
            _p({"floor": 4, "type": "event", "hp_before": 63, "hp_after": 63, "picked_card": "Backflip", "notes": "Took card reward from event – deck is growing."}),
            _p({"floor": 5, "type": "combat", "hp_before": 63, "hp_after": 58, "picked_card": "Bouncing Flask", "skipped_cards": ["Backstab", "Finisher"], "notes": "Took rare poison card but deck is split between shiv and poison."}),
            _p({"floor": 6, "type": "shop", "hp_before": 58, "hp_after": 58, "picked_card": "Slice", "notes": "Bought a cheap card – deck bloat continues."}),
            _p({"floor": 7, "type": "rest", "hp_before": 58, "hp_after": 70, "notes": "Full heal."}),
            _p({"floor": 8, "type": "elite", "hp_before": 70, "hp_after": 44, "picked_card": "Cloak and Dagger", "skipped_cards": ["Storm of Steel", "Skewer"], "relic_gained": "Orichalcum", "notes": "Lagavulin. Long fight, took chip damage every turn."}),
            _p({"floor": 9, "type": "combat", "hp_before": 50, "hp_after": 45, "picked_card": "Poisoned Stab", "skipped_cards": ["Riddle with Holes"], "notes": ""}),
            _p({"floor": 10, "type": "combat", "hp_before": 45, "hp_after": 41, "picked_card": "Piercing Wail", "skipped_cards": ["Dash"], "notes": ""}),
            _p({"floor": 11, "type": "combat", "hp_before": 47, "hp_after": 40, "picked_card": "Caltrops", "skipped_cards": ["Masterful Stab"], "notes": ""}),
            _p({"floor": 12, "type": "event", "hp_before": 40, "hp_after": 40, "picked_card": "", "notes": "Living Wall – swapped a Strike for Endless Agony."}),
            _p({"floor": 13, "type": "combat", "hp_before": 40, "hp_after": 35, "picked_card": "Reflex", "skipped_cards": ["Concentrate", "Tactician"], "notes": ""}),
            _p({"floor": 14, "type": "rest", "hp_before": 35, "hp_after": 58, "notes": ""}),
            _p({"floor": 15, "type": "elite", "hp_before": 58, "hp_after": 29, "picked_card": "Leg Sweep", "skipped_cards": ["Unload", "Blur"], "relic_gained": "Maw Bank", "notes": "Book of Stabbing – had no consistent block engine."}),
            _p({"floor": 16, "type": "combat", "hp_before": 35, "hp_after": 31, "picked_card": "Outmaneuver", "skipped_cards": ["Setup", "Sucker Punch"], "notes": "Prayer Wheel doubles card picks – deck swells to 30 cards."}),
            _p({"floor": 17, "type": "combat", "hp_before": 31, "hp_after": 26, "picked_card": "Dagger Spray", "skipped_cards": ["Deadly Poison"], "notes": ""}),
            _p({"floor": 18, "type": "shop", "hp_before": 26, "hp_after": 26, "picked_card": "Terror", "notes": "Bought Terror but deck is too thick to draw it reliably."}),
            _p({"floor": 19, "type": "rest", "hp_before": 26, "hp_after": 52, "notes": ""}),
            _p({"floor": 20, "type": "combat", "hp_before": 52, "hp_after": 44, "picked_card": "Heel Hook", "skipped_cards": ["Flechettes"], "notes": ""}),
            _p({"floor": 21, "type": "combat", "hp_before": 50, "hp_after": 39, "picked_card": "Infinite Blades", "skipped_cards": ["Escape Plan", "Distraction"], "notes": ""}),
            _p({"floor": 22, "type": "combat", "hp_before": 45, "hp_after": 35, "picked_card": "Flechettes", "skipped_cards": ["Grand Finale"], "notes": "Deck is now 30 cards. Can't find key powers when needed."}),
            _p({"floor": 23, "type": "combat", "hp_before": 35, "hp_after": 0, "picked_card": "", "notes": "Snake Plant. Drew 0 block cards on turn 2 against 8×3 attack. Dies with Caltrops in draw pile."}),
        ],
    }


def _run_003_poor_defense() -> dict[str, Any]:
    """Defect builds all attacks, ignores Frost orbs and block cards, dies to
    chip damage in act 2."""
    return {
        "run_id": "mock-003-poor-defense",
        "character": "Defect",
        "ascension": 7,
        "floor_reached": 20,
        "killed_by": "Chosen",
        "max_hp": 75,
        "final_hp": 0,
        "gold": 203,
        "cards": [
            "Zap", "Dualcast", "Ball Lightning", "Cold Snap",
            "Barrage", "Streamline", "Sunder", "Melter",
            "Compile Driver", "Hyperbeam", "Beam Cell", "Rip and Tear",
            "Go for the Eyes", "Scrape", "Rebound",
        ],
        "relics": [
            "Cracked Core", "Data Disk", "Lantern", "Vajra",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 75, "hp_after": 70, "picked_card": "Ball Lightning", "skipped_cards": ["Leap"], "notes": "Skipped Leap – wanted damage."}),
            _p({"floor": 2, "type": "combat", "hp_before": 70, "hp_after": 64, "picked_card": "Streamline", "skipped_cards": ["Steam Barrier"], "notes": "Skipped Steam Barrier again."}),
            _p({"floor": 3, "type": "combat", "hp_before": 70, "hp_after": 62, "picked_card": "Cold Snap", "skipped_cards": ["Charge Battery"], "notes": "Only Frost source – not enough."}),
            _p({"floor": 4, "type": "shop", "hp_before": 62, "hp_after": 62, "picked_card": "Melter", "notes": "Bought another attack."}),
            _p({"floor": 5, "type": "combat", "hp_before": 62, "hp_after": 56, "picked_card": "Sunder", "skipped_cards": ["Glacier", "Coolheaded"], "notes": "Chose Sunder over Glacier – all-in on damage."}),
            _p({"floor": 6, "type": "event", "hp_before": 56, "hp_after": 39, "picked_card": "", "notes": "Scrap Ooze – took damage for a relic (Data Disk)."}),
            _p({"floor": 7, "type": "rest", "hp_before": 39, "hp_after": 67, "notes": ""}),
            _p({"floor": 8, "type": "elite", "hp_before": 67, "hp_after": 31, "picked_card": "Hyperbeam", "skipped_cards": ["Self Repair", "Buffer"], "relic_gained": "Lantern", "notes": "Sentries. Hyperbeam cleared, but took heavy damage. Skipped Self Repair!"}),
            _p({"floor": 9, "type": "combat", "hp_before": 37, "hp_after": 31, "picked_card": "Beam Cell", "skipped_cards": ["Stack"], "notes": ""}),
            _p({"floor": 10, "type": "combat", "hp_before": 37, "hp_after": 29, "picked_card": "Rip and Tear", "skipped_cards": ["Equilibrium"], "notes": "Skipped Equilibrium – no block engine developing."}),
            _p({"floor": 11, "type": "rest", "hp_before": 29, "hp_after": 62, "notes": "Desperate heal."}),
            _p({"floor": 12, "type": "combat", "hp_before": 62, "hp_after": 51, "picked_card": "Go for the Eyes", "skipped_cards": ["Force Field", "Reinforced Body"], "notes": ""}),
            _p({"floor": 13, "type": "combat", "hp_before": 57, "hp_after": 48, "picked_card": "Scrape", "skipped_cards": ["Genetic Algorithm"], "notes": "Skipped Genetic Algorithm – ignoring block scaling."}),
            _p({"floor": 14, "type": "event", "hp_before": 48, "hp_after": 48, "picked_card": "Barrage", "notes": ""}),
            _p({"floor": 15, "type": "combat", "hp_before": 48, "hp_after": 40, "picked_card": "Rebound", "skipped_cards": ["Coolheaded"], "notes": "Still skipping block."}),
            _p({"floor": 16, "type": "shop", "hp_before": 40, "hp_after": 40, "notes": "Bought Vajra – more damage. Ignored block potion."}),
            _p({"floor": 17, "type": "elite", "hp_before": 40, "hp_after": 18, "picked_card": "Compile Driver", "skipped_cards": ["Glacier", "Defragment"], "relic_gained": "Vajra", "notes": "Gremlin Leader. Entered with 40 HP, no Frost focus. Barely survived."}),
            _p({"floor": 18, "type": "rest", "hp_before": 18, "hp_after": 46, "notes": "Healed at the wrong camp – needed an upgrade."}),
            _p({"floor": 19, "type": "combat", "hp_before": 46, "hp_after": 28, "picked_card": "", "notes": "Snake Plant again. 8×3 with no block engine."}),
            _p({"floor": 20, "type": "combat", "hp_before": 28, "hp_after": 0, "picked_card": "", "notes": "Chosen. Hexed, all skills cost 2. Drew 4 attacks, no orbs for block. Dies."}),
        ],
    }


def _run_004_low_scaling() -> dict[str, Any]:
    """Regent's star-banking deck never gets going; act boss out-scales."""
    return {
        "run_id": "mock-004-low-scaling",
        "character": "Regent",
        "ascension": 4,
        "floor_reached": 17,
        "killed_by": "The Guardian",
        "max_hp": 75,
        "final_hp": 0,
        "gold": 145,
        "cards": [
            "Celestial Arrow", "Star Chant", "Cosmic Shield",
            "Divine Strike", "Luminous Burst", "Solar Flare",
            "Star Barrage", "Starlight Beacon", "Void Step",
            "Nova", "Guiding Light",
        ],
        "relics": [
            "Holy Water", "Golden Idol", "Smiling Mask",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 75, "hp_after": 70, "picked_card": "Celestial Arrow", "skipped_cards": ["Radiant Shield"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 70, "hp_after": 64, "picked_card": "Star Chant", "skipped_cards": ["Pillar of Creation"], "notes": ""}),
            _p({"floor": 3, "type": "event", "hp_before": 70, "hp_after": 57, "picked_card": "", "notes": "Golden Idol event – lost HP for Idol."}),
            _p({"floor": 4, "type": "combat", "hp_before": 57, "hp_after": 49, "picked_card": "Cosmic Shield", "skipped_cards": ["Twilight Shield"], "notes": ""}),
            _p({"floor": 5, "type": "combat", "hp_before": 55, "hp_after": 47, "picked_card": "Divine Strike", "skipped_cards": ["Stellar Core", "Oracle"], "notes": "Skipped scaling cards Stellar Core and Oracle."}),
            _p({"floor": 6, "type": "rest", "hp_before": 47, "hp_after": 72, "notes": ""}),
            _p({"floor": 7, "type": "elite", "hp_before": 72, "hp_after": 38, "picked_card": "Luminous Burst", "skipped_cards": ["Beacon of Hope", "Constellation"], "relic_gained": "Smiling Mask", "notes": "Took Luminous Burst for immediate damage over scaling."}),
            _p({"floor": 8, "type": "combat", "hp_before": 44, "hp_after": 37, "picked_card": "Solar Flare", "skipped_cards": ["Falling Star"], "notes": ""}),
            _p({"floor": 9, "type": "combat", "hp_before": 43, "hp_after": 36, "picked_card": "Star Barrage", "skipped_cards": ["Heavenly Strike"], "notes": ""}),
            _p({"floor": 10, "type": "shop", "hp_before": 36, "hp_after": 36, "picked_card": "Void Step", "notes": "Bought Void Step – utility but no damage scaling."}),
            _p({"floor": 11, "type": "rest", "hp_before": 36, "hp_after": 66, "notes": ""}),
            _p({"floor": 12, "type": "combat", "hp_before": 66, "hp_after": 57, "picked_card": "Nova", "skipped_cards": ["Star Align", "Shooting Star"], "notes": "Nova is slow. Skipped Star Align scaling."}),
            _p({"floor": 13, "type": "combat", "hp_before": 63, "hp_after": 54, "picked_card": "Guiding Light", "skipped_cards": ["Eclipse"], "notes": ""}),
            _p({"floor": 14, "type": "event", "hp_before": 54, "hp_after": 54, "picked_card": "", "notes": "Upgrade shrine – upgraded Divine Strike."}),
            _p({"floor": 15, "type": "combat", "hp_before": 54, "hp_after": 45, "picked_card": "Starlight Beacon", "skipped_cards": ["Zenith", "Empyrean"], "notes": ""}),
            _p({"floor": 16, "type": "rest", "hp_before": 45, "hp_after": 68, "notes": "Had to rest instead of upgrading – falling behind the curve."}),
            _p({"floor": 17, "type": "boss", "hp_before": 68, "hp_after": 0, "picked_card": "", "notes": "The Guardian. No scaling powers in play. Guardian's thorn mode + 36-damage charge out-scaled the deck. Dies on turn 8."}),
        ],
    }


def _run_005_potion_unused() -> dict[str, Any]:
    """Ironclad hoards a Block Potion and a Fire Potion, dies with both unused."""
    return {
        "run_id": "mock-005-potion-unused",
        "character": "Ironclad",
        "ascension": 6,
        "floor_reached": 22,
        "killed_by": "Book of Stabbing",
        "max_hp": 80,
        "final_hp": 0,
        "gold": 312,
        "cards": [
            "Bash", "Twin Strike", "Headbutt", "Inflame",
            "Shrug It Off", "Uppercut", "Flame Barrier",
            "Disarm", "Spot Weakness", "Reaper", "Whirlwind",
            "Shockwave",
        ],
        "relics": [
            "Burning Blood", "Bottled Flame", "Mercury Hourglass",
            "Meal Ticket", "Strike Dummy",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 80, "hp_after": 74, "picked_card": "Twin Strike", "skipped_cards": ["Clash"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 80, "hp_after": 71, "picked_card": "Headbutt", "skipped_cards": ["Thunderclap"], "notes": ""}),
            _p({"floor": 3, "type": "event", "hp_before": 77, "hp_after": 77, "picked_card": "Inflame", "notes": "Event gave Inflame. Good pickup."}),
            _p({"floor": 4, "type": "combat", "hp_before": 77, "hp_after": 69, "picked_card": "Shrug It Off", "skipped_cards": ["Iron Wave"], "notes": ""}),
            _p({"floor": 5, "type": "combat", "hp_before": 75, "hp_after": 66, "picked_card": "Uppercut", "skipped_cards": ["Sword Boomerang", "Cleave"], "notes": ""}),
            _p({"floor": 6, "type": "rest", "hp_before": 66, "hp_after": 80, "notes": ""}),
            _p({"floor": 7, "type": "shop", "hp_before": 80, "hp_after": 80, "notes": "Bought Block Potion and Fire Potion. Didn't need them yet."}),
            _p({"floor": 8, "type": "elite", "hp_before": 80, "hp_after": 48, "picked_card": "Whirlwind", "skipped_cards": ["Blood for Blood", "Rupture"], "relic_gained": "Bottled Flame", "notes": "Used Whirlwind to clear minions. Took heavy damage – could have used Block Potion to save 12 HP."}),
            _p({"floor": 9, "type": "combat", "hp_before": 54, "hp_after": 46, "picked_card": "Flame Barrier", "skipped_cards": ["Warcry"], "notes": ""}),
            _p({"floor": 10, "type": "event", "hp_before": 52, "hp_after": 52, "picked_card": "", "notes": "Purifier – removed a Strike."}),
            _p({"floor": 11, "type": "combat", "hp_before": 52, "hp_after": 43, "picked_card": "Disarm", "skipped_cards": ["Clothesline", "Pommel Strike"], "notes": "Disarm is good but doesn't help with multi-attacks from Book of Stabbing."}),
            _p({"floor": 12, "type": "rest", "hp_before": 43, "hp_after": 72, "notes": ""}),
            _p({"floor": 13, "type": "combat", "hp_before": 72, "hp_after": 63, "picked_card": "Spot Weakness", "skipped_cards": ["Body Slam"], "notes": ""}),
            _p({"floor": 14, "type": "combat", "hp_before": 69, "hp_after": 60, "picked_card": "Reaper", "skipped_cards": ["Heavy Blade"], "notes": "Reaper is sustain but needs strength to matter."}),
            _p({"floor": 15, "type": "elite", "hp_before": 60, "hp_after": 31, "picked_card": "Shockwave", "skipped_cards": ["Brutality", "Combust"], "relic_gained": "Meal Ticket", "notes": "Had both potions. Saved Block Potion for 'real emergency'. Took 29 damage."}),
            _p({"floor": 16, "type": "rest", "hp_before": 31, "hp_after": 62, "notes": "Healed instead of upgrading – deck is falling behind."}),
            _p({"floor": 17, "type": "combat", "hp_before": 62, "hp_after": 53, "picked_card": "", "notes": ""}),
            _p({"floor": 18, "type": "combat", "hp_before": 59, "hp_after": 50, "picked_card": "", "notes": ""}),
            _p({"floor": 19, "type": "shop", "hp_before": 50, "hp_after": 50, "notes": "Bought Mercury Hourglass. Already had two potions – didn't buy more."}),
            _p({"floor": 20, "type": "combat", "hp_before": 50, "hp_after": 41, "picked_card": "", "notes": ""}),
            _p({"floor": 21, "type": "combat", "hp_before": 47, "hp_after": 38, "picked_card": "", "notes": ""}),
            _p({"floor": 22, "type": "elite", "hp_before": 38, "hp_after": 0, "picked_card": "", "notes": "Book of Stabbing. Turn 4 at 15×6 damage. Both potions still in belt. Dies with Block Potion and Fire Potion unused."}),
        ],
    }


def _run_006_boss_strategy_failure() -> dict[str, Any]:
    """Necrobinder fights Hexaghost with a Doom deck that can't race."""
    return {
        "run_id": "mock-006-boss-strategy",
        "character": "Necrobinder",
        "ascension": 5,
        "floor_reached": 17,
        "killed_by": "Hexaghost",
        "max_hp": 70,
        "final_hp": 0,
        "gold": 178,
        "cards": [
            "Bone Armor", "Haunting Strike", "Shadow Bolt",
            "Doom Clock", "Grave Rot", "Death Mark",
            "Soul Burn", "Dark Ritual", "Carrion Feast",
            "Life Drain", "Phantom Strike",
        ],
        "relics": [
            "Cracked Core", "Darkstone Periapt", "Ssserpent Head",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 70, "hp_after": 65, "picked_card": "Bone Armor", "skipped_cards": ["Wraith Strike"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 71, "hp_after": 63, "picked_card": "Shadow Bolt", "skipped_cards": ["Death Grip"], "notes": ""}),
            _p({"floor": 3, "type": "combat", "hp_before": 69, "hp_after": 61, "picked_card": "Haunting Strike", "skipped_cards": ["Nether Shield"], "notes": ""}),
            _p({"floor": 4, "type": "event", "hp_before": 67, "hp_after": 67, "picked_card": "", "notes": "Ssserpent Head – gained gold, got Doubt curse."}),
            _p({"floor": 5, "type": "shop", "hp_before": 67, "hp_after": 67, "picked_card": "Doom Clock", "notes": "Bought Doom Clock – committing to Doom strategy."}),
            _p({"floor": 6, "type": "combat", "hp_before": 67, "hp_after": 58, "picked_card": "Grave Rot", "skipped_cards": ["Chill of the Grave"], "notes": ""}),
            _p({"floor": 7, "type": "rest", "hp_before": 58, "hp_after": 70, "notes": ""}),
            _p({"floor": 8, "type": "elite", "hp_before": 70, "hp_after": 35, "picked_card": "Dark Ritual", "skipped_cards": ["Tombstone", "Grim Harvest"], "relic_gained": "Darkstone Periapt", "notes": "Sentries. Doom Clock too slow – took tons of damage before Doom triggered."}),
            _p({"floor": 9, "type": "combat", "hp_before": 41, "hp_after": 33, "picked_card": "Soul Burn", "skipped_cards": ["Unholy Vigor"], "notes": ""}),
            _p({"floor": 10, "type": "combat", "hp_before": 39, "hp_after": 30, "picked_card": "Death Mark", "skipped_cards": ["Bone Storm", "Necrosis"], "notes": ""}),
            _p({"floor": 11, "type": "event", "hp_before": 36, "hp_after": 36, "notes": "Dead Adventurer – fought for a relic, no reward."}),
            _p({"floor": 12, "type": "rest", "hp_before": 36, "hp_after": 64, "notes": ""}),
            _p({"floor": 13, "type": "combat", "hp_before": 64, "hp_after": 55, "picked_card": "Life Drain", "skipped_cards": ["Spectral Blade", "Reanimate"], "notes": ""}),
            _p({"floor": 14, "type": "combat", "hp_before": 61, "hp_after": 52, "picked_card": "Carrion Feast", "skipped_cards": ["Wither"], "notes": ""}),
            _p({"floor": 15, "type": "combat", "hp_before": 58, "hp_after": 49, "picked_card": "Phantom Strike", "skipped_cards": ["Dread Presence", "Gravedigger"], "notes": ""}),
            _p({"floor": 16, "type": "rest", "hp_before": 49, "hp_after": 70, "notes": "Healed to full. But Doom Deck is too slow for Hexaghost's Inferno pattern."}),
            _p({"floor": 17, "type": "boss", "hp_before": 70, "hp_after": 0, "picked_card": "", "notes": "Hexaghost. Round 2 Inferno deals 6×6 = 36. Doom Clock at 3 stacks. No burst damage. Dies on round 6 with Hexaghost at 97 HP. Strategy mismatch: Doom is too slow for this boss."}),
        ],
    }


def _run_007_greedy_path() -> dict[str, Any]:
    """Silent takes three elites in act 1 without resting, dies to the third."""
    return {
        "run_id": "mock-007-greedy-path",
        "character": "Silent",
        "ascension": 8,
        "floor_reached": 14,
        "killed_by": "Lagavulin",
        "max_hp": 70,
        "final_hp": 0,
        "gold": 256,
        "cards": [
            "Survivor", "Neutralize", "Dagger Throw", "Quick Slash",
            "Backstab", "Dagger Spray", "Footwork",
            "Leg Sweep",
        ],
        "relics": [
            "Ring of the Snake", "Kunai", "Wrist Blade",
            "Bag of Preparation",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 70, "hp_after": 64, "picked_card": "Dagger Throw", "skipped_cards": ["Slice"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 64, "hp_after": 58, "picked_card": "Quick Slash", "skipped_cards": ["Deflect"], "notes": ""}),
            _p({"floor": 3, "type": "event", "hp_before": 64, "hp_after": 64, "picked_card": "Backstab", "notes": "Event gave Backstab – strong card but need upgrades."}),
            _p({"floor": 4, "type": "combat", "hp_before": 64, "hp_after": 57, "picked_card": "Dagger Spray", "skipped_cards": ["Deadly Poison", "Prepared"], "notes": ""}),
            _p({"floor": 5, "type": "combat", "hp_before": 63, "hp_after": 55, "picked_card": "Footwork", "skipped_cards": ["Bane"], "notes": "Got Footwork – finally a block solution, but unupgraded."}),
            _p({"floor": 6, "type": "elite", "hp_before": 55, "hp_after": 24, "picked_card": "Leg Sweep", "skipped_cards": ["All-Out Attack", "Flechettes"], "relic_gained": "Kunai", "notes": "Gremlin Nob at 55 HP. Footwork was a curse. Survived with 24 HP. GREEDY – should rest next."}),
            _p({"floor": 7, "type": "rest", "hp_before": 24, "hp_after": 48, "notes": "Could have healed to 70 but chose to upgrade Footwork instead. Healed only partially."}),
            _p({"floor": 8, "type": "elite", "hp_before": 48, "hp_after": 19, "picked_card": "", "relic_gained": "Wrist Blade", "notes": "Lagavulin. Footwork+1 helped but entering at 48 HP was greedy. Barely survived."}),
            _p({"floor": 9, "type": "shop", "hp_before": 19, "hp_after": 19, "notes": "Bought a potion but no heal available. Desperate."}),
            _p({"floor": 10, "type": "rest", "hp_before": 19, "hp_after": 46, "notes": "Healed but still not full. Path forces another elite."}),
            _p({"floor": 11, "type": "combat", "hp_before": 52, "hp_after": 42, "picked_card": "", "notes": ""}),
            _p({"floor": 12, "type": "combat", "hp_before": 48, "hp_after": 38, "picked_card": "", "notes": ""}),
            _p({"floor": 13, "type": "event", "hp_before": 44, "hp_after": 44, "notes": "No rest site available before third elite."}),
            _p({"floor": 14, "type": "elite", "hp_before": 44, "hp_after": 0, "picked_card": "", "notes": "Lagavulin again. Turn 1 Siphon Soul drops STR/DEX. Turn 3 double-attack for 40. Dies. Took 3 elites in Act 1 with only 1 full rest – greed killed the run."}),
        ],
    }


def _run_008_wrong_upgrade() -> dict[str, Any]:
    """Defect upgrades Zap and Dualcast early instead of key powers; dies to
    act 2 hallway fights."""
    return {
        "run_id": "mock-008-wrong-upgrade",
        "character": "Defect",
        "ascension": 4,
        "floor_reached": 19,
        "killed_by": "Snecko",
        "max_hp": 75,
        "final_hp": 0,
        "gold": 167,
        "cards": [
            "Zap+1", "Dualcast+1", "Defragment", "Coolheaded",
            "Creative AI", "Glacier", "Ball Lightning",
            "Compile Driver", "Self Repair", "Storm",
        ],
        "relics": [
            "Cracked Core", "Frozen Core", "Inserter",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 75, "hp_after": 69, "picked_card": "Ball Lightning", "skipped_cards": ["Stack"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 69, "hp_after": 62, "picked_card": "Coolheaded", "skipped_cards": ["Rebound"], "notes": ""}),
            _p({"floor": 3, "type": "rest", "hp_before": 68, "hp_after": 68, "notes": "Upgraded Zap instead of Coolheaded. Wanted more damage from starting card."}),
            _p({"floor": 4, "type": "combat", "hp_before": 68, "hp_after": 60, "picked_card": "Defragment", "skipped_cards": ["Streamline", "Go for the Eyes"], "notes": "Got Defragment – the best power but stays unupgraded."}),
            _p({"floor": 5, "type": "event", "hp_before": 60, "hp_after": 60, "picked_card": "", "notes": ""}),
            _p({"floor": 6, "type": "combat", "hp_before": 60, "hp_after": 53, "picked_card": "Glacier", "skipped_cards": ["Sweeping Beam"], "notes": "Glacier is great. But left unupgraded."}),
            _p({"floor": 7, "type": "rest", "hp_before": 53, "hp_after": 53, "notes": "Upgraded Dualcast instead of Defragment. Wanted burst damage."}),
            _p({"floor": 8, "type": "elite", "hp_before": 53, "hp_after": 22, "picked_card": "Creative AI", "skipped_cards": ["Multi-Cast", "Chaos"], "relic_gained": "Frozen Core", "notes": "Creative AI is great but needs energy. Dualcast+1 was irrelevant this fight."}),
            _p({"floor": 9, "type": "rest", "hp_before": 22, "hp_after": 55, "notes": "Had to rest. Three campfires so far, two wasted on wrong upgrades."}),
            _p({"floor": 10, "type": "combat", "hp_before": 55, "hp_after": 46, "picked_card": "Compile Driver", "skipped_cards": ["Heatsinks", "Scrape"], "notes": ""}),
            _p({"floor": 11, "type": "combat", "hp_before": 52, "hp_after": 42, "picked_card": "Self Repair", "skipped_cards": ["Recycle", "Lock On"], "notes": "Self Repair unupgraded – heals 7 instead of 10."}),
            _p({"floor": 12, "type": "shop", "hp_before": 42, "hp_after": 42, "notes": "Bought Inserter relic. Good for orb slots but needs focus scaling."}),
            _p({"floor": 13, "type": "rest", "hp_before": 42, "hp_after": 42, "notes": "FINALLY upgraded Defragment. But it's act 2 and pacing is off."}),
            _p({"floor": 14, "type": "combat", "hp_before": 42, "hp_after": 34, "picked_card": "Storm", "skipped_cards": ["Force Field", "Tempest"], "notes": ""}),
            _p({"floor": 15, "type": "elite", "hp_before": 34, "hp_after": 15, "picked_card": "", "relic_gained": "", "notes": "Book of Stabbing. No focus scaling + unupgraded block. Barely survived 15 HP."}),
            _p({"floor": 16, "type": "rest", "hp_before": 15, "hp_after": 48, "notes": "Desperate heal. Can't upgrade anymore."}),
            _p({"floor": 17, "type": "combat", "hp_before": 48, "hp_after": 38, "picked_card": "", "notes": ""}),
            _p({"floor": 18, "type": "combat", "hp_before": 44, "hp_after": 33, "picked_card": "", "notes": ""}),
            _p({"floor": 19, "type": "combat", "hp_before": 33, "hp_after": 0, "picked_card": "", "notes": "Snecko. Confusion randomized costs. Creative AI and Defragment both cost 3. Dies with a hand full of unplayable cards. Wrong upgrade priority throughout the run."}),
        ],
    }


def _run_009_relic_synergy_issue() -> dict[str, Any]:
    """Regent's Star-based deck picks up Snecko Eye; cost randomization ruins
    the Star-banking engine."""
    return {
        "run_id": "mock-009-relic-synergy",
        "character": "Regent",
        "ascension": 3,
        "floor_reached": 29,
        "killed_by": "The Champ",
        "max_hp": 75,
        "final_hp": 0,
        "gold": 89,
        "cards": [
            "Star Chant", "Star Shower", "Cosmic Shield",
            "Luminous Burst", "Star Barrage", "Oracle",
            "Falling Star", "Star Align", "Stellar Core",
            "Celestial Arrow", "Solar Flare", "Zenith",
            "Twilight Shield", "Empyrean",
        ],
        "relics": [
            "Holy Water", "Golden Idol", "Smiling Mask",
            "Data Disk", "Snecko Eye", "Meal Ticket",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 75, "hp_after": 69, "picked_card": "Star Chant", "skipped_cards": ["Divine Strike"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 69, "hp_after": 62, "picked_card": "Cosmic Shield", "skipped_cards": ["Guiding Light"], "notes": ""}),
            _p({"floor": 3, "type": "event", "hp_before": 68, "hp_after": 55, "picked_card": "", "notes": "Golden Idol event – paid HP."}),
            _p({"floor": 4, "type": "combat", "hp_before": 55, "hp_after": 47, "picked_card": "Star Shower", "skipped_cards": ["Nova"], "notes": ""}),
            _p({"floor": 5, "type": "combat", "hp_before": 53, "hp_after": 45, "picked_card": "Luminous Burst", "skipped_cards": ["Radiant Shield"], "notes": ""}),
            _p({"floor": 6, "type": "rest", "hp_before": 45, "hp_after": 73, "notes": ""}),
            _p({"floor": 7, "type": "elite", "hp_before": 73, "hp_after": 44, "picked_card": "Oracle", "skipped_cards": ["Beacon of Hope", "Star Align"], "relic_gained": "Data Disk", "notes": "Data Disk is +1 Focus – useless for Regent. Dead relic."}),
            _p({"floor": 8, "type": "combat", "hp_before": 50, "hp_after": 42, "picked_card": "Star Barrage", "skipped_cards": ["Heavenly Strike"], "notes": ""}),
            _p({"floor": 9, "type": "shop", "hp_before": 42, "hp_after": 42, "picked_card": "Star Align", "notes": "Star Align is key scaling. Deck is coming together."}),
            _p({"floor": 10, "type": "rest", "hp_before": 42, "hp_after": 72, "notes": "Upgraded Oracle."}),
            _p({"floor": 11, "type": "combat", "hp_before": 72, "hp_after": 63, "picked_card": "Falling Star", "skipped_cards": ["Void Step"], "notes": ""}),
            _p({"floor": 12, "type": "combat", "hp_before": 69, "hp_after": 60, "picked_card": "Stellar Core", "skipped_cards": ["Shooting Star", "Constellation"], "notes": ""}),
            _p({"floor": 13, "type": "event", "hp_before": 60, "hp_after": 60, "picked_card": "Celestial Arrow", "notes": ""}),
            _p({"floor": 14, "type": "combat", "hp_before": 60, "hp_after": 52, "picked_card": "Solar Flare", "skipped_cards": ["Eclipse"], "notes": ""}),
            _p({"floor": 15, "type": "rest", "hp_before": 52, "hp_after": 75, "notes": "Upgraded Star Barrage."}),
            _p({"floor": 16, "type": "boss", "hp_before": 75, "hp_after": 38, "picked_card": "Snecko Eye", "skipped_cards": ["Holy Water", "Empty Cage"], "relic_gained": "Snecko Eye", "notes": "Picked Snecko Eye over Holy Water. Reasoning: '+2 draw per turn is broken.' BIG MISTAKE."}),
            _p({"floor": 17, "type": "combat", "hp_before": 38, "hp_after": 30, "picked_card": "Twilight Shield", "skipped_cards": ["Astral Pulse"], "notes": "Snecko randomizes costs. Star Chant costs 3 – can't bank Stars."}),
            _p({"floor": 18, "type": "event", "hp_before": 36, "hp_after": 36, "picked_card": "", "notes": "Upgrade shrine – upgraded Stellar Core. But Snecko makes cost irrelevant."}),
            _p({"floor": 19, "type": "combat", "hp_before": 42, "hp_after": 33, "picked_card": "Zenith", "skipped_cards": ["Supernova"], "notes": "Zenith costs 3 most turns. Star-banking synergy is broken."}),
            _p({"floor": 20, "type": "rest", "hp_before": 33, "hp_after": 66, "notes": "Had to rest. Can't sustain with Snecko."}),
            _p({"floor": 21, "type": "combat", "hp_before": 66, "hp_after": 57, "picked_card": "Empyrean", "skipped_cards": ["Pillar of Creation"], "notes": ""}),
            _p({"floor": 22, "type": "shop", "hp_before": 57, "hp_after": 57, "notes": "Bought card remove. Removed Defend. But deck is fundamentally broken now."}),
            _p({"floor": 23, "type": "combat", "hp_before": 63, "hp_after": 53, "picked_card": "", "notes": ""}),
            _p({"floor": 24, "type": "combat", "hp_before": 59, "hp_after": 49, "picked_card": "", "notes": ""}),
            _p({"floor": 25, "type": "combat", "hp_before": 55, "hp_after": 44, "picked_card": "", "notes": ""}),
            _p({"floor": 26, "type": "event", "hp_before": 44, "hp_after": 44, "picked_card": "", "notes": "Mind Bloom – took gold."}),
            _p({"floor": 27, "type": "rest", "hp_before": 44, "hp_after": 73, "notes": ""}),
            _p({"floor": 28, "type": "combat", "hp_before": 73, "hp_after": 63, "picked_card": "", "notes": ""}),
            _p({"floor": 29, "type": "boss", "hp_before": 63, "hp_after": 0, "picked_card": "", "notes": "The Champ. Phase 2 Execute. Snecko Eye turned Oracle (normally 1-cost) into 3-cost. Couldn't play it. Star engine collapsed. Dies with 6 Stars banked and no way to spend them."}),
        ],
    }


def _run_010_energy_curve_collapse() -> dict[str, Any]:
    """Necrobinder loads up on 2–3 cost cards with no energy generation,
    draws unplayable hands turn after turn."""
    return {
        "run_id": "mock-010-energy-curve",
        "character": "Necrobinder",
        "ascension": 2,
        "floor_reached": 21,
        "killed_by": "Taskmaster",
        "max_hp": 70,
        "final_hp": 0,
        "gold": 134,
        "cards": [
            "Bone Armor", "Lich Form", "Cadaver",
            "Bone Storm", "Dark Ritual", "Death Grip",
            "Carrion Feast", "Gravedigger", "Soul Burn",
            "Doom Clock", "Dread Presence",
        ],
        "relics": [
            "Cracked Core", "Charon's Ashes", "Calling Bell",
            "Du-Vu Doll",
        ],
        "path": [
            _p({"floor": 1, "type": "combat", "hp_before": 70, "hp_after": 64, "picked_card": "Bone Armor", "skipped_cards": ["Haunting Strike"], "notes": ""}),
            _p({"floor": 2, "type": "combat", "hp_before": 70, "hp_after": 62, "picked_card": "Cadaver", "skipped_cards": ["Shadow Bolt"], "notes": "Cadaver costs 2 – first heavy card."}),
            _p({"floor": 3, "type": "event", "hp_before": 62, "hp_after": 62, "picked_card": "Lich Form", "notes": "Event gave Lich Form – 3 cost rare power. Powerful but expensive."}),
            _p({"floor": 4, "type": "combat", "hp_before": 62, "hp_after": 54, "picked_card": "Bone Storm", "skipped_cards": ["Spectral Blade", "Necrosis"], "notes": "Bone Storm costs 2. Curve getting heavy."}),
            _p({"floor": 5, "type": "combat", "hp_before": 60, "hp_after": 51, "picked_card": "Dark Ritual", "skipped_cards": ["Chill of the Grave"], "notes": "Dark Ritual costs 2. Skipped a 1-cost block card."}),
            _p({"floor": 6, "type": "rest", "hp_before": 51, "hp_after": 70, "notes": "Upgraded Lich Form – still costs 3."}),
            _p({"floor": 7, "type": "elite", "hp_before": 70, "hp_after": 29, "picked_card": "Death Grip", "skipped_cards": ["Nether Shield", "Reanimate"], "relic_gained": "Charon's Ashes", "notes": "Lich Form stuck in hand 3 turns. Only had 3 energy. Took massive damage."}),
            _p({"floor": 8, "type": "shop", "hp_before": 35, "hp_after": 35, "picked_card": "Carrion Feast", "notes": "Bought Carrion Feast – another 2-cost card."}),
            _p({"floor": 9, "type": "rest", "hp_before": 35, "hp_after": 64, "notes": "Had to rest. Dying."}),
            _p({"floor": 10, "type": "combat", "hp_before": 64, "hp_after": 54, "picked_card": "Gravedigger", "skipped_cards": ["Phantom Strike", "Life Drain"], "notes": "Gravedigger costs 2. Still no energy solution."}),
            _p({"floor": 11, "type": "combat", "hp_before": 60, "hp_after": 49, "picked_card": "Soul Burn", "skipped_cards": ["Wither"], "notes": "Soul Burn costs 2."}),
            _p({"floor": 12, "type": "event", "hp_before": 55, "hp_after": 40, "picked_card": "", "notes": "Scrap Ooze – took damage for Calling Bell relic."}),
            _p({"floor": 13, "type": "combat", "hp_before": 46, "hp_after": 36, "picked_card": "Doom Clock", "skipped_cards": ["Banshee's Cry", "Wraith Strike"], "notes": "Doom Clock costs 2. Took it over two 1-cost cards."}),
            _p({"floor": 14, "type": "rest", "hp_before": 36, "hp_after": 66, "notes": ""}),
            _p({"floor": 15, "type": "combat", "hp_before": 66, "hp_after": 55, "picked_card": "Dread Presence", "skipped_cards": ["Grave Rot"], "notes": "Dread Presence costs 2."}),
            _p({"floor": 16, "type": "boss", "hp_before": 55, "hp_after": 21, "picked_card": "", "relic_gained": "Du-Vu Doll", "notes": "Slime Boss. Lich Form finally played on turn 4. Survived with 21 HP."}),
            _p({"floor": 17, "type": "combat", "hp_before": 27, "hp_after": 18, "picked_card": "", "notes": "Act 2 hallway. Drew Lich Form, Cadaver, Bone Storm on turn 1. Can only play 1 card."}),
            _p({"floor": 18, "type": "combat", "hp_before": 24, "hp_after": 14, "picked_card": "", "notes": ""}),
            _p({"floor": 19, "type": "shop", "hp_before": 14, "hp_after": 14, "notes": "Bought Energy Potion – too little, too late."}),
            _p({"floor": 20, "type": "rest", "hp_before": 14, "hp_after": 46, "notes": "Desperate heal. Can't fix curve this late."}),
            _p({"floor": 21, "type": "elite", "hp_before": 46, "hp_after": 0, "picked_card": "", "notes": "Taskmaster. Turn 1: draw Lich Form (3), Bone Storm (2), Gravedigger (2). Can play 1 card. Turn 2: draw Doom Clock (2), Cadaver (2), Defend (1). Dies with an average cost of 2.3 per card. No energy generation."}),
        ],
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RUN_BUILDERS = [
    _run_001_low_hp_vs_elite,
    _run_002_thick_deck,
    _run_003_poor_defense,
    _run_004_low_scaling,
    _run_005_potion_unused,
    _run_006_boss_strategy_failure,
    _run_007_greedy_path,
    _run_008_wrong_upgrade,
    _run_009_relic_synergy_issue,
    _run_010_energy_curve_collapse,
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate all 10 mock runs and write them to individual JSON files."""
    logger.info("=== Generating 10 mock failed runs ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for builder in RUN_BUILDERS:
        try:
            run = builder()
            run_id = run["run_id"]
            filename = f"{run_id}.json"
            path = OUTPUT_DIR / filename
            path.write_text(
                json.dumps(run, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "✓ %s  |  %-10s  A%-2d  floor %2d  %s  (%d cards, %d relics, %d floors)",
                filename,
                run["character"],
                run["ascension"],
                run["floor_reached"],
                run["killed_by"],
                len(run["cards"]),
                len(run["relics"]),
                len(run["path"]),
            )
        except Exception:
            logger.exception("Failed to generate run from %s", builder.__name__)

    logger.info("=== Done — %d runs in %s ===", len(RUN_BUILDERS), OUTPUT_DIR)


if __name__ == "__main__":
    main()
