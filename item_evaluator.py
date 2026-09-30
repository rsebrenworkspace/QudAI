"""
Item Evaluation Engine for Caves of Qud AI Agent
Implements the 10-criteria rubric and safety overrides from Caves-of-Qud-AI-Agent-Build-Guide.md (lines 680-705).
"""

from typing import Dict, Any, List, Tuple


# Critical safety items that must NEVER be discarded or replaced blindly
PROTECTED_SLOTS = ["Floating Nearby", "Hands", "Back"]

LIGHT_SOURCES = [
    "torch", "floating glowsphere", "glowsphere", "miner's helmet",
    "chem cell powered light", "lantern", "night vision"
]

ESCAPE_ITEMS = [
    "recoiler", "teleportation", "sphere of negative weight",
    "skates", "mechanical wings", "phasing"
]


def score_item(item: Dict[str, Any], template: Dict[str, Any], equipped_gear: List[str] = None, inventory: List[Dict[str, Any]] = None) -> Tuple[int, Dict[str, int], str]:
    """
    Scores an item using the 10-criteria evaluation rubric:
      item_score = enables_core_build (0..5)
                 + improves_primary_damage (0..5)
                 + improves_survivability (0..5)
                 + provides_escape_or_control (0..5)
                 + covers_build_counter (0..5)
                 + weight_burden (-5..0)
                 + ammo_or_power_burden (-5..0)
                 + slot_conflict (-5..0)
                 + friendly_fire_risk (-5..0)
                 + rarity_or_replacement_risk (-3..0)

    Returns:
      (total_score, breakdown_dict, evaluation_summary)
    """
    if not item:
        return 0, {}, "Empty item"

    name = item.get("name", "").lower()
    desc = item.get("description", "").lower()
    weight = item.get("weight", 1)
    av = item.get("av", 0)
    dv = item.get("dv", 0)
    slot = item.get("slot", "").lower()
    is_artifact = item.get("is_artifact", False) or "relic" in name or "cybernetic" in name
    archetype_id = template.get("id", "")

    breakdown = {
        "enables_core_build": 0,
        "improves_primary_damage": 0,
        "improves_survivability": 0,
        "provides_escape_or_control": 0,
        "covers_build_counter": 0,
        "weight_burden": 0,
        "ammo_or_power_burden": 0,
        "slot_conflict": 0,
        "friendly_fire_risk": 0,
        "rarity_or_replacement_risk": 0,
    }

    # 1. Enables core build (0..5)
    pref_weapons = [w.lower() for w in template.get("combat_doctrine", {}).get("preferred_weapons", [])]
    if any(pw in name for pw in pref_weapons):
        breakdown["enables_core_build"] += 4

    if archetype_id in ("auspicious_beginnings", "limb_off", "axe_berserker") and "axe" in name:
        breakdown["enables_core_build"] = max(breakdown["enables_core_build"], 4)
    elif archetype_id in ("praetorian_generalist", "praetorian_tank") and ("rifle" in name or "shield" in name or "long sword" in name):
        breakdown["enables_core_build"] = max(breakdown["enables_core_build"], 4)
    elif archetype_id in ("esper_ited_away", "esper_mindflayer") and ("ego" in desc or "willpower" in desc or "psychic" in desc or "torch" in name or "glowsphere" in name):
        breakdown["enables_core_build"] = max(breakdown["enables_core_build"], 4)
    elif archetype_id in ("classic_punchkin",) and ("fist" in name or "hand bone" in name or "shield" in name or "cudgel" in name):
        breakdown["enables_core_build"] = max(breakdown["enables_core_build"], 5)
    elif archetype_id in ("gunkin", "bullet_specter", "akimbo_gunslinger") and ("pistol" in name or "revolver" in name or "gun rack" in name):
        breakdown["enables_core_build"] = max(breakdown["enables_core_build"], 5)
    elif archetype_id in ("gas_giant",) and ("gas tumbler" in name or "respirator" in name):
        breakdown["enables_core_build"] = max(breakdown["enables_core_build"], 5)

    # 2. Improves primary damage (0..5)
    if "damage" in desc or "penetration" in desc or "pv" in desc or item.get("damage_die"):
        breakdown["improves_primary_damage"] += 3
    if "crysteel" in name or "carbide" in name or "folded" in name or "zetachrome" in name or "vibro" in name:
        breakdown["improves_primary_damage"] += 2

    # 3. Improves survivability (0..5)
    if av > 0:
        breakdown["improves_survivability"] += min(5, av)
    if dv > 0:
        breakdown["improves_survivability"] += min(3, dv)
    if "healing" in desc or "salve" in name or "bandage" in name:
        breakdown["improves_survivability"] += 3

    # 4. Provides escape or control (0..5)
    if any(esc in name for esc in ["recoiler", "teleport", "speed", "sprint", "boots", "wings"]):
        breakdown["provides_escape_or_control"] += 4
    if any(cc in name for cc in ["freeze", "stun", "daze", "sleep", "tangle"]):
        breakdown["provides_escape_or_control"] += 3

    # 5. Covers build counter (0..5)
    # E.g. cold resistance for Auspicious Beginnings, light source for Esper/Night-vision mutants, ranged fallback for melee
    if any(elem in desc for elem in ["heat resist", "cold resist", "acid resist", "electric resist"]):
        breakdown["covers_build_counter"] += 3
    if any(ls in name for ls in LIGHT_SOURCES):
        breakdown["covers_build_counter"] += 4

    # 6. Weight burden (-5..0)
    if weight > 40:
        breakdown["weight_burden"] = -4
    elif weight > 25:
        breakdown["weight_burden"] = -2
    elif weight > 15:
        breakdown["weight_burden"] = -1

    # 7. Ammo or power burden (-5..0)
    if "energy cell" in desc and "depleted" in desc:
        breakdown["ammo_or_power_burden"] = -2
    if "lead slug" in name or "chem cell" in name:
        breakdown["ammo_or_power_burden"] = 0  # Useful supplies

    # 8. Slot conflict (-5..0)
    # If it conflicts with existing core weapon/gear
    if slot in ("hands", "floating nearby", "back") and equipped_gear:
        # Mild conflict if slot is already occupied
        breakdown["slot_conflict"] = -1

    # 9. Friendly-fire risk (-5..0)
    if any(danger in name for danger in ["grenade", "explosive", "thermal grenade", "corrosive gas"]):
        breakdown["friendly_fire_risk"] = -2

    # 10. Rarity or replacement risk (-3..0)
    if is_artifact:
        breakdown["rarity_or_replacement_risk"] = 0  # Do not penalize artifacts
    elif "fragile" in desc or "rusted" in name:
        breakdown["rarity_or_replacement_risk"] = -2

    total_score = sum(breakdown.values())
    summary = f"{name} (Score: {total_score}) [Core:{breakdown['enables_core_build']} Dmg:{breakdown['improves_primary_damage']} Sur:{breakdown['improves_survivability']} Esc:{breakdown['provides_escape_or_control']}]"
    return total_score, breakdown, summary


def can_safely_discard_or_sell(item: Dict[str, Any], inventory: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Hard safety overrides from the build guide:
    - Never discard the only reliable light source, ranged option, escape item, or recoiler.
    - Do not sell unidentified or build-critical artifacts.
    """
    name = item.get("name", "").lower()

    # 1. Unidentified artifacts
    if item.get("unidentified", False) or "unknown" in name or "weird" in name:
        return False, "Hard override: Never sell unidentified artifacts before inspection."

    # 2. Recoilers
    if "recoiler" in name:
        return False, "Hard override: Critical escape recoiler; preserve for teleportation travel."

    # 3. Sole light source check
    if any(ls in name for ls in LIGHT_SOURCES):
        light_count = sum(1 for it in inventory if any(ls in it.get("name", "").lower() for ls in LIGHT_SOURCES))
        if light_count <= 1:
            return False, "Hard override: Cannot discard sole light source."

    # 4. Sole ranged weapon check
    if any(rw in name for rw in ["rifle", "pistol", "revolver", "bow"]):
        ranged_count = sum(1 for it in inventory if any(rw in it.get("name", "").lower() for rw in ["rifle", "pistol", "revolver", "bow"]))
        if ranged_count <= 1:
            return False, "Hard override: Cannot discard sole ranged weapon fallback."

    return True, "Safe to trade/discard"
