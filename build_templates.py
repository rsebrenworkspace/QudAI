"""
Caves of Qud AI Build Templates & Archetype Knowledge Base
Implements the 9 core archetypes, stat allocation doctrines, skill progression trees,
and tactical sequencing defined in Caves-of-Qud-AI-Agent-Build-Guide.md.
"""

from skill_database import (
    SKILL_DATABASE,
    get_skill_info,
    is_skill_learnable,
    get_best_skill_to_learn,
)

BUILD_TEMPLATES = {
    # 1. Auspicious Beginnings — freeze/axe escape mutant
    "auspicious_beginnings": {
        "id": "auspicious_beginnings",
        "name": "Auspicious Beginnings (Freeze & Dismember Marauder)",
        "archetype": "Freeze Control & Axe Finisher",
        "callings": ["Marauder", "Warden"],
        "genotype": "Mutated Human",
        "strengths": [
            "Freezing Ray locks dangerous enemies in solid ice from distance 2-8",
            "Multiple Legs provides passive move speed advantage for effortless kiting and disengage",
            "Dismember severs enemy weapon limbs, faces, and heads in melee",
            "Teleportation serves as an absolute emergency escape button"
        ],
        "weaknesses": [
            "Amphibious defect increases water consumption rate",
            "Melee trading before targets are frozen is risky"
        ],
        "preferred_range": 4,
        "stat_priorities": [
            {"stat": "Strength", "target": 22, "reason": "Melee penetration and Dismember chance"},
            {"stat": "Toughness", "target": 20, "reason": "Survivability floor against heavy hitters"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Agility", "target": 20, "reason": "Dodge value (DV) and accuracy"},
            {"stat": "Strength", "target": 26, "reason": "Decapitate and Cleave scaling"},
            {"stat": "Toughness", "target": 24, "reason": "Late game HP buffer"}
        ],
        "skill_progression": [
            "Axe",
            "Axe_Expertise",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Tactics",
            "Tactics_Hurdle",
            "Tactics_Charge",
            "Axe_Cleave",
            "Axe_Dismember",
            "Axe_Decapitate",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Calloused"
        ],
        "mutation_priorities": ["FreezingRay", "MultipleLegs", "Teleportation"],
        "combat_doctrine": {
            "doctrine_name": "Freeze, Close, and Dismember",
            "open_combat_action": "Freeze dangerous targets at range (dist 2-8), then close or disengage",
            "close_contact_policy": "Dismember adjacent targets; escape with Multiple Legs if HP < 60%",
            "melee_engagement": "Execute Dismember and Cleave against frozen/dazed opponents",
            "preferred_weapons": ["Folded carbide battle axe", "Crysteel battle axe", "Vibro-axe"],
            "ability_rotation": [
                "1. Opener & CC: Freezing Ray (dist 2-8) to freeze approaching threats in ice.",
                "2. Gap-Closer: Melee Charge (dist 2-4) on controlled targets to daze them.",
                "3. Limb Severing: Dismember adjacent enemies to eliminate weapon limbs.",
                "4. Armor Shred: Cleave to permanently shred enemy AV.",
                "5. Emergency Escape: Teleportation if surrounded and HP < 50%."
            ]
        }
    },

    # 2. Praetorian Generalist — rifle, sword, and shield True Kin
    "praetorian_generalist": {
        "id": "praetorian_generalist",
        "name": "Praetorian Generalist (Rifle & Tower Shield)",
        "archetype": "Hybrid Ranged Sniper & Shield Frontliner",
        "callings": ["Praetorian", "Child of the Deep", "Nomad"],
        "genotype": "True Kin",
        "strengths": [
            "Optical bioscanner extracts exact enemy HP, AV, DV, and difficulty",
            "Desert rifle / high-velocity lead slugs eliminate threats from 15-20 tiles away",
            "Shield Slam stuns, knocks back, and dazes adjacent melee attackers",
            "High Armor Value (AV 15-25+) renders standard physical attacks harmless"
        ],
        "weaknesses": [
            "Ammo dependent (requires maintaining spare lead slugs / cells)",
            "Vulnerable to armor-penetrating vibro weapons and extreme heat/cold"
        ],
        "preferred_range": 6,
        "stat_priorities": [
            {"stat": "Toughness", "target": 22, "reason": "Massive HP pool to synergize with heavy armor"},
            {"stat": "Strength", "target": 22, "reason": "Melee penetration and shield bash power"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Agility", "target": 20, "reason": "Rifle accuracy and Spry dodge value"},
            {"stat": "Strength", "target": 26, "reason": "End-game heavy weapons and shields"},
            {"stat": "Toughness", "target": 26, "reason": "Hazard and explosive resistance"}
        ],
        "skill_progression": [
            "Rifles",
            "Rifle_SteadyHands",
            "Rifle_DrawABead",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Shield",
            "Shield_Block",
            "Shield_Slam",
            "Rifle_SuppressiveFire",
            "Shield_DeftBlocking",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Calloused"
        ],
        "mutation_priorities": [],  # True Kin uses Cybernetics
        "combat_doctrine": {
            "doctrine_name": "Rifle Opening, Shield Finish",
            "open_combat_action": "Draw a bead and fire high-velocity rifle slugs at maximum range (dist >= 4)",
            "close_contact_policy": "Shield Slam adjacent threats to knock down/stun; swap to blade defense",
            "melee_engagement": "Face-tank with high AV while trading Long Blade strikes",
            "preferred_weapons": ["Desert rifle", "Steel long sword", "Tower shield", "Carbine"],
            "ability_rotation": [
                "1. Sniping Volley: FIRE_MISSILE (dist 4-20) with clear raytraced line-of-fire.",
                "2. Melee Stun Bash: Shield Slam adjacent enemies to stun and knock them back.",
                "3. Blade Strike: Long Blade Duelist Stance bump-attacks to parry and slash.",
                "4. Safe Top-off: Reload rifle whenever enemies are outside melee range."
            ]
        }
    },

    # 3. Limb-Off — durable multiple-arms axe mutant
    "limb_off": {
        "id": "limb_off",
        "name": "Limb-Off (Multi-Arm Meat Grinder)",
        "archetype": "Multi-Weapon Axe Berserker",
        "callings": ["Marauder"],
        "genotype": "Mutated Human",
        "strengths": [
            "Multiple Arms delivers 4-8 simultaneous axe strikes per turn",
            "Dismember removes enemy limbs, heads, and weapons with frightening frequency",
            "Carapace provides massive innate AV and resistance",
            "Regeneration passively regrows severed limbs and speeds HP recovery"
        ],
        "weaknesses": [
            "Requires Multiweapon Fighting skills before multi-axe kit fully matures",
            "Melee-centric: needs gap closers or ranged backup against flying/turret targets"
        ],
        "preferred_range": 1,
        "stat_priorities": [
            {"stat": "Strength", "target": 22, "reason": "PV penetration and Dismember chance"},
            {"stat": "Toughness", "target": 22, "reason": "Base HP to absorb melee counterattacks"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Agility", "target": 20, "reason": "Multiweapon Fighting hit chance"},
            {"stat": "Strength", "target": 28, "reason": "Cleave and Decapitate requirements"}
        ],
        "skill_progression": [
            "Multiweapon_Fighting",
            "Multiweapon_Flurry",
            "Axe",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Axe_Expertise",
            "Multiweapon_Proficiency",
            "Tactics",
            "Tactics_Hurdle",
            "Tactics_Charge",
            "Axe_Cleave",
            "Axe_Dismember",
            "Multiweapon_Expertise",
            "Axe_Decapitate",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Calloused"
        ],
        "mutation_priorities": ["MultipleArms", "Carapace", "Regeneration", "NightVision"],
        "combat_doctrine": {
            "doctrine_name": "Multi-Arm Dismemberment",
            "open_combat_action": "Charge into melee contact; use ranged fallback against flying/explosive threats",
            "close_contact_policy": "Unleash Flurry and Dismember; retreat to 1-tile chokes if surrounded",
            "melee_engagement": "Relentless multi-axe strikes focused on enemy weapon limbs",
            "preferred_weapons": ["Battle axe", "Folded carbide axe", "Crysteel battle axe"],
            "ability_rotation": [
                "1. Gap Closer: Melee Charge (dist 2-4) to close distance and daze target.",
                "2. Multi-Strike Burst: Flurry to attack with all equipped axes in 1 turn.",
                "3. Severe Dismember: Dismember adjacent foes to sever limbs and cause heavy bleed.",
                "4. Armor Shred: Cleave to permanently reduce target AV."
            ]
        }
    },

    # 4. Esper-ited Away — high-Willpower clairvoyant Esper & Thrall Vanguard
    "esper_ited_away": {
        "id": "esper_ited_away",
        "name": "Esper-ited Away (The Clairvoyant Thrallmaster)",
        "archetype": "Pure Mental Sorcerer & Pet Vanguard",
        "callings": ["Apostle", "Greybeard", "Pilgrim"],
        "genotype": "Mutated Human",
        "strengths": [
            "Commands loyal combat thralls via Proselytize as frontline meat shields",
            "Light Manipulation emits laser beams (Lase) penetrating armor at infinite range",
            "Clairvoyance reveals enemy layouts and hidden rooms through solid walls",
            "Sunder Mind annihilates priority targets at range with direct psychic damage",
            "Force Wall / Force Bubble creates an impenetrable barrier against all physical harm"
        ],
        "weaknesses": [
            "Psychic Glimmer attracts interdimensional psychic hunters and assassin clones",
            "Physically frail with low Strength and carry weight"
        ],
        "preferred_range": 15,
        "stat_priorities": [
            {"stat": "Ego", "target": 24, "reason": "Mental mutation power, thrall persuasion, and penetration"},
            {"stat": "Willpower", "target": 24, "reason": "Massive cooldown reductions for mental abilities"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Toughness", "target": 18, "reason": "Health baseline to survive psychic backlash"},
            {"stat": "Ego", "target": 32, "reason": "Uncapped mutation level scaling"}
        ],
        "skill_progression": [
            "Tactics",
            "Tactics_Hurdle",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Discipline",
            "Discipline_Meditate",
            "Discipline_FastingWay",
            "Discipline_IronMind",
            "Discipline_Lionheart",
            "Customs",
            "Customs_Tactful",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Calloused",
            "Tactics_Juke",
            "Survival",
            "Survival_Camp",
            "Survival_Trailblazer"
        ],
        "mutation_priorities": ["LightManipulation", "SunderMind", "Clairvoyance", "ForceWall", "ForceBubble", "Teleportation"],
        "combat_doctrine": {
            "doctrine_name": "Psychic Dominion & Thrall Vanguard",
            "open_combat_action": "Recruit tough beasts/humanoids with Proselytize. Fire Lase / Sunder Mind past pet with clear raytraced line-of-fire. Pop Force Wall if pressed.",
            "close_contact_policy": "Let combat pet absorb melee trades while you pop Force Bubble, cast Stunning Force, or backpedal",
            "melee_engagement": "Strictly avoid physical melee; support your combat pet from safe range",
            "preferred_weapons": ["Floating glowsphere", "Light mental focus weapons", "Shield", "Torch"],
            "ability_rotation": [
                "0. Pet Recruitment: Cast Proselytize on adjacent beast/humanoid (dist 1) if without companion.",
                "1. Opener & CC: Stunning Force (dist 3-8) to blast advancing enemies backward.",
                "2. Lethal Psychic Channel: Sunder Mind (dist 2-25) against tough, elite, or armored enemies.",
                "3. Sustained Beam: Lase laser beams (dist 1-25) ONLY when line-of-fire is clear of pets.",
                "4. Close Defense: Pop Force Bubble / Force Wall when enemies breach dist <= 2."
            ]
        }
    },

    # 5. Uncle Iroh — electrical/fire control caster
    "uncle_iroh": {
        "id": "uncle_iroh",
        "name": "Uncle Iroh (Lightning & Flame Elementalist)",
        "archetype": "Burst Elemental Caster & Wall Tactician",
        "callings": ["Greybeard", "Apostle"],
        "genotype": "Mutated Human",
        "strengths": [
            "Heightened Hearing detects unseen threats behind walls before opening doors",
            "Electrical Generation delivers devastating electrical burst damage",
            "Flaming Ray burns targets at range on a very short cooldown",
            "Force Wall seals corridors and breaks line of effect for safe cooldown recovery"
        ],
        "weaknesses": [
            "Tonic Allergy defect: must NEVER auto-use medical tonics",
            "Cooldown dependent: requires maintaining distance while energy charges recharge"
        ],
        "preferred_range": 6,
        "stat_priorities": [
            {"stat": "Willpower", "target": 22, "reason": "Rapid cooldown cycling for Ray and Electrical Generation"},
            {"stat": "Toughness", "target": 20, "reason": "Survivability buffer against ranged snipers"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Agility", "target": 18, "reason": "Dodge value and positioning"},
            {"stat": "Willpower", "target": 26, "reason": "Continuous elemental generation"}
        ],
        "skill_progression": [
            "Tactics",
            "Tactics_Hurdle",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Weathered",
            "Endurance_Calloused",
            "Tactics_Juke",
            "SingleWeaponFighting",
            "SingleWeaponFighting_OpportuneAttacks",
            "SingleWeaponFighting_WeaponExpertise",
            "SingleWeaponFighting_PenetratingStrikes"
        ],
        "mutation_priorities": ["ElectricalGeneration", "FlamingRay", "HeightenedHearing", "ForceWall"],
        "combat_doctrine": {
            "doctrine_name": "Detect, Wall, and Incinerate",
            "open_combat_action": "Detect targets with Heightened Hearing; burn with Flaming Ray; burst with Electrical Generation",
            "close_contact_policy": "Erect Force Wall to trap enemies or buy cooldown reset turns; reposition safely",
            "melee_engagement": "Avoid melee; use physical backup weapon only against heat/electric immune targets",
            "preferred_weapons": ["Staff", "Shield", "Torch", "Ranged backup rifle"],
            "ability_rotation": [
                "1. Opener Ranged Burn: Flaming Ray (dist 2-8) along clear line-of-fire.",
                "2. Electrical Discharge: Electrical Generation burst on clustered hostiles.",
                "3. Tactical Barrier: Force Wall to seal chokepoints or protect retreat path.",
                "4. Emergency Defense: Intimidate or Cudgel knockback if pressured."
            ]
        }
    },

    # 6. Bullet Specter — phased mutant gunslinger
    "bullet_specter": {
        "id": "bullet_specter",
        "name": "Bullet Specter (Phased Pistol Ghost)",
        "archetype": "Phasing Kiter & Rapid Pistol Duelist",
        "callings": ["Gunslinger"],
        "genotype": "Mutated Human",
        "strengths": [
            "Phasing allows stepping out of phase to pass through walls and evade all physical attacks",
            "Time Dilation slows surrounding enemies, creating huge action-economy advantages",
            "High Agility (23+) delivers unmatched pistol accuracy and extreme Dodge Value (DV)",
            "Triple-jointed enables extreme mobility and defensive agility"
        ],
        "weaknesses": [
            "Tonic Allergy defect: strictly prohibits automated tonic consumption",
            "High ammunition consumption rate requires disciplined supply management"
        ],
        "preferred_range": 5,
        "stat_priorities": [
            {"stat": "Agility", "target": 24, "reason": "Pistol hit rate, Akimbo efficiency, and DV"},
            {"stat": "Toughness", "target": 20, "reason": "Survivability buffer"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Agility", "target": 30, "reason": "Chain Fire and Faster Than My Shadow"},
            {"stat": "Willpower", "target": 20, "reason": "Phasing and Time Dilation cooldown speed"}
        ],
        "skill_progression": [
            "Pistol",
            "Pistol_SteadyHands",
            "Pistol_Akimbo",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Pistol_WeakSpotter",
            "Tactics",
            "Tactics_Hurdle",
            "Tactics_Juke",
            "Acrobatics",
            "Acrobatics_SwiftReflexes",
            "Acrobatics_Dodge",
            "Pistol_DisarmingShot",
            "Pistol_DeadShot",
            "Pistol_EmptyTheClips",
            "Pistol_FastestGun"
        ],
        "mutation_priorities": ["Phasing", "TripleJointed", "TimeDilation", "SunderMind", "NightVision"],
        "combat_doctrine": {
            "doctrine_name": "Phased Pistol Kiting",
            "open_combat_action": "Fire pistols from optimal range (dist 4-6); preserve ammo against trivial targets",
            "close_contact_policy": "Activate Time Dilation or Phasing to reposition through terrain",
            "melee_engagement": "Disarming Shot to strip enemy weapons, then backpedal into open ground",
            "preferred_weapons": ["Border revolver", "Semi-automatic pistol", "Chain pistol"],
            "ability_rotation": [
                "1. Weapon Denial: Disarming Shot (dist 2-8) to disarm dangerous armed enemies.",
                "2. Rapid Volley: Chain Fire (dist 2-6) to unleash rapid lead storm into priority target.",
                "3. Time Control: Time Dilation when enemies close within dist <= 3.",
                "4. Phase Evasion: Phasing to pass through obstacles or evade lethal encirclement."
            ]
        }
    },

    # 7. Classic Punchkin — cybernetic unarmed True Kin
    "classic_punchkin": {
        "id": "classic_punchkin",
        "name": "Classic Punchkin (Carbide Fist Juggernaut)",
        "archetype": "Unarmed Cudgel Stunner & Armor Bruiser",
        "callings": ["Child of the Hearth", "Warden"],
        "genotype": "True Kin",
        "strengths": [
            "Carbide hand bones scale unarmed melee damage and penetration directly with Strength",
            "Slam displaces enemies, crashes them into walls, and inflicts heavy daze/stun",
            "Cudgel skill tree locks enemies into permanent stun-lock cycles",
            "Extremely high base attributes across the board (all 18+ starting)"
        ],
        "weaknesses": [
            "Strictly melee-reliant: requires ranged fallback against flying, explosive, or kiting foes",
            "Subject to attrition without shield block or high AV armor"
        ],
        "preferred_range": 1,
        "stat_priorities": [
            {"stat": "Strength", "target": 24, "reason": "Unarmed penetration and Slam damage"},
            {"stat": "Toughness", "target": 22, "reason": "Melee HP pool to out-trade brutes"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Strength", "target": 30, "reason": "Uncapped fist scaling and Cudgel masteries"},
            {"stat": "Agility", "target": 20, "reason": "Hit accuracy and dodge"}
        ],
        "skill_progression": [
            "Cudgel",
            "Cudgel_Expertise",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Tactics",
            "Tactics_Hurdle",
            "Tactics_Charge",
            "Cudgel_Bludgeon",
            "Cudgel_ChargingStrike",
            "Cudgel_Conk",
            "Cudgel_Backswing",
            "Cudgel_Slam",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Calloused"
        ],
        "mutation_priorities": [],  # True Kin uses Cybernetics (Hand bones, giant hands)
        "combat_doctrine": {
            "doctrine_name": "Unarmed Stun and Slam",
            "open_combat_action": "Close distance using cover/chokes; use ranged fallback against flying/explosive targets",
            "close_contact_policy": "Slam targets into walls/obstacles; maintain cudgel stun pressure",
            "melee_engagement": "Relentless carbide fist strikes to keep targets continuously dazed or stunned",
            "preferred_weapons": ["Carbide hand bones", "Shield", "Tower shield", "Ranged backup rifle"],
            "ability_rotation": [
                "1. Gap Closer / Collision: Cudgel Slam (dist 1-2) to smash target into obstacle and stun.",
                "2. Charging Strike: Cudgel Charging Strike to close distance and stagger.",
                "3. Stun Maintenance: Bludgeon and Backhand to renew daze/stun states.",
                "4. Shield Block: Maintain raised shield for incoming physical mitigation."
            ]
        }
    },

    # 8. Gunkin — gun-rack Akimbo True Kin
    "gunkin": {
        "id": "gunkin",
        "name": "Gunkin (Quad-Gun Akimbo Leadstorm)",
        "archetype": "Multi-Gun Akimbo Gunner",
        "callings": ["Gunslinger", "Artifex", "Praetorian"],
        "genotype": "True Kin",
        "strengths": [
            "Gun rack cybernetic allows equipping 4+ pistols or heavy missile weapons simultaneously",
            "Akimbo fires all equipped missile weapons in a single turn",
            "Rapid Release Finger Flexors drastically cuts firing energy cost",
            "Deadliest burst DPS in Caves of Qud against single targets and boss encounters"
        ],
        "weaknesses": [
            "Extremely ammo and power hungry: requires constant logistics management",
            "Needs high-tier cybernetics and license credits before fully online"
        ],
        "preferred_range": 5,
        "stat_priorities": [
            {"stat": "Agility", "target": 24, "reason": "Pistol hit rate, Akimbo efficiency, and DV"},
            {"stat": "Toughness", "target": 20, "reason": "Survivability buffer"},
            {"stat": "Agility", "target": 32, "reason": "Ultra-fast action economy and Chain Fire"},
            {"stat": "Intelligence", "target": 19, "reason": "Tinkering II to craft custom ammo mods"}
        ],
        "skill_progression": [
            "Pistol",
            "Pistol_SteadyHands",
            "Pistol_Akimbo",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Pistol_WeakSpotter",
            "Pistol_SlingAndRun",
            "Pistol_DisarmingShot",
            "Pistol_DeadShot",
            "Pistol_EmptyTheClips",
            "Pistol_FastestGun",
            "Tactics",
            "Tactics_Hurdle",
            "Tactics_Juke",
            "Acrobatics",
            "Acrobatics_SwiftReflexes",
            "Acrobatics_Dodge"
        ],
        "mutation_priorities": [],  # True Kin uses Cybernetics (Gun rack, Flexors)
        "combat_doctrine": {
            "doctrine_name": "Multi-Gun Akimbo Burst",
            "open_combat_action": "Verify all gun chambers loaded and LOF clear, then unleash Akimbo lead volley",
            "close_contact_policy": "Disarm armed opponents; step back to maintain optimal 4-6 tile firing lane",
            "melee_engagement": "Point blank multi-gun bursts; disengage if out of ammunition",
            "preferred_weapons": ["Border revolver", "Semi-automatic pistol", "Chain pistol", "Laser pistol"],
            "ability_rotation": [
                "1. Weapon Denial: Disarming Shot (dist 2-8) to disarm priority threat.",
                "2. Multi-Gun Burst: Akimbo / Chain Fire (dist 2-6) to dump all barrels into target.",
                "3. Sustained Fire: FIRE_MISSILE at optimal distance.",
                "4. Fast Tactical Reload: Reload all weapons as soon as ammunition drops below 50%."
            ]
        }
    },

    # 9. Gas Giant — continuous corrosive/sleep gas mutant
    "gas_giant": {
        "id": "gas_giant",
        "name": "Gas Giant (Corrosive & Sleep Cloud Master)",
        "archetype": "Continuous AoE Gas Controller",
        "callings": ["Greybeard"],
        "genotype": "Mutated Human",
        "strengths": [
            "Corrosive Gas Generation melts armor and flesh indiscriminately across wide areas",
            "Sleep Gas Generation puts entire rooms of enemies into helpless sleep",
            "Carapace and Heightened Quickness provide passive durability and repositioning speed",
            "At high Willpower, gas generation cooldowns become low enough for continuous uptime"
        ],
        "weaknesses": [
            "Friendly fire hazard: gas clouds harm allies and pets if unmanaged",
            "Ineffective against gas-immune or acid-resistant enemies (requires physical fallback)"
        ],
        "preferred_range": 4,
        "stat_priorities": [
            {"stat": "Willpower", "target": 24, "reason": "Gas generation cooldown reduction"},
            {"stat": "Toughness", "target": 20, "reason": "Health baseline"},
            {"stat": "Intelligence", "target": 15, "reason": "Butchery and Harvestry need Intelligence 15 (forage for food, HANDOFF issue 36)"},
            {"stat": "Willpower", "target": 28, "reason": "Continuous gas generation cycle threshold"},
            {"stat": "Agility", "target": 18, "reason": "Quickness and kite positioning"}
        ],
        "skill_progression": [
            "Tactics",
            "Tactics_Hurdle",
            "CookingAndGathering",
            "CookingAndGathering_Butchery",
            "CookingAndGathering_Harvestry",
            "CookingAndGathering_MealPreparation",
            "Endurance",
            "Endurance_ShakeItOff",
            "Endurance_Longstrider",
            "Endurance_Weathered",
            "Endurance_Calloused",
            "Acrobatics",
            "Acrobatics_SwiftReflexes",
            "Acrobatics_Dodge",
            "Tactics_Juke",
            "Survival",
            "Survival_Camp"
        ],
        "mutation_priorities": ["CorrosiveGasGeneration", "SleepGasGeneration", "Carapace", "HeightenedQuickness", "AdrenalControl"],
        "combat_doctrine": {
            "doctrine_name": "Sleep, Blanket, and Dissolve",
            "open_combat_action": "Map pet positions and airflow; release Sleep Gas to incapacitate cluster; blanket with Corrosive Gas",
            "close_contact_policy": "Kite in circles around the edge of the gas cloud while trapped enemies dissolve",
            "melee_engagement": "Avoid entering own corrosive gas; use ranged fallback against acid-immune targets",
            "preferred_weapons": ["Gas tumbler", "Respirator", "Shield", "Ranged backup rifle"],
            "ability_rotation": [
                "1. Incapacitating Fog: Sleep Gas Generation on advancing hostiles (verify no pets in cloud).",
                "2. Acid Blanket: Corrosive Gas Generation inside sleep cloud to dissolve enemies.",
                "3. Adrenal Surge: Adrenal Control when engaging elite or dangerous mobs.",
                "4. Cloud Perimeter Kite: Backpedal and maneuver around gas borders while cloud ticks."
            ]
        }
    }
}

# Aliases for backward compatibility
BUILD_TEMPLATES["rifle_nomad"] = BUILD_TEMPLATES["praetorian_generalist"]
BUILD_TEMPLATES["axe_berserker"] = BUILD_TEMPLATES["auspicious_beginnings"]
BUILD_TEMPLATES["esper_mindflayer"] = BUILD_TEMPLATES["esper_ited_away"]
BUILD_TEMPLATES["praetorian_tank"] = BUILD_TEMPLATES["praetorian_generalist"]
BUILD_TEMPLATES["akimbo_gunslinger"] = BUILD_TEMPLATES["gunkin"]


def detect_build(game_state):
    """
    Analyzes character calling/subtype, equipment, mutations, cybernetics, and stats
    to match the most accurate build template from the 9 archetypes in the guide.
    """
    if not game_state:
        return BUILD_TEMPLATES["praetorian_generalist"]

    calling = (game_state.get("calling", "") or game_state.get("subtype", "")).lower()
    genotype = (game_state.get("genotype", "")).lower()
    equipped = game_state.get("equipped_summary", "").lower()
    has_missile = game_state.get("has_missile_weapon", False)
    mutations = [m.get("class", "").lower() for m in game_state.get("mutations", [])]
    abilities = [a.get("name", "").lower() for a in game_state.get("abilities", [])]
    attrs = game_state.get("attributes", {})
    ego = attrs.get("Ego", 10)
    str_val = attrs.get("Strength", 10)
    agi = attrs.get("Agility", 10)
    wil = attrs.get("Willpower", 10)

    # 1. Gas Giant detection
    if any(m in mutations for m in ["corrosivegasgeneration", "sleepgasgeneration"]) or any("corrosive gas" in a or "sleep gas" in a for a in abilities):
        return BUILD_TEMPLATES["gas_giant"]

    # 2. Uncle Iroh detection (Electrical Gen + Flaming Ray)
    if ("electricalgeneration" in mutations or any("electrical" in a for a in abilities)) and ("flamingray" in mutations or any("flaming" in a for a in abilities)):
        return BUILD_TEMPLATES["uncle_iroh"]

    # 3. Bullet Specter detection (Phasing + Gunslinger)
    if "phasing" in mutations and ("gunslinger" in calling or "pistol" in equipped):
        return BUILD_TEMPLATES["bullet_specter"]

    # 4. Classic Punchkin (Carbide Hand Bones / Unarmed True Kin)
    if "carbide hand" in equipped or "hand bones" in equipped or ("child of the hearth" in calling and str_val >= 20):
        return BUILD_TEMPLATES["classic_punchkin"]

    # 5. Limb-Off (Multi-Arms Axe Marauder)
    if "multiplearms" in mutations and ("axe" in equipped or "marauder" in calling or any("dismember" in a for a in abilities)):
        return BUILD_TEMPLATES["limb_off"]

    # 6. Auspicious Beginnings (Freezing Ray + Axe Marauder)
    if "freezingray" in mutations and ("axe" in equipped or "marauder" in calling):
        return BUILD_TEMPLATES["auspicious_beginnings"]

    # 7. Esper-ited Away (Psychic powers / Apostle / Greybeard)
    mental_muts = ["sundermind", "lightmanipulation", "clairvoyance", "forcewall", "forcebubble", "teleportation", "cryokinesis", "pyrokinesis"]
    if any(m in mental_muts for m in mutations) or any(c in calling for c in ["apostle", "greybeard", "pilgrim"]) or ego >= 20:
        return BUILD_TEMPLATES["esper_ited_away"]

    # 8. Gunkin (Gun rack / Akimbo True Kin)
    if "gun rack" in equipped or (("true kin" in genotype or "true_kin" in genotype) and ("pistol" in equipped or "revolver" in equipped)):
        return BUILD_TEMPLATES["gunkin"]

    # 9. Praetorian Generalist (Rifle + Shield True Kin / General Sniper)
    if any(c in calling for c in ["praetorian", "child of the deep", "nomad", "watervine farmer"]):
        return BUILD_TEMPLATES["praetorian_generalist"]

    # Equipment fallbacks
    if "pistol" in equipped or "revolver" in equipped or any("akimbo" in a for a in abilities):
        return BUILD_TEMPLATES["gunkin"]
    if "axe" in equipped or any("dismember" in a for a in abilities):
        return BUILD_TEMPLATES["auspicious_beginnings"]
    if "shield" in equipped:
        return BUILD_TEMPLATES["praetorian_generalist"]

    # Default: Praetorian Generalist
    return BUILD_TEMPLATES["praetorian_generalist"]


def get_stat_allocation_recommendation(template, current_stats):
    """Returns the recommended stat to increase according to the template doctrine."""
    for rule in template.get("stat_priorities", []):
        st = rule["stat"]
        target = rule["target"]
        cur = current_stats.get(st, 10)
        if cur < target:
            return st, rule["reason"]

    primary = template["stat_priorities"][0]["stat"]
    return primary, "All benchmark thresholds met; continuing primary scaling."


def get_skill_progression_list(template):
    return template.get("skill_progression", [])


def get_combat_doctrine(template):
    return template.get("combat_doctrine", {})


def get_mutation_allocation_recommendation(template, current_mutations, mp):
    """
    Evaluates mutation points (MP) spending according to archetype doctrine.
    Returns (action_string, reason_string) or (None, None).
    - If mp >= 4:
      Checks whether to unlock a new mutation ability (especially if core priorities are missing,
      or existing mutations are capped).
    - If mp >= 1:
      Checks whether to level up an existing core mutation.
    """
    if mp <= 0:
        return None, None

    mut_priorities = template.get("mutation_priorities", [])
    if not mut_priorities:
        # True Kin or unconfigured
        return None, None

    # Check which existing mutations can be leveled
    can_level_muts = [
        m for m in current_mutations
        if m.get("can_level", False) and m.get("level", 0) < m.get("cap", 99)
    ]
    can_level_any_mut = len(can_level_muts) > 0

    # Check for missing priority mutations
    curr_classes = {m.get("class", "").lower() for m in current_mutations}
    curr_names = {m.get("name", "").lower() for m in current_mutations}
    missing_priorities = [
        p for p in mut_priorities
        if p.lower() not in curr_classes and p.lower() not in curr_names
    ]

    # Level 4 mechanic: At 4 MP, mutants can unlock a new mutation ability!
    if mp >= 4:
        # If there are core missing priority mutations, or if existing mutations cannot be leveled:
        if missing_priorities:
            preferred = missing_priorities[0]
            return f"AUTOLEVEL_BUY_MUTATION:{preferred}", f"Class Progression ({template['name']}): Unlocking new mutation ability (Priority: {preferred}) for 4 MP"
        elif not can_level_any_mut:
            return "AUTOLEVEL_BUY_MUTATION", f"Class Progression ({template['name']}): All mutations capped; unlocking new mutation ability for 4 MP"

    # Otherwise, level up existing priority mutations
    if can_level_any_mut:
        for p in mut_priorities:
            m_obj = next((m for m in can_level_muts if m.get("class", "").lower() == p.lower()), None)
            if m_obj:
                return f"AUTOLEVEL_MUTATION:{m_obj.get('class')}", f"Class Progression ({template['name']}): Leveling {m_obj.get('name')}"

    # Fallback if mp >= 4 and nothing else to level
    if mp >= 4:
        return "AUTOLEVEL_BUY_MUTATION", f"Class Progression ({template['name']}): Unlocking new mutation ability for 4 MP"

    return None, None

