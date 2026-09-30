"""
Caves of Qud AI Build Templates & Archetype Knowledge Base
Defines popular Qud character builds, what each class is strong at,
their stat allocation doctrines, skill progression trees, and combat doctrines.
"""

BUILD_TEMPLATES = {
    "rifle_nomad": {
        "name": "Issachar Rifle Nomad (The Ghost of the Salt)",
        "archetype": "Ranged Sniper & Kite Specialist",
        "callings": ["Nomad", "Gunslinger"],
        "strengths": [
            "Extreme range safety: eliminates threats from 15-20 tiles away before they can close in",
            "High penetration with high-velocity lead slugs (1d8+ rifle damage)",
            "Immense mobility and kiting efficiency with Sprint and distance preservation",
            "Strong crowd control via Freezing Ray (freezes pursuers in solid ice)"
        ],
        "weaknesses": [
            "Ammo dependent (requires maintaining spare lead slugs / energy cells)",
            "Vulnerable if cornered in narrow 1-tile dead ends against multiple melee brutes"
        ],
        "preferred_range": 6,  # Maintain distance >= 4, fire at max range
        "stat_priorities": [
            {"stat": "Toughness", "target": 20, "reason": "Survival floor, max HP, and poison/bleed saves"},
            {"stat": "Agility", "target": 24, "reason": "Rifle accuracy, DV dodge value, and Flattening Fire prereqs"},
            {"stat": "Toughness", "target": 26, "reason": "Mid-game HP scaling against rocket/turret bursts"},
            {"stat": "Agility", "target": 30, "reason": "End-game Ultra Fire requirements and untouchable DV"},
            {"stat": "Intelligence", "target": 18, "reason": "Tinkering ammo mods and skill points"}
        ],
        "skill_progression": [
            "Rifles",
            "Rifle_SteadyHands",
            "Rifle_DrawABead",
            "Rifle_FlatteningFire",
            "Rifle_SuppressiveFire",
            "Rifle_SureFire",
            "Acrobatics",
            "Acrobatics_Dodge",          # Spry: +2 DV
            "Acrobatics_SwiftReflexes",  # +5 DV vs missiles
            "Acrobatics_Jump",           # 2-tile gap escape
            "Endurance",
            "Endurance_Swimming",        # Turns deep impassable water into safe path
            "Endurance_Longstrider",     # +10 move speed for effortless kiting
            "Endurance_Weathered",       # Elemental resistance
            "Endurance_ShakeItOff",      # Saves against stun, daze, freeze
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_Butchery"
        ],
        "mutation_priorities": ["FreezingRay", "HeightenedSpeed", "Phasing", "Teleportation"],
        "combat_doctrine": {
            "doctrine_name": "Kite and Snipe",
            "open_combat_action": "Draw a bead and fire rifle at maximum range",
            "close_contact_policy": "Activate Sprint and disengage to safe distance (dist >= 3)",
            "melee_engagement": "Only as emergency fallback when out of ammo or cornered",
            "preferred_weapons": ["Issachar rifle", "Sniper rifle", "Laser rifle", "Carbine"],
            "ability_rotation": [
                "1. Opener & Freeze CC: Cast Freezing Ray (dist 2-8) to freeze pursuers in solid ice.",
                "2. Primary Sniping: Fire high-velocity rifle slugs (FIRE_MISSILE) at maximum range.",
                "3. Emergency Disengage: Activate Sprint and kite into open ground if enemies close to dist <= 2."
            ]
        }
    },

    "axe_berserker": {
        "name": "Marauder Meat-Grinder (The Dismemberer)",
        "archetype": "Melee Bruiser & Bleed Finisher",
        "callings": ["Marauder", "Warden"],
        "strengths": [
            "Brutal close-quarters armor penetration and burst damage",
            "Dismembers enemy limbs, weapons, faces, and heads (instant decapitation)",
            "Massive bleeding damage that stacks and melts high-HP bosses",
            "Melee Charge ability closes gaps instantly and dazes opponents"
        ],
        "weaknesses": [
            "Subject to heavy attrition taking bump-attacks and elemental damage in melee",
            "Needs high AV armor to avoid getting chunked by heavy hitters"
        ],
        "preferred_range": 1,
        "stat_priorities": [
            {"stat": "Strength", "target": 22, "reason": "Weapon penetration (PV) and Dismember chance"},
            {"stat": "Toughness", "target": 22, "reason": "High base HP to win melee trades"},
            {"stat": "Strength", "target": 26, "reason": "Decapitate prereq (Str 25) and Cleave stacking"},
            {"stat": "Agility", "target": 18, "reason": "Hit chance and Spry access"},
            {"stat": "Strength", "target": 30, "reason": "Berserk! prereq (Str 29) for 100% dismember uptime"}
        ],
        "skill_progression": [
            "Axe",
            "Axe_Proficiency",
            "Tactics_Charge",
            "Axe_Dismember",
            "Axe_Cleave",
            "Cudgel_ChargingStrike",
            "Axe_Decapitate",
            "Axe_Berserk",
            "Endurance",
            "Endurance_Calloused",
            "Endurance_ShakeItOff",
            "CookingAndGathering_Butchery"
        ],
        "mutation_priorities": ["HeightenedStrength", "Horns", "MultipleArms", "Regeneration"],
        "combat_doctrine": {
            "doctrine_name": "Charge and Dismember",
            "open_combat_action": "Use Charge to close distance into melee range and daze target",
            "close_contact_policy": "Full melee attack, prioritize high-value enemy limbs with Dismember",
            "melee_engagement": "Relentless aggressive bump-attacks",
            "preferred_weapons": ["Folded carbide battle axe", "Crysteel battle axe", "Vibro-axe"],
            "ability_rotation": [
                "1. Gap-Closer Opener: Melee Charge (dist 2-4) to close distance instantly and daze target.",
                "2. Limb Severing: Dismember adjacent enemies to sever limbs and inflict severe bleed.",
                "3. Armor Shred: Cleave adjacent enemies to permanently reduce their AV.",
                "4. Lethal Finisher: Decapitate or Berserk on wounded targets."
            ]
        }
    },

    "akimbo_gunslinger": {
        "name": "Akimbo Gunslinger (Lead Storm)",
        "archetype": "Rapid-Fire Close-to-Mid Range Gunner",
        "callings": ["Gunslinger", "Arconaut"],
        "strengths": [
            "Fires both pistols simultaneously every turn (Akimbo)",
            "Disarms dangerous armed enemies from distance (Disarming Shot)",
            "Chain Fire dumps 8-12 rounds into a single enemy in 1 turn",
            "Extremely high DV dodge value from high Agility"
        ],
        "weaknesses": [
            "Extremely high ammo consumption rate",
            "Pistols have shorter effective range than rifles (falls off beyond 8 tiles)"
        ],
        "preferred_range": 4,
        "stat_priorities": [
            {"stat": "Agility", "target": 24, "reason": "Pistol hit rate, Akimbo efficiency, and DV"},
            {"stat": "Toughness", "target": 20, "reason": "Survivability buffer"},
            {"stat": "Agility", "target": 30, "reason": "Chain Fire and Faster Than My Shadow"},
            {"stat": "Intelligence", "target": 19, "reason": "Tinkering II to craft custom ammo mods"}
        ],
        "skill_progression": [
            "Pistol",
            "Pistol_Akimbo",
            "Pistol_FastReload",
            "Pistol_DisarmingShot",
            "Pistol_DeadShot",
            "Pistol_ChainFire",
            "Acrobatics",
            "Acrobatics_Dodge",
            "Acrobatics_SwiftReflexes",
            "Tinkering",
            "Tinkering_Scavenger"
        ],
        "mutation_priorities": ["MultipleArms", "HeightenedSpeed", "TripleJointed"],
        "combat_doctrine": {
            "doctrine_name": "Mid-Range Suppressive Sweep",
            "open_combat_action": "Open fire with Akimbo dual pistols at range 4-6",
            "close_contact_policy": "Disarm opponent if armed, cycle Chain Fire",
            "melee_engagement": "Point blank pistol bursts",
            "preferred_weapons": ["Border revolver", "Semi-automatic pistol", "Chain pistol"],
            "ability_rotation": [
                "1. Weapon Denial: Disarming Shot (dist 2-8) to knock ranged/melee weapons out of enemy hands.",
                "2. High Burst Volley: Chain Fire (dist 2-6) to unleash rapid-fire lead storm into target.",
                "3. Sustained Fire: FIRE_MISSILE at optimal distance (dist 2-6)."
            ]
        }
    },

    "esper_mindflayer": {
        "name": "Esper Mindflayer (The Ascendant Will)",
        "archetype": "Pure Mental Sorcerer & Thrall Master",
        "callings": ["Apostle", "Greybeard", "Pilgrim"],
        "strengths": [
            "Commands loyal combat thralls / pets via Proselytize as frontline meat shields",
            "Light Manipulation emits laser beams (Lase) penetrating armor at infinite range",
            "Mental abilities (Sunder Mind, Cryokinesis, Stunning Force) annihilate foes from safety",
            "Force Bubble provides an impenetrable barrier against all physical harm",
            "Massive versatility: teleportation, clairvoyance, temporal fugue clones"
        ],
        "weaknesses": [
            "Psychic Glimmer attracts interdimensional psychic hunters and assassin clones",
            "Physically frail with low Strength and carry weight"
        ],
        "preferred_range": 15,
        "stat_priorities": [
            {"stat": "Ego", "target": 24, "reason": "Mental mutation power, persuasion checks, and penetration scale with Ego"},
            {"stat": "Willpower", "target": 24, "reason": "Drastic cooldown reductions for mental abilities"},
            {"stat": "Toughness", "target": 18, "reason": "Health baseline to survive psychic backlash"},
            {"stat": "Ego", "target": 32, "reason": "Uncapped mutation level and thrall domination scaling"}
        ],
        "skill_progression": [
            "Persuasion",
            "Persuasion_Proselytize",
            "Customs",
            "Customs_Tactful",
            "Discipline",
            "Discipline_MindOverBody",
            "Discipline_IronMind",
            "Endurance"
        ],
        "mutation_priorities": ["LightManipulation", "SunderMind", "Cryokinesis", "Pyrokinesis", "StunningForce", "Teleportation", "ForceBubble"],
        "combat_doctrine": {
            "doctrine_name": "Psychic Dominion & Thrall Vanguard",
            "open_combat_action": "Recruit tough beasts and humanoids with Proselytize to serve as frontline combat tanks. Stay behind your pet, using Stunning Force to CC approaching threats and Lase laser beams for sustained DPS. Pop Force Bubble or Teleport Other if pressed.",
            "close_contact_policy": "Let your pet absorb melee trades while you pop Force Bubble, cast Stunning Force, or backpedal into open ground",
            "melee_engagement": "Strictly avoid physical melee; support your combat pet from safe range",
            "preferred_weapons": ["Light mental focus weapons", "Shield", "Torch"],
            "ability_rotation": [
                "0. Pet Recruitment: If without an active companion, cast Proselytize on an adjacent beast or humanoid (dist 1) to recruit a combat thrall & meat shield.",
                "1. Opener & Crowd Control: Cast Stunning Force (dist 3-8) to stun, daze, and blast advancing enemies backward.",
                "2. Heavy Lethal Channel: Sunder Mind (dist 2-25) against tough, elite, or armored enemies.",
                "3. Sustained Beam Assault: Fire Lase laser beams (dist 1-25, charges permitting) over your pet's shoulder to eliminate targets at range.",
                "4. Elemental Damage: Cast Cryokinesis / Pyrokinesis / Rays to burn or freeze hostile zones.",
                "5. Emergency Close Defense: When enemies breach within dist <= 2, pop Force Bubble, cast Teleport Other to banish them, or use Intimidate to make them flee."
            ]
        }
    },

    "praetorian_tank": {
        "name": "Praetorian Juggernaut (The Iron Wall)",
        "archetype": "True Kin Heavy Armor Tank",
        "callings": ["Praetorian", "Child of the Deep"],
        "strengths": [
            "Unmatched Armor Value (AV 15-25+), rendering normal physical attacks harmless",
            "Shield Block completely negates incoming heavy melee strikes",
            "Heavy weapon suppressive fire rips through hordes",
            "Full access to True Kin high-tier Cybernetics implants"
        ],
        "weaknesses": [
            "Low DV (dodge value) means almost all attacks connect (relies 100% on AV to negate damage)",
            "Vulnerable to armor-penetrating vibro weapons and elemental heat/cold extremes"
        ],
        "preferred_range": 1,
        "stat_priorities": [
            {"stat": "Toughness", "target": 22, "reason": "Massive HP pool to synergize with high AV"},
            {"stat": "Strength", "target": 22, "reason": "Heavy weapon handling and shield bash power"},
            {"stat": "Toughness", "target": 28, "reason": "Total resistance to physical hazards"},
            {"stat": "Strength", "target": 26, "reason": "Carrying ultra-heavy plate armor and cannons"}
        ],
        "skill_progression": [
            "Shield",
            "Shield_Block",
            "Shield_ShieldSlam",
            "HeavyWeapons",
            "HeavyWeapons_Tank",
            "HeavyWeapons_Strafe",
            "LongBlades",
            "LongBlades_Proficiency",
            "LongBlades_DuelistStance",
            "Endurance_Calloused"
        ],
        "mutation_priorities": [],  # True Kin uses Cybernetics
        "combat_doctrine": {
            "doctrine_name": "Anchor and Crush",
            "open_combat_action": "Fire heavy ordnance or advance behind raised tower shield",
            "close_contact_policy": "Shield Slam to knock down enemies, hold frontline",
            "melee_engagement": "Face-tank and trade blows while completely mitigating damage",
            "preferred_weapons": ["Tower shield", "Folded carbide long sword", "Chain gun"],
            "ability_rotation": [
                "1. Suppressive Barrage: Heavy Weapons fire (dist 3-10) to stagger enemy approaches.",
                "2. Melee Stun Bash: Shield Slam adjacent enemies to stun and daze them.",
                "3. Weapon Denial: Swipe / Disarm adjacent enemies to disarm their primary weapon.",
                "4. Defensive Stance: Maintain Duelist Stance for maximum parry and AV."
            ]
        }
    }
}

for _k, _v in BUILD_TEMPLATES.items():
    _v["id"] = _k



def detect_build(game_state):
    """
    Analyzes character calling/subtype, equipment, mutations, and stats to match
    the most accurate build template.
    """
    if not game_state:
        return BUILD_TEMPLATES["rifle_nomad"]

    calling = (game_state.get("calling", "") or game_state.get("subtype", "")).lower()
    equipped = game_state.get("equipped_summary", "").lower()
    has_missile = game_state.get("has_missile_weapon", False)
    mutations = [m.get("class", "").lower() for m in game_state.get("mutations", [])]
    abilities = [a.get("name", "").lower() for a in game_state.get("abilities", [])]
    attrs = game_state.get("attributes", {})
    ego = attrs.get("Ego", 10)
    str_val = attrs.get("Strength", 10)
    agi = attrs.get("Agility", 10)

    # 1. Direct Calling Match
    if calling:
        if any(c in calling for c in ["apostle", "greybeard", "pilgrim"]):
            return BUILD_TEMPLATES["esper_mindflayer"]
        if any(c in calling for c in ["marauder", "warden"]):
            return BUILD_TEMPLATES["axe_berserker"]
        if any(c in calling for c in ["praetorian", "child of the deep"]):
            return BUILD_TEMPLATES["praetorian_tank"]
        if "gunslinger" in calling and ("pistol" in equipped or "revolver" in equipped):
            return BUILD_TEMPLATES["akimbo_gunslinger"]
        if any(c in calling for c in ["nomad", "watervine farmer"]):
            return BUILD_TEMPLATES["rifle_nomad"]

    # 2. Esper detection
    mental_muts = ["sundermind", "cryokinesis", "pyrokinesis", "beguiling", "lightmanipulation", "forcebubble"]
    if any(m in mental_muts for m in mutations) or ego >= 22:
        return BUILD_TEMPLATES["esper_mindflayer"]

    # 3. Akimbo Pistols
    if "pistol" in equipped or "revolver" in equipped or any("akimbo" in a for a in abilities):
        return BUILD_TEMPLATES["akimbo_gunslinger"]

    # 4. Axe Marauder
    if "axe" in equipped or any("dismember" in a for a in abilities) or (str_val >= 20 and str_val > agi + 3):
        return BUILD_TEMPLATES["axe_berserker"]

    # 5. Praetorian Tank
    if "shield" in equipped and ("plate" in equipped or "chain" in equipped or "armor" in equipped):
        return BUILD_TEMPLATES["praetorian_tank"]

    # Default: Rifle Nomad (our primary rifle sniper build)
    return BUILD_TEMPLATES["rifle_nomad"]


def get_stat_allocation_recommendation(template, current_stats):
    """
    Returns the recommended stat to increase according to the template doctrine.
    """
    for rule in template.get("stat_priorities", []):
        st = rule["stat"]
        target = rule["target"]
        cur = current_stats.get(st, 10)
        if cur < target:
            return st, rule["reason"]

    # If all targets reached, boost primary archetype stat
    primary = template["stat_priorities"][0]["stat"]
    return primary, "All benchmark thresholds met; continuing primary scaling."


def get_skill_progression_list(template):
    return template.get("skill_progression", [])


def get_combat_doctrine(template):
    return template.get("combat_doctrine", {})
