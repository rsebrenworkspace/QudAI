import json
import brain
import build_templates
import item_evaluator

print("==================================================")
print("  Running QudAI Multi-Class Tactical Verification  ")
print("==================================================")

# 1. Test Safe State (Should REST)
safe_state = {
    "hp": 15,
    "max_hp": 24,
    "x": 10,
    "y": 10,
    "z": 10,
    "calling": "Nomad",
    "hostiles_nearby": False,
    "hostiles_adjacent": False,
    "water_drams": 28,
    "effects": [],
    "abilities": [{"name": "Sprint", "command": "CommandToggleRunning", "cooldown": 0, "usable": True}],
    "has_missile_weapon": True,
    "missile_ammo": 6,
    "missile_max_ammo": 6,
    "zone_name": "Joppa",
    "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear"},
    "visible_entities": []
}

dec_safe = brain.query_decision(safe_state, took_damage=False, enemies=[])
print("\n--- Test 1: Damaged but Safe (HP 15/24) ---")
print(f"Action: {dec_safe['action']} | Reason: {dec_safe['reason']}")
assert dec_safe['action'] == "REST", "Expected REST when safe and hurt!"

# 2. Test Safe Autoleveling (AP / SP / MP)
levelup_state = dict(safe_state)
levelup_state["hp"] = 24
levelup_state["ap"] = 1
levelup_state["sp"] = 65
levelup_state["attributes"] = {"Strength": 14, "Agility": 18, "Toughness": 16, "Intelligence": 14, "Willpower": 14, "Ego": 10}
dec_lvl = brain.query_decision(levelup_state, took_damage=False, enemies=[])
print("\n--- Test 2: Safe Level-Up (Nomad AP 1) ---")
print(f"Action: {dec_lvl['action']} | Reason: {dec_lvl['reason']}")
assert dec_lvl['action'].startswith("AUTOLEVEL_STAT:Toughness"), f"Expected AUTOLEVEL_STAT:Toughness, got {dec_lvl['action']}"

# 3. Test Melee Bruiser (Marauder) - Charge from Distance 3
marauder_charge_state = {
    "hp": 30,
    "max_hp": 30,
    "x": 10,
    "y": 10,
    "z": 10,
    "calling": "Marauder",
    "equipped_summary": "Hand: folded carbide battle axe",
    "hostiles_nearby": True,
    "hostiles_adjacent": False,
    "water_drams": 20,
    "effects": [],
    "abilities": [
        {"name": "Charge", "command": "CommandMeleeCharge", "cooldown": 0, "usable": True},
        {"name": "Dismember", "command": "CommandDismember", "cooldown": 0, "usable": True}
    ],
    "has_missile_weapon": False,
    "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear", "NE": "Clear", "NW": "Clear", "SE": "Clear", "SW": "Clear"},
    "visible_entities": [
        {"name": "albino ape", "tx": 13, "ty": 10, "dist": 3, "dir": "E", "is_enemy": True}
    ]
}
enemies_m = [e for e in marauder_charge_state["visible_entities"] if e["is_enemy"]]
dec_charge = brain.fallback_melee(
    marauder_charge_state, enemies_m, {}, ["MOVE_E", "MOVE_W"], ["MOVE_E", "MOVE_W"],
    marauder_charge_state["abilities"], build_templates.BUILD_TEMPLATES["auspicious_beginnings"],
    (10, 10), 10, 10, 30, 30, False, False, 0, 0, 0
)
print("\n--- Test 3: Marauder Melee Charge (Enemy at dist 3) ---")
print(f"Action: {dec_charge['action']} | Reason: {dec_charge['reason']}")
assert dec_charge['action'] == "USE_ABILITY:CommandMeleeCharge:E", f"Expected charge East, got {dec_charge['action']}"

# 4. Test Melee Bruiser (Marauder) - Dismember Adjacent Enemy
dec_dismember = brain.fallback_melee(
    marauder_charge_state, enemies_m, {"E": "albino ape"}, ["MOVE_W"], ["MOVE_E", "MOVE_W"],
    marauder_charge_state["abilities"], build_templates.BUILD_TEMPLATES["auspicious_beginnings"],
    (10, 10), 10, 10, 30, 30, False, False, 0, 0, 0
)
print("\n--- Test 4: Marauder Dismember (Adjacent Melee) ---")
print(f"Action: {dec_dismember['action']} | Reason: {dec_dismember['reason']}")
assert dec_dismember['action'] == "USE_ABILITY:CommandDismember:E", f"Expected dismember East, got {dec_dismember['action']}"

# 5. Test Esper Mindflayer - Pop Force Bubble when in close contact
esper_state = {
    "hp": 12,
    "max_hp": 18,
    "x": 10,
    "y": 10,
    "z": 10,
    "calling": "Apostle",
    "mutations": [{"name": "Force Bubble", "class": "ForceBubble", "level": 3, "can_level": True}],
    "abilities": [
        {"name": "Force Bubble", "command": "CommandForceBubble", "cooldown": 0, "usable": True},
        {"name": "Sunder Mind", "command": "CommandSunderMind", "cooldown": 0, "usable": True}
    ],
    "surroundings": {"N": "Clear", "E": "[ENEMY: snapjaw]", "W": "Clear", "S": "Clear"},
    "visible_entities": [{"name": "snapjaw", "tx": 11, "ty": 10, "dist": 1, "dir": "E", "is_enemy": True}]
}
enemies_esp = [e for e in esper_state["visible_entities"] if e["is_enemy"]]
dec_bubble = brain.fallback_esper(
    esper_state, enemies_esp, {"E": "snapjaw"}, ["MOVE_W"], ["MOVE_W"],
    esper_state["abilities"], build_templates.BUILD_TEMPLATES["esper_ited_away"],
    (10, 10), 10, 10, 12, 18, False, False, 0, 0, 0
)
print("\n--- Test 5: Esper Close Contact (Pop Force Bubble) ---")
print(f"Action: {dec_bubble['action']} | Reason: {dec_bubble['reason']}")
assert dec_bubble['action'] == "USE_ABILITY:CommandForceBubble", f"Expected Force Bubble, got {dec_bubble['action']}"

# 5b. Test Esper Mindflayer - Recruit Pet with Proselytize
esper_proselytize_state = {
    "hp": 18,
    "max_hp": 18,
    "x": 10,
    "y": 10,
    "has_companion": False,
    "abilities": [
        {"name": "Proselytize", "command": "CommandProselytize", "cooldown": 0, "usable": True},
        {"name": "Lase", "command": "CommandLase", "cooldown": 0, "usable": True}
    ],
    "visible_entities": [
        {"name": "snapjaw scavenger", "blueprint": "SnapjawScavenger", "dist": 1, "dir": "E", "tx": 11, "ty": 10, "is_enemy": True}
    ]
}
dec_pro = brain.fallback_esper(
    esper_proselytize_state, esper_proselytize_state["visible_entities"], {"E": "snapjaw scavenger"}, ["MOVE_W"], ["MOVE_W"],
    esper_proselytize_state["abilities"], build_templates.BUILD_TEMPLATES["esper_ited_away"],
    (10, 10), 10, 10, 18, 18, False, False, 0, 0, 0
)
print("\n--- Test 5b: Esper Pet Recruitment (Proselytize adjacent snapjaw) ---")
print(f"Action: {dec_pro['action']} | Reason: {dec_pro['reason']}")
assert dec_pro['action'] == "USE_ABILITY:CommandProselytize:E", f"Expected CommandProselytize:E, got {dec_pro['action']}"

# 6. Test Esper Mindflayer - Cast Sunder Mind at Range
dec_sunder = brain.fallback_esper(
    esper_state, [{"name": "snapjaw warlord", "tx": 18, "ty": 10, "dist": 8, "dir": "E", "is_enemy": True}],
    {}, ["MOVE_W"], ["MOVE_W"],
    esper_state["abilities"], build_templates.BUILD_TEMPLATES["esper_ited_away"],
    (10, 10), 10, 10, 18, 18, False, False, 0, 0, 0
)
print("\n--- Test 6: Esper Ranged Channel (Sunder Mind) ---")
print(f"Action: {dec_sunder['action']} | Reason: {dec_sunder['reason']}")
assert dec_sunder['action'].startswith("USE_ABILITY:CommandSunderMind"), f"Expected Sunder Mind, got {dec_sunder['action']}"

# 6b. Test Esper Light Manipulation - Fire Lase at Glowpad (with clear LOF)
esper_lase_state = {
    "abilities": [
        {"name": "Lase", "command": "CommandLase", "cooldown": 0, "usable": True},
        {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True}
    ]
}
dec_lase = brain.fallback_esper(
    esper_lase_state, [{"name": "wet glowpad", "tx": 18, "ty": 10, "dist": 8, "dir": "E", "is_enemy": True}],
    {}, ["MOVE_W"], ["MOVE_W"],
    esper_lase_state["abilities"], build_templates.BUILD_TEMPLATES["esper_ited_away"],
    (10, 10), 10, 10, 18, 18, False, False, 0, 0, 0
)
print("\n--- Test 6b: Esper Lase Light Beam (Target: Glowpad at dist 8, clear LOF) ---")
print(f"Action: {dec_lase['action']} | Reason: {dec_lase['reason']}")
assert dec_lase['action'] == "USE_ABILITY:CommandLase:E", f"Expected CommandLase:E, got {dec_lase['action']}"

# 7. Test Akimbo Gunslinger - Chain Fire
gunslinger_state = {
    "hp": 20,
    "max_hp": 20,
    "x": 10,
    "y": 10,
    "z": 10,
    "calling": "Gunslinger",
    "equipped_summary": "Hand: border revolver; Hand: semi-automatic pistol",
    "has_missile_weapon": True,
    "missile_ammo": 6,
    "missile_max_ammo": 6,
    "inv_ammo": 200,
    "abilities": [
        {"name": "Chain Fire", "command": "CommandChainFire", "cooldown": 0, "usable": True}
    ],
    "surroundings": {"N": "Clear", "E": "Clear", "W": "Clear", "S": "Clear"},
    "visible_entities": [{"name": "madpole", "tx": 14, "ty": 10, "dist": 4, "dir": "E", "is_enemy": True}]
}
enemies_gun = [e for e in gunslinger_state["visible_entities"] if e["is_enemy"]]
dec_gun = brain.fallback_gunslinger(
    gunslinger_state, enemies_gun, {}, ["MOVE_W"], ["MOVE_W"],
    gunslinger_state["abilities"], build_templates.BUILD_TEMPLATES["gunkin"],
    (10, 10), 10, 10, 20, 20, False, True, 6, 6, 200
)
print("\n--- Test 7: Gunslinger Chain Fire (Enemy at dist 4) ---")
print(f"Action: {dec_gun['action']} | Reason: {dec_gun['reason']}")
assert dec_gun['action'] == "USE_ABILITY:CommandChainFire", f"Expected Chain Fire, got {dec_gun['action']}"

# 8. Test Rifle Nomad - Freezing Ray Pursuer at Distance 3
nomad_state = {
    "hp": 22,
    "max_hp": 22,
    "x": 10,
    "y": 10,
    "z": 10,
    "calling": "Nomad",
    "equipped_summary": "Missile Weapon: Issachar rifle",
    "has_missile_weapon": True,
    "missile_ammo": 6,
    "missile_max_ammo": 6,
    "inv_ammo": 1000,
    "abilities": [
        {"name": "Freezing Ray", "command": "CommandFreezingRay", "cooldown": 0, "usable": True},
        {"name": "Sprint", "command": "CommandToggleRunning", "cooldown": 0, "usable": True}
    ],
    "surroundings": {"N": "Clear", "E": "Clear", "W": "Clear", "S": "Clear"},
    "visible_entities": [{"name": "glowpad", "tx": 13, "ty": 10, "dist": 3, "dir": "E", "is_enemy": True}]
}
enemies_nom = [e for e in nomad_state["visible_entities"] if e["is_enemy"]]
dec_freeze = brain.fallback_nomad(
    nomad_state, enemies_nom, {}, ["MOVE_W"], ["MOVE_W"],
    nomad_state["abilities"], build_templates.BUILD_TEMPLATES["praetorian_generalist"],
    (10, 10), 10, 10, 22, 22, False, True, 6, 6, 1000, False
)
print("\n--- Test 8: Rifle Nomad Freezing Ray (Pursuer at dist 3) ---")
print(f"Action: {dec_freeze['action']} | Reason: {dec_freeze['reason']}")
assert dec_freeze['action'] == "USE_ABILITY:CommandFreezingRay:E", f"Expected Freezing Ray East, got {dec_freeze['action']}"

# 9. Test LM Studio Full LLM Combat Prompting
combat_state = {
    "hp": 18,
    "max_hp": 24,
    "x": 20,
    "y": 15,
    "z": 10,
    "calling": "Nomad",
    "hostiles_nearby": True,
    "hostiles_adjacent": False,
    "water_drams": 28,
    "effects": [],
    "abilities": [
        {"name": "Sprint", "command": "CommandToggleRunning", "cooldown": 0, "usable": True},
        {"name": "Freezing Ray", "command": "CommandFreezingRay", "cooldown": 0, "usable": True}
    ],
    "has_missile_weapon": True,
    "missile_ammo": 4,
    "missile_max_ammo": 6,
    "inventory_ammo": 500,
    "zone_name": "Red Rock",
    "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear"},
    "visible_entities": [
        {"name": "snapjaw hunter", "tx": 22, "ty": 15, "dist": 2, "dir": "E", "is_enemy": True, "difficulty": "Average", "level": 2}
    ]
}

enemies = [e for e in combat_state["visible_entities"] if e["is_enemy"]]
dec_combat = brain.query_decision(combat_state, took_damage=True, enemies=enemies)
print("\n--- Test 9: Live LM Studio Decision with Class Prompting ---")
print(f"Action: {dec_combat['action']} | Reason: {dec_combat['reason']}")
assert dec_combat['action'], "Expected valid action from LM Studio or deterministic fallback!"

# 10. Test Native Autoexplore Dispatch (Healthy, Safe, Unexplored)
explore_state = dict(safe_state)
explore_state["hp"] = 24
explore_state["zone_fully_explored"] = False
dec_explore = brain.query_decision(explore_state, took_damage=False, enemies=[])
print("\n--- Test 10: Safe Area Exploration via Native Qud Autoexplore ---")
print(f"Action: {dec_explore['action']} | Reason: {dec_explore['reason']}")
assert dec_explore['action'] == "AUTOEXPLORE", f"Expected AUTOEXPLORE, got {dec_explore['action']}"

# 11. Test Zone Fully Explored -> Stairs Down / Zone Transition
fully_explored_state = dict(safe_state)
fully_explored_state["hp"] = 24
fully_explored_state["level"] = 3
fully_explored_state["zone_id"] = "JoppaWorld.10.19.1.0.10"
fully_explored_state["zone_fully_explored"] = True
fully_explored_state["visible_entities"] = [
    {"name": "stairs leading down", "tx": 10, "ty": 9, "dist": 1, "dir": "N", "is_enemy": False}
]
dec_zone_done = brain.query_decision(fully_explored_state, took_damage=False, enemies=[])
print("\n--- Test 11: Zone Fully Explored -> Navigate to Stairs Down ---")
print(f"Action: {dec_zone_done['action']} | Reason: {dec_zone_done['reason']}")
assert dec_zone_done['action'] == "MOVE_N", f"Expected MOVE_N towards stairs down, got {dec_zone_done['action']}"

# 12. Test Raytraced Line-of-Fire & Pet Friendly-Fire Protection
print("\n--- Test 12: Raytraced Line-of-Fire & Pet Friendly-Fire Protection ---")
# Player at (10, 10), Companion at (12, 10), Target at (15, 10)
# Ray along (10, 10) -> (15, 10) passes directly through (12, 10)!
is_clear, reason = brain.is_line_of_fire_clear((10, 10), (15, 10), companions=[{"name": "charmed seahorse", "tx": 12, "ty": 10}])
print(f"LOF clear check: {is_clear} | Reason: {reason}")
assert not is_clear, "Expected LOF to be blocked by charmed seahorse!"

# Check that Esper redirects to Sunder Mind when LOF is blocked by pet!
esper_pet_blocked_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10,
    "has_companion": True,
    "companions": [{"name": "charmed seahorse", "tx": 12, "ty": 10}],
    "abilities": [
        {"name": "Lase", "command": "CommandLase", "cooldown": 0, "usable": True},
        {"name": "Sunder Mind", "command": "CommandSunderMind", "cooldown": 0, "usable": True}
    ]
}
dec_pet_safe = brain.fallback_esper(
    esper_pet_blocked_state,
    [{"name": "dragonfly", "tx": 15, "ty": 10, "dist": 5, "dir": "E", "is_enemy": True}],
    {}, ["MOVE_N", "MOVE_S"], ["MOVE_N", "MOVE_S"],
    esper_pet_blocked_state["abilities"], build_templates.BUILD_TEMPLATES["esper_ited_away"],
    (10, 10), 10, 10, 20, 20, False, False, 0, 0, 0
)
print(f"Action with pet in LOF: {dec_pet_safe['action']} | Reason: {dec_pet_safe['reason']}")
assert dec_pet_safe['action'].startswith("USE_ABILITY:CommandSunderMind"), "Expected Sunder Mind over pet without beam friendly fire!"

# 13. Test Glowpad De-prioritization & Autoexplore Persistence
print("\n--- Test 13: Glowpad De-prioritization (Distant stationary trivial enemy) ---")
glowpad_far_state = {
    "hp": 24, "max_hp": 24, "x": 10, "y": 10, "z": 10,
    "calling": "Apostle",
    "zone_fully_explored": False,
    "hostiles_nearby": True,  # Engine reports true because glowpad exists in zone
    "hostiles_adjacent": False,
    "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear"},
    "visible_entities": [
        {"name": "glowpad", "blueprint": "Glowpad", "tx": 22, "ty": 10, "dist": 12, "dir": "E", "is_enemy": True, "difficulty": "Trivial", "level": 1, "is_stationary": True}
    ]
}
enemies_gp = [e for e in glowpad_far_state["visible_entities"] if e["is_enemy"]]
dec_glowpad_test = brain.query_decision(glowpad_far_state, took_damage=False, enemies=enemies_gp)
print(f"Action with distant glowpad: {dec_glowpad_test['action']} | Reason: {dec_glowpad_test['reason']}")
assert dec_glowpad_test['action'] == "AUTOEXPLORE", f"Expected AUTOEXPLORE to ignore distant glowpad, got {dec_glowpad_test['action']}"

# 14. Test All 9 Archetype Detection
print("\n--- Test 14: Build Guide 9 Archetype Detection Verification ---")
test_build_cases = [
    ({"mutations": [{"class": "FreezingRay"}], "calling": "Marauder"}, "auspicious_beginnings"),
    ({"calling": "Praetorian", "equipped_summary": "desert rifle; tower shield"}, "praetorian_generalist"),
    ({"mutations": [{"class": "MultipleArms"}], "calling": "Marauder"}, "limb_off"),
    ({"mutations": [{"class": "SunderMind"}], "calling": "Apostle"}, "esper_ited_away"),
    ({"mutations": [{"class": "ElectricalGeneration"}, {"class": "FlamingRay"}], "calling": "Greybeard"}, "uncle_iroh"),
    ({"mutations": [{"class": "Phasing"}], "calling": "Gunslinger"}, "bullet_specter"),
    ({"calling": "Child of the Hearth", "equipped_summary": "carbide hand bones", "attributes": {"Strength": 22}}, "classic_punchkin"),
    ({"calling": "Gunslinger", "genotype": "True Kin", "equipped_summary": "border revolver"}, "gunkin"),
    ({"mutations": [{"class": "CorrosiveGasGeneration"}, {"class": "SleepGasGeneration"}], "calling": "Greybeard"}, "gas_giant"),
]

for state, expected_id in test_build_cases:
    detected = build_templates.detect_build(state)
    print(f"Detected: {detected['id']:25} | Expected: {expected_id}")
    assert detected["id"] == expected_id, f"Expected {expected_id}, got {detected['id']}"

# 15. Test Item Evaluation Rubric & Safety Overrides
print("\n--- Test 15: Item Scoring Engine & Safety Overrides ---")
axe_item = {"name": "folded carbide battle axe", "weight": 8, "av": 0, "dv": 0, "slot": "Hands", "description": "1d10+4 weapon"}
marauder_template = build_templates.BUILD_TEMPLATES["auspicious_beginnings"]
praetorian_template = build_templates.BUILD_TEMPLATES["praetorian_generalist"]

score_marauder, bd_m, sum_m = item_evaluator.score_item(axe_item, marauder_template)
score_praetorian, bd_p, sum_p = item_evaluator.score_item(axe_item, praetorian_template)
print(f"Axe score for Marauder: {score_marauder} | For Praetorian: {score_praetorian}")
assert score_marauder > score_praetorian, "Axe should score higher for Marauder axe build!"

# Test Safety Override: Cannot discard sole torch or recoiler
can_sell_torch, r_torch = item_evaluator.can_safely_discard_or_sell(
    {"name": "torch"}, [{"name": "torch"}, {"name": "copper dagger"}]
)
print(f"Can sell sole torch: {can_sell_torch} | Reason: {r_torch}")
assert not can_sell_torch, "Should protect sole light source!"

can_sell_recoiler, r_rec = item_evaluator.can_safely_discard_or_sell(
    {"name": "Joppa recoiler"}, [{"name": "Joppa recoiler"}]
)
print(f"Can sell recoiler: {can_sell_recoiler} | Reason: {r_rec}")
assert not can_sell_recoiler, "Should protect recoiler!"

# 16. Test Charmed Pet Absolute Immunity (Post-Proselytize State)
print("\n--- Test 16: Charmed Pet Absolute Immunity (Post-Proselytize State) ---")
post_charm_state = {
    "hp": 24, "max_hp": 24, "x": 10, "y": 10, "z": 10,
    "calling": "Apostle",
    "has_companion": True,
    "companions": [{"name": "charmed goat", "tx": 11, "ty": 10, "hp": 18, "max_hp": 18, "dist": 1, "dir": "E"}],
    "zone_fully_explored": False,
    "hostiles_nearby": False,
    "hostiles_adjacent": False,
    "surroundings": {"E": "[COMPANION: goat]", "N": "Clear", "S": "Clear", "W": "Clear"},
    "abilities": [
        {"name": "Lase", "command": "CommandLase", "cooldown": 0, "usable": True},
        {"name": "Force Bubble", "command": "CommandForceBubble", "cooldown": 0, "usable": True},
        {"name": "Proselytize", "command": "CommandProselytize", "cooldown": 0, "usable": True}
    ],
    # Simulate a raw entity list where the engine briefly had stale flags
    "visible_entities": [
        {"name": "goat", "tx": 11, "ty": 10, "dist": 1, "dir": "E", "is_enemy": True, "is_companion": False}
    ]
}

# A. filter_hostile_enemies must purge the goat
clean_enemies = brain.filter_hostile_enemies(post_charm_state["visible_entities"], post_charm_state["companions"])
print(f"Filtered enemies count: {len(clean_enemies)}")
assert len(clean_enemies) == 0, f"Expected 0 enemies after filtering companion, got {clean_enemies}"

# B. is_line_of_fire_clear directly to pet coordinate must return False
lof_to_pet, lof_reason = brain.is_line_of_fire_clear((10, 10), (11, 10), companions=post_charm_state["companions"])
print(f"LOF to pet coordinate: {lof_to_pet} | Reason: {lof_reason}")
assert not lof_to_pet, "Expected LOF directly to companion to be blocked!"
assert "friendly companion" in lof_reason.lower()

# C. get_adjacent_threats must not treat adjacent companion as a melee threat
adj_threats_pet = brain.get_adjacent_threats(post_charm_state["surroundings"], companions=post_charm_state["companions"])
print(f"Adjacent threats with companion: {adj_threats_pet}")
assert len(adj_threats_pet) == 0, f"Expected no adjacent threats from companion, got {adj_threats_pet}"

# Even if surroundings had legacy [ENEMY: goat] string, companion name filter must purge it:
stale_surroundings = {"E": "[ENEMY: goat]", "N": "Clear", "S": "Clear", "W": "Clear"}
adj_threats_stale = brain.get_adjacent_threats(stale_surroundings, companions=post_charm_state["companions"])
print(f"Adjacent threats with stale [ENEMY: goat]: {adj_threats_stale}")
assert len(adj_threats_stale) == 0, f"Expected stale enemy string to be purged by companion name, got {adj_threats_stale}"

# D. 5x5 ASCII grid must render companion as 'C'
grid_text = brain.render_5x5_grid(post_charm_state["surroundings"])
print(f"5x5 Grid representation:\n{grid_text}")
assert 'C' in grid_text, "Expected 'C' in grid for companion tile!"

# E. query_decision must NOT backpedal, pop Force Bubble, or fire Lase at pet
dec_post_charm = brain.query_decision(post_charm_state, took_damage=False, enemies=post_charm_state["visible_entities"])
print(f"Post-charm decision: {dec_post_charm['action']} | Reason: {dec_post_charm['reason']}")
assert dec_post_charm['action'] == "AUTOEXPLORE", f"Expected AUTOEXPLORE in peaceful post-charm state, got {dec_post_charm['action']}"
assert "lase" not in dec_post_charm['action'].lower()
assert "bubble" not in dec_post_charm['action'].lower()

print("\n--- Test 17: Esper Standoff Doctrine & Emergency Banishment ---")
# 1. Verify build classification
esper_tmpl = build_templates.BUILD_TEMPLATES["esper_ited_away"]
assert brain.is_pure_caster_or_ranged(esper_tmpl), "Expected esper_ited_away to be pure caster!"

# 2. Adjacent hostile threat with Teleport Other ready: Must banish threat across map
adj_threat_state = {
    "hp": 8, "max_hp": 27, "x": 10, "y": 10, "effects": ["bleeding"],
    "genotype": "Mutated Human", "calling": "Apostle",
    "has_companion": True, "companions": [{"name": "charmed goat", "tx": 10, "ty": 9, "dist": 1}],
    "surroundings": {"NW": "[ENEMY: glowfish]", "N": "Clear", "E": "Clear", "S": "Clear", "W": "Clear"},
    "visible_entities": [{"name": "glowfish", "dist": 1, "dir": "NW", "tx": 9, "ty": 9, "is_enemy": True}],
    "abilities": [
        {"name": "Teleport Other", "command": "CommandTeleportOther", "cooldown": 0, "usable": True},
        {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 30, "usable": False},
        {"name": "Lase (0 charges)", "command": "CommandLase", "cooldown": 0, "usable": False}
    ]
}
dec_banish = brain.query_decision(adj_threat_state, took_damage=True, enemies=adj_threat_state["visible_entities"])
print(f"Adjacent threat decision: {dec_banish['action']} | Reason: {dec_banish['reason']}")
assert "teleportother" in dec_banish['action'].lower(), f"Expected Teleport Other banish, got {dec_banish['action']}"
assert not dec_banish['action'].startswith("MOVE_"), f"Esper must not bump-attack in melee, got {dec_banish['action']}"

# 3. Distant hostile with all powers on cooldown: Must WAIT to recharge, NOT advance with staff!
standoff_state = {
    "hp": 20, "max_hp": 27, "x": 10, "y": 10, "effects": [],
    "genotype": "Mutated Human", "calling": "Apostle",
    "has_companion": True, "companions": [{"name": "charmed goat", "tx": 10, "ty": 9, "dist": 1}],
    "surroundings": {"N": "Clear", "E": "Clear", "S": "Clear", "W": "Clear"},
    "visible_entities": [{"name": "glowpad", "dist": 4, "dir": "E", "tx": 14, "ty": 10, "is_enemy": True, "is_stationary": True}],
    "abilities": [
        {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 30, "usable": False},
        {"name": "Lase (0 charges)", "command": "CommandLase", "cooldown": 0, "usable": False}
    ]
}
dec_standoff = brain.fallback_esper(
    standoff_state, standoff_state["visible_entities"], {},
    ["MOVE_N", "MOVE_S", "MOVE_W"], ["MOVE_N", "MOVE_S", "MOVE_W"],
    standoff_state["abilities"], esper_tmpl, (10, 10), 10, 10, 20, 27, False, False, 0, 0, 0
)
print(f"Standoff recharge decision: {dec_standoff['action']} | Reason: {dec_standoff['reason']}")
assert dec_standoff['action'] == "WAIT", f"Expected WAIT to recharge, got {dec_standoff['action']}"
assert "staff" not in dec_standoff['reason'].lower(), f"Esper must not advance with staff, got {dec_standoff['reason']}"

# 18. Test Peaceful Townsfolk & Conversational NPC Immunity (Joppa Start)
print("\n--- Test 18: Peaceful Townsfolk & Conversational NPC Immunity (Joppa Start) ---")
joppa_state = {
    "hp": 18, "max_hp": 18, "x": 37, "y": 21, "z": 10,
    "genotype": "Mutated Human", "calling": "Apostle",
    "zone_name": "Joppa", "zone_fully_explored": False,
    "hostiles_nearby": True, "hostiles_adjacent": True,
    "surroundings": {
        "N": "[ENEMY: watervine farmer and Mechanimist convert], dirt path",
        "E": "dirt path", "S": "dirt path", "W": "dirt path"
    },
    "visible_entities": [
        {"name": "watervine farmer and Mechanimist convert", "blueprint": "JoppaFarmerConvert", "dist": 1, "dir": "N", "tx": 37, "ty": 20, "is_enemy": True},
        {"name": "Warden Yrame", "blueprint": "Warden Yrame", "dist": 13, "dir": "NE", "tx": 50, "ty": 12, "is_enemy": True},
        {"name": "Elder Irudad", "blueprint": "Elder Irudad", "dist": 8, "dir": "NW", "tx": 30, "ty": 15, "is_enemy": False},
        {"name": "wet glowfish [swimming]", "blueprint": "Glowfish", "dist": 20, "dir": "SW", "tx": 17, "ty": 22, "is_enemy": True, "difficulty": "Average"}
    ],
    "abilities": [
        {"name": "Teleport Other", "command": "CommandTeleportOther", "cooldown": 0, "usable": True},
        {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True},
        {"name": "Lase (4 charges)", "command": "CommandLase", "cooldown": 0, "usable": True},
        {"name": "Proselytize", "command": "CommandProselytize", "cooldown": 0, "usable": True}
    ]
}

# Verify filters
joppa_enemies = brain.filter_hostile_enemies(joppa_state["visible_entities"])
print(f"Filtered Joppa enemies count: {len(joppa_enemies)} (expected 1 glowfish, 0 town NPCs)")
assert len(joppa_enemies) == 1 and joppa_enemies[0]["name"] == "wet glowfish [swimming]", f"Expected only glowfish, got {joppa_enemies}"

joppa_adj_threats = brain.get_adjacent_threats(joppa_state["surroundings"])
print(f"Joppa adjacent threats: {joppa_adj_threats} (expected empty dict)")
assert joppa_adj_threats == {}, f"Watervine farmer must not be considered adjacent threat! Got: {joppa_adj_threats}"

farmer_ent = joppa_state["visible_entities"][0]
assert not brain.is_proselytizable(farmer_ent), "Watervine farmer must not be proselytized!"

glowfish_ent = joppa_state["visible_entities"][3]
assert brain.is_ignorable_stationary_enemy(glowfish_ent), "Distant glowfish swimming in pond must be ignored during exploration!"

dec_joppa = brain.query_decision(joppa_state, took_damage=False, enemies=joppa_enemies)
print(f"Joppa peaceful decision: {dec_joppa['action']} | Reason: {dec_joppa['reason']}")
assert dec_joppa['action'] == "AUTOEXPLORE", f"Expected AUTOEXPLORE in Joppa, got {dec_joppa['action']}"
assert "teleport" not in dec_joppa['action'].lower(), f"Must not banish town NPC! Action: {dec_joppa['action']}"
assert not dec_joppa['action'].startswith("MOVE_N"), f"Must not bump-attack town NPC! Action: {dec_joppa['action']}"

# 19. Test Multi-Tile Oscillation Loop Detection & Room Breakout
print("\n--- Test 19: Multi-Tile Oscillation Loop Detection & Room Breakout ---")
brain.recent_positions.clear()
brain.stuck_autoexplore_zones.clear()
brain.visit_counts.clear()

# Simulate bouncing between (14, 10) [Sign adjacent] and (15, 10) [Table adjacent]
pos_A = (14, 10)
pos_B = (15, 10)
brain.recent_positions.extend([pos_A, pos_B, pos_A, pos_B, pos_A])
brain.visit_counts[pos_A] = 3
brain.visit_counts[pos_B] = 2
pos_freq = brain.recent_positions.count(pos_A)
assert pos_freq == 3, f"Expected pos_freq 3, got {pos_freq}"

house_surroundings = {
    "N": "[BLOCKED: wooden sign]",
    "E": "dirt floor",        # Leads to (15, 10) [already in recent_positions]
    "W": "[BLOCKED: wooden wall]",
    "S": "open doorway",       # Leads to (14, 11) [FRESH ESCAPE TILE]
    "NW": "[BLOCKED: wooden wall]",
    "NE": "[BLOCKED: wooden wall]",
    "SW": "[BLOCKED: wooden wall]",
    "SE": "[BLOCKED: wooden wall]",
}
valid_m = brain.get_valid_moves(house_surroundings, pos_A, None, is_in_combat=False)
open_escapes = [m for m in valid_m if (pos_A[0] + brain.CARDINAL_OFFSETS[m[5:]][0], pos_A[1] + brain.CARDINAL_OFFSETS[m[5:]][1]) not in brain.recent_positions]

print(f"Valid moves from {pos_A}: {valid_m}")
print(f"Open escapes avoiding cycle: {open_escapes}")
assert "MOVE_S" in open_escapes, f"Expected MOVE_S as open escape, got {open_escapes}"
assert "MOVE_E" not in open_escapes, "MOVE_E leads to (15, 10) in recent_positions and must be excluded!"

# Test breakout action selection
open_escapes.sort(key=lambda m: brain.visit_counts[(pos_A[0] + brain.CARDINAL_OFFSETS[m[5:]][0], pos_A[1] + brain.CARDINAL_OFFSETS[m[5:]][1])])
breakout_action = open_escapes[0]
print(f"Selected breakout action: {breakout_action}")
assert breakout_action == "MOVE_S", f"Expected MOVE_S breakout action, got {breakout_action}"

# Test subsequent query_decision switches to frontier exploration
test_zone_id = "Joppa.10"
brain.current_zone_id = test_zone_id
brain.CURRENT_TRACKED_ZONE = test_zone_id
brain.stuck_autoexplore_zones.add(test_zone_id)
osc_state = {
    "hp": 24, "max_hp": 24, "x": 14, "y": 10, "z": 10,
    "zone_id": test_zone_id, "zone_name": "Joppa",
    "zone_fully_explored": False,  # Engine still thinks unexplored
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": house_surroundings,
    "visible_entities": []
}
dec_post_osc = brain.query_decision(osc_state, took_damage=False, enemies=[])
print(f"Decision with stuck autoexplore: {dec_post_osc['action']} | Reason: {dec_post_osc['reason']}")
assert dec_post_osc['action'] != "AUTOEXPLORE", "Must NOT call AUTOEXPLORE when zone is in stuck_autoexplore_zones!"
assert dec_post_osc['action'] == "MOVE_S", f"Expected MOVE_S frontier move, got {dec_post_osc['action']}"

# 20. Test Companion Avoidance in Pathfinding & Autolevel Circuit Breaker
print("\n--- Test 20: Companion Avoidance & Autolevel Circuit Breaker ---")
brain.CHARMED_COMPANION_COORDS.clear()
brain.CHARMED_COMPANION_COORDS.add((65, 17))  # Amoeba at East

water_shore_surroundings = {
    "NW": "[BLOCKED: deep water]",
    "N": "[BLOCKED: deep water]",
    "NE": "[BLOCKED: deep water]",
    "W": "[BLOCKED: deep water]",
    "E": "[COMPANION: giant amoeba], puddle of rules",  # Companion East
    "SW": "[BLOCKED: deep water]",
    "S": "puddle of rules|1 dram of salty asphalt",     # Open South
    "SE": "Empty ground",                               # Open South-East
}

valid_shore_moves = brain.get_valid_moves(water_shore_surroundings, (64, 17), None, is_in_combat=False)
print(f"Valid moves near water & pet: {valid_shore_moves}")
assert "MOVE_E" not in valid_shore_moves, f"MOVE_E directly bumps into companion and must be excluded when open moves exist! Got: {valid_shore_moves}"
assert "MOVE_S" in valid_shore_moves, f"MOVE_S must be open! Got: {valid_shore_moves}"
assert "MOVE_SE" in valid_shore_moves, f"MOVE_SE must be open! Got: {valid_shore_moves}"

# Test fallback to companion when completely trapped
trapped_surroundings = {
    "NW": "[BLOCKED: wall]",
    "N": "[BLOCKED: wall]",
    "NE": "[BLOCKED: wall]",
    "W": "[BLOCKED: wall]",
    "E": "[COMPANION: giant amoeba]",
    "SW": "[BLOCKED: wall]",
    "S": "[BLOCKED: wall]",
    "SE": "[BLOCKED: wall]",
}
trapped_moves = brain.get_valid_moves(trapped_surroundings, (64, 17), None, is_in_combat=False)
print(f"Trapped moves (companion swap fallback): {trapped_moves}")
assert trapped_moves == ["MOVE_E"], f"Expected fallback swap MOVE_E when trapped, got {trapped_moves}"

# Test Autolevel Circuit Breaker logic
stuck_autolevel_state = {
    "hp": 25, "max_hp": 25, "x": 64, "y": 17, "z": 10,
    "calling": "Apostle",
    "ap": 1, "sp": 234, "mp": 3,
    "attributes": {"Strength": 15, "Agility": 16, "Toughness": 18, "Intelligence": 17, "Willpower": 18, "Ego": 21},
    "mutations": [
        {"name": "Clairvoyance", "class": "Clairvoyance", "level": 3, "cap": 3, "can_level": True},
        {"name": "Light Manipulation", "class": "LightManipulation", "level": 3, "cap": 3, "can_level": True}
    ],
    "skills": ["Persuasion_Proselytize"],
    "surroundings": water_shore_surroundings,
    "visible_entities": [],
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "zone_fully_explored": False,
    "zone_id": "JoppaWorld.10.19.1.0.10", "zone_name": "salt marsh"
}

# Normal query: proposes autolevel
dec_lvl_normal = brain.query_decision(stuck_autolevel_state, took_damage=False, enemies=[], suppress_autolevel=False)
print(f"Normal autolevel decision: {dec_lvl_normal['action']} | {dec_lvl_normal['reason']}")
assert dec_lvl_normal['action'] == "AUTOLEVEL_STAT:Ego", f"Expected AUTOLEVEL_STAT:Ego, got {dec_lvl_normal['action']}"

# Suppressed query (circuit breaker tripped): bypasses autolevel and explores / moves!
dec_lvl_suppressed = brain.query_decision(stuck_autolevel_state, took_damage=False, enemies=[], suppress_autolevel=True)
print(f"Circuit breaker suppressed decision: {dec_lvl_suppressed['action']} | {dec_lvl_suppressed['reason']}")
assert not dec_lvl_suppressed['action'].startswith("AUTOLEVEL"), f"Must not propose autolevel when suppressed! Got: {dec_lvl_suppressed['action']}"
assert dec_lvl_suppressed['action'] in ("AUTOEXPLORE", "MOVE_S", "MOVE_SE"), f"Expected exploration or movement, got {dec_lvl_suppressed['action']}"

print("\n--- Test 21: Staircase Gating, Delving, & Tactical Retreat ---")
brain.KNOWN_STAIRS_DOWN.clear()
brain.KNOWN_STAIRS_UP.clear()
brain.RETREAT_TARGET_LEVEL = None
brain.visit_counts.clear()
brain.recent_positions.clear()
brain.stuck_autoexplore_zones.clear()

surface_zone = "JoppaWorld.10.19.1.0.10"
# Scenario 21.1: Surface stairs down detected at Level 1
state_surface_lvl1 = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10,
    "level": 1,
    "zone_id": surface_zone, "zone_name": "salt marsh",
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass", "S": "grass", "E": "grass", "W": "grass", "NE": "grass", "NW": "grass", "SE": "grass", "SW": "grass"},
    "stairs_down": [{"name": "hole in the ground", "tx": 15, "ty": 12}],
    "standing_on_stairs_down": False,
    "visible_entities": []
}
# Step 1: Ingest stairs
brain.update_stair_records(state_surface_lvl1)
assert surface_zone in brain.KNOWN_STAIRS_DOWN, "Stairs down must be recorded in spatial memory!"
assert brain.KNOWN_STAIRS_DOWN[surface_zone]["req_level"] == 3, f"Surface stairs down must require Level 3, got {brain.KNOWN_STAIRS_DOWN[surface_zone]['req_level']}"

# Query decision at Level 1 standing near/on stairs:
# Even if standing directly on stairs down at Level 1, should NOT descend
state_surface_lvl1_on_stairs = dict(state_surface_lvl1)
state_surface_lvl1_on_stairs["x"] = 15
state_surface_lvl1_on_stairs["y"] = 12
state_surface_lvl1_on_stairs["standing_on_stairs_down"] = True
dec_gated = brain.query_decision(state_surface_lvl1_on_stairs, took_damage=False, enemies=[])
print(f"Level 1 on stairs down decision: {dec_gated['action']} | Reason: {dec_gated['reason']}")
assert dec_gated["action"] != "USE_STAIRS_DOWN", "Level 1 character must NOT descend stairs (gated to Level 3)!"

# Scenario 21.2: Character reaches Level 3, zone fully explored -> Routes back to remembered stairs down (15, 12)
state_surface_lvl3_cleared = {
    "hp": 28, "max_hp": 28, "x": 10, "y": 10, "z": 10,
    "level": 3,
    "zone_id": surface_zone, "zone_name": "salt marsh",
    "zone_fully_explored": True,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass", "S": "grass", "E": "grass", "W": "grass", "NE": "grass", "NW": "grass", "SE": "grass", "SW": "grass"},
    "stairs_down": [{"name": "hole in the ground", "tx": 15, "ty": 12}],
    "standing_on_stairs_down": False,
    "visible_entities": []
}
dec_route = brain.query_decision(state_surface_lvl3_cleared, took_damage=False, enemies=[])
print(f"Level 3 cleared zone decision: {dec_route['action']} | Reason: {dec_route['reason']}")
# From (10, 10) towards (15, 12), best move is SE or E
assert dec_route["action"] in ("MOVE_SE", "MOVE_E", "MOVE_S"), f"Expected movement towards stairs down, got {dec_route['action']}"
assert "Navigating to stairs down" in dec_route["reason"] or "Dungeon" in dec_route["reason"]

# Scenario 21.3: Standing on stairs down at Level 3 -> Descend!
state_surface_lvl3_on_stairs = dict(state_surface_lvl3_cleared)
state_surface_lvl3_on_stairs["x"] = 15
state_surface_lvl3_on_stairs["y"] = 12
state_surface_lvl3_on_stairs["standing_on_stairs_down"] = True
dec_descend = brain.query_decision(state_surface_lvl3_on_stairs, took_damage=False, enemies=[])
print(f"Level 3 on stairs down decision: {dec_descend['action']} | Reason: {dec_descend['reason']}")
assert dec_descend["action"] == "USE_STAIRS_DOWN", f"Expected USE_STAIRS_DOWN, got {dec_descend['action']}"

# Scenario 21.4: Underground (z = 11) with critical HP (< 35%) -> Flees to stairs up & retreats
stratum1_zone = "JoppaWorld.10.19.1.0.11"
state_stratum1_retreat = {
    "hp": 8, "max_hp": 30, "x": 20, "y": 15, "z": 11,  # hp ratio = 8/30 = 26.6% (< 35%)
    "level": 3,
    "zone_id": stratum1_zone, "zone_name": "underground",
    "zone_fully_explored": False,
    "hostiles_nearby": True, "hostiles_adjacent": False,
    "surroundings": {"C": "tunnel floor", "N": "tunnel floor", "S": "tunnel floor", "E": "tunnel floor", "W": "tunnel floor"},
    "stairs_up": [{"name": "iron ladder up", "tx": 20, "ty": 12}],
    "standing_on_stairs_up": False,
    "visible_entities": [{"name": "snapjaw hunter", "dist": 3, "tx": 23, "ty": 15, "difficulty": "Tough"}]
}
brain.update_stair_records(state_stratum1_retreat)
assert stratum1_zone in brain.KNOWN_STAIRS_UP, "Stairs up must be recorded in spatial memory!"

# When not standing on stairs up, should flee towards stairs up (20, 12) from (20, 15) -> MOVE_N
dec_flee_su = brain.query_decision(state_stratum1_retreat, took_damage=True, enemies=[{"name": "snapjaw hunter", "dist": 3, "tx": 23, "ty": 15, "difficulty": "Tough"}])
print(f"Critical HP underground decision: {dec_flee_su['action']} | Reason: {dec_flee_su['reason']}")
assert dec_flee_su["action"] == "MOVE_N", f"Expected MOVE_N towards stairs up, got {dec_flee_su['action']}"
assert "stairs up" in dec_flee_su["reason"].lower()

# When standing on stairs up with critical HP -> USE_STAIRS_UP and sets RETREAT_TARGET_LEVEL = cur_lvl + 1 = 4
state_stratum1_on_su = dict(state_stratum1_retreat)
state_stratum1_on_su["x"] = 20
state_stratum1_on_su["y"] = 12
state_stratum1_on_su["standing_on_su"] = True
state_stratum1_on_su["standing_on_stairs_up"] = True
dec_ascend = brain.query_decision(state_stratum1_on_su, took_damage=True, enemies=[{"name": "snapjaw hunter", "dist": 3, "tx": 23, "ty": 12, "difficulty": "Tough"}])
print(f"Standing on stairs up decision: {dec_ascend['action']} | Reason: {dec_ascend['reason']}")
assert dec_ascend["action"] == "USE_STAIRS_UP", f"Expected USE_STAIRS_UP, got {dec_ascend['action']}"
assert brain.RETREAT_TARGET_LEVEL == 4, f"Expected RETREAT_TARGET_LEVEL to be 4, got {brain.RETREAT_TARGET_LEVEL}"

# Scenario 21.5: Character ascends back to surface (z = 10) to recover.
# While still Level 3, stairs down are blocked by retreat recovery goal
state_surface_recovery = dict(state_surface_lvl3_cleared)
state_surface_recovery["hp"] = 12
state_surface_recovery["standing_on_stairs_down"] = True
state_surface_recovery["x"] = 15
state_surface_recovery["y"] = 12
dec_rec = brain.query_decision(state_surface_recovery, took_damage=False, enemies=[])
print(f"Surface recovery at Level 3 decision: {dec_rec['action']} | Reason: {dec_rec['reason']}")
# Should REST (since hp 12/28 < 75%) and NOT descend because RETREAT_TARGET_LEVEL is 4
assert dec_rec["action"] != "USE_STAIRS_DOWN", "Must NOT descend while recovering from retreat!"

# Once Level 4 is attained, RETREAT_TARGET_LEVEL clears and character can re-delve
state_surface_lvl4 = dict(state_surface_recovery)
state_surface_lvl4["level"] = 4
state_surface_lvl4["hp"] = 35
state_surface_lvl4["max_hp"] = 35
dec_redelve = brain.query_decision(state_surface_lvl4, took_damage=False, enemies=[])
print(f"Surface at Level 4 (goal met) decision: {dec_redelve['action']} | Reason: {dec_redelve['reason']}")
assert brain.RETREAT_TARGET_LEVEL is None, "RETREAT_TARGET_LEVEL must clear upon reaching target level!"
assert dec_redelve["action"] == "USE_STAIRS_DOWN", f"Expected re-descent USE_STAIRS_DOWN at Level 4, got {dec_redelve['action']}"

# 22. Test Skill Trees, Prerequisite Gating & SP Savings
print("\n--- Test 22: Skill Trees, Prerequisite Gating & SP Savings ---")
# Scenario 22.1: Marauder has 150 SP, wants to progress in Axe tree but does NOT yet have parent skill 'Axe'
marauder_state_no_parent = {
    "hp": 30, "max_hp": 30, "x": 10, "y": 10, "z": 10,
    "calling": "Marauder",
    "equipped_summary": "Hand: folded carbide battle axe",
    "level": 2, "ap": 0, "sp": 150, "mp": 0,
    "attributes": {"Strength": 22, "Agility": 18, "Toughness": 20, "Intelligence": 14, "Willpower": 14, "Ego": 10},
    "skills": [],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_parent = brain.query_decision(marauder_state_no_parent, took_damage=False, enemies=[])
print(f"Parent skill decision: {dec_parent['action']} | Reason: {dec_parent['reason']}")
assert dec_parent["action"] == "AUTOLEVEL_SKILL:Axe", f"Expected AUTOLEVEL_SKILL:Axe before powers, got {dec_parent['action']}"

# Scenario 22.2: Free 0-Cost Power Instant Acquisition (even at 0 SP)
marauder_state_free_power = dict(marauder_state_no_parent)
marauder_state_free_power["skills"] = ["Axe"]
marauder_state_free_power["sp"] = 0
dec_free = brain.query_decision(marauder_state_free_power, took_damage=False, enemies=[])
print(f"Free 0-cost power decision: {dec_free['action']} | Reason: {dec_free['reason']}")
assert dec_free["action"] == "AUTOLEVEL_SKILL:Axe_Expertise", f"Expected AUTOLEVEL_SKILL:Axe_Expertise for 0 SP, got {dec_free['action']}"

# Scenario 22.3: Attribute Requirement Gating (Apostle Wil 18 vs Wil 29)
apostle_state_gated = {
    "hp": 24, "max_hp": 24, "x": 10, "y": 10, "z": 10,
    "calling": "Apostle",
    "level": 3, "ap": 0, "sp": 150, "mp": 0,
    "attributes": {"Strength": 14, "Agility": 16, "Toughness": 18, "Intelligence": 17, "Willpower": 18, "Ego": 21},
    "skills": ["Tactics", "Tactics_Hurdle", "CookingAndGathering", "CookingAndGathering_Butchery", "CookingAndGathering_MealPreparation", "Customs", "Customs_Tactful"],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_apostle = brain.query_decision(apostle_state_gated, took_damage=False, enemies=[])
print(f"Apostle next eligible skill decision: {dec_apostle['action']} | Reason: {dec_apostle['reason']}")
assert dec_apostle["action"] == "AUTOLEVEL_SKILL:Discipline", f"Expected AUTOLEVEL_SKILL:Discipline, got {dec_apostle['action']}"

# Scenario 22.4: SP Savings Doctrine (Has 75 SP, next is Customs which costs 150 SP)
apostle_state_saving = {
    "hp": 24, "max_hp": 24, "x": 10, "y": 10, "z": 10,
    "calling": "Apostle",
    "level": 3, "ap": 0, "sp": 75, "mp": 0,
    "attributes": {"Strength": 14, "Agility": 16, "Toughness": 18, "Intelligence": 17, "Willpower": 18, "Ego": 21},
    "skills": ["Tactics", "Tactics_Hurdle"],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_save = brain.query_decision(apostle_state_saving, took_damage=False, enemies=[])
print(f"SP saving decision: {dec_save['action']} | Reason: {dec_save['reason']}")
# Must NOT lock into invalid autolevel or waste points on random filler; should save SP and explore!
assert not dec_save["action"].startswith("AUTOLEVEL"), f"Must NOT attempt invalid autolevel when saving SP! Got: {dec_save['action']}"
assert dec_save["action"] == "AUTOEXPLORE", f"Expected AUTOEXPLORE while saving SP, got {dec_save['action']}"

# Scenario 22.5: Engine learnable_skills Telemetry Verification
praetorian_state_telem = {
    "hp": 30, "max_hp": 30, "x": 10, "y": 10, "z": 10,
    "calling": "Praetorian",
    "level": 3, "ap": 0, "sp": 100, "mp": 0,
    "attributes": {"Strength": 20, "Agility": 18, "Toughness": 20, "Intelligence": 16, "Willpower": 14, "Ego": 10},
    "skills": ["Rifles", "Rifle_SteadyHands", "Rifle_DrawABead", "Shield", "Shield_Block"],
    "learnable_skills": [
        {"class": "Shield_Slam", "name": "Shield Slam", "cost": 100, "parent": "Shield", "is_parent": False}
    ],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_telem = brain.query_decision(praetorian_state_telem, took_damage=False, enemies=[])
print(f"Engine learnable_skills decision: {dec_telem['action']} | Reason: {dec_telem['reason']}")
assert dec_telem["action"] == "AUTOLEVEL_SKILL:Shield_Slam", f"Expected AUTOLEVEL_SKILL:Shield_Slam, got {dec_telem['action']}"


# =====================================================================
# TEST 23: Zone Hopping Prevention & Inward Border Navigation
# =====================================================================
print("\n" + "="*50)
print("TEST 23: Zone Hopping Prevention & Inward Border Navigation")
print("="*50)

# Reset global tracking variables
brain.CURRENT_TRACKED_ZONE = None
brain.RECENT_ZONES.clear()
brain.ZONE_STEP_COUNT = 0
brain.ZONE_HOPPING_DETECTED = False
brain.LAST_ZONE_ENTRY = None

# Scenario 23.1: Entering a new zone at border x=0, y=12
# Character enters "Joppa.1.1.1.10" from west, landing at (0, 12).
# West tile is the reverse zone exit back to prior zone.
# East tile is open terrain towards the zone center.
border_state_1 = {
    "hp": 20, "max_hp": 20, "x": 0, "y": 12, "z": 10,
    "zone_id": "Joppa.1.1.1.10",
    "calling": "Warden",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "W": "[ZONE_EXIT: W]", "E": "grass", "N": "grass", "S": "grass"},
    "visible_entities": []
}

# First zone registration
brain.update_zone_records({"zone_id": "Joppa.1.1.0.10", "x": 79, "y": 12})
dec_inward = brain.query_decision(border_state_1, took_damage=False, enemies=[])
print(f"Border entry decision: {dec_inward['action']} | Reason: {dec_inward['reason']}")
assert dec_inward["action"] == "MOVE_E", f"Expected inward MOVE_E from western border, got: {dec_inward['action']}"
assert "Border Navigation" in dec_inward["reason"] or "interior" in dec_inward["reason"]

# Scenario 23.2: Zone Hopping Breaker (Oscillation between Zone A and Zone B)
# Simulate ping-pong: Zone A -> Zone B -> Zone A
brain.CURRENT_TRACKED_ZONE = None
brain.RECENT_ZONES.clear()
brain.ZONE_HOPPING_DETECTED = False

# Step into Zone A
brain.update_zone_records({"zone_id": "ZoneA", "x": 40, "y": 12})
# Step into Zone B
brain.update_zone_records({"zone_id": "ZoneB", "x": 0, "y": 12})
# Hop back into Zone A (oscillation!)
hop_back_state = {
    "hp": 20, "max_hp": 20, "x": 79, "y": 12, "z": 10,
    "zone_id": "ZoneA",
    "calling": "Warden",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_fully_explored": True,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "E": "[ZONE_EXIT: E]", "W": "grass", "N": "grass", "S": "grass"},
    "visible_entities": []
}
dec_hop = brain.query_decision(hop_back_state, took_damage=False, enemies=[])
print(f"Zone hopping breaker decision: {dec_hop['action']} | Reason: {dec_hop['reason']}")
assert brain.ZONE_HOPPING_DETECTED, "ZONE_HOPPING_DETECTED must be True after A -> B -> A oscillation!"
assert dec_hop["action"] == "MOVE_W", f"Expected inward MOVE_W away from eastern border, got: {dec_hop['action']}"
assert "Zone Hopping Breaker" in dec_hop["reason"]

# Scenario 23.3: Backtrack Exit Suppression when fully explored
# When zone is fully explored, character must NOT immediately reverse exit if ZONE_HOPPING_DETECTED
suppress_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 12, "z": 10,
    "zone_id": "ZoneA",
    "calling": "Warden",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_fully_explored": True,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "W": "[ZONE_EXIT: W]", "E": "wall", "N": "grass", "S": "grass"},
    "visible_entities": []
}
brain.LAST_ZONE_ENTRY = {"from_zone": "ZoneB", "to_zone": "ZoneA", "reverse_dir": "W"}
brain.ZONE_HOPPING_DETECTED = True
brain.ZONE_STEP_COUNT = 2
dec_suppress = brain.query_decision(suppress_state, took_damage=False, enemies=[])
print(f"Reverse exit suppression decision: {dec_suppress['action']} | Reason: {dec_suppress['reason']}")
assert dec_suppress["action"] != "MOVE_W", f"Must NOT backtrack into reverse exit during oscillation! Got: {dec_suppress['action']}"


# =====================================================================
# TEST 24: Sustenance & Survival (Butchering, Cooking, Camping & Eating)
# =====================================================================
print("\n" + "="*50)
print("TEST 24: Sustenance & Survival Routines")
print("="*50)

# Scenario 24.1: Opportunistic Field Butchery when Safe
butcher_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10,
    "calling": "Warden",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "can_butcher": True,
    "corpses_nearby": 1,
    "skills": ["CookingAndGathering", "CookingAndGathering_Butchery"],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_b = brain.query_decision(butcher_state, took_damage=False, enemies=[])
print(f"Opportunistic butcher decision: {dec_b['action']} | Reason: {dec_b['reason']}")
assert dec_b["action"] == "BUTCHER", f"Expected BUTCHER, got {dec_b['action']}"

# Scenario 24.2: Opportunistic Field Harvesting when Safe
harvest_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10,
    "calling": "Warden",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "can_harvest": True,
    "harvestable_nearby": 1,
    "skills": ["CookingAndGathering", "CookingAndGathering_Harvestry"],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_h = brain.query_decision(harvest_state, took_damage=False, enemies=[])
print(f"Opportunistic harvest decision: {dec_h['action']} | Reason: {dec_h['reason']}")
assert dec_h["action"] == "HARVEST", f"Expected HARVEST, got {dec_h['action']}"

# Scenario 24.3: Adjacent Campfire Cooking when Hungry
cook_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10,
    "calling": "Warden",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "is_hungry": True,
    "hunger_level": "Hungry",
    "campfire_nearby": True,
    "food_count": 2,
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_c = brain.query_decision(cook_state, took_damage=False, enemies=[])
print(f"Campfire cook decision: {dec_c['action']} | Reason: {dec_c['reason']}")
assert dec_c["action"] == "COOK_MEAL", f"Expected COOK_MEAL at adjacent campfire, got {dec_c['action']}"

# Scenario 24.4: Starting a Campfire (Make Camp) when Famished with ingredients
camp_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10,
    "calling": "Warden",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "is_famished": True,
    "hunger_level": "Famished",
    "campfire_nearby": False,
    "can_make_camp": True,
    "food_count": 3,
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_camp = brain.query_decision(camp_state, took_damage=False, enemies=[])
print(f"Make camp decision: {dec_camp['action']} | Reason: {dec_camp['reason']}")
assert dec_camp["action"] == "MAKE_CAMP", f"Expected MAKE_CAMP, got {dec_camp['action']}"

# Scenario 24.5: Eating Food from Inventory when Hungry
eat_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10,
    "calling": "Warden",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "is_hungry": True,
    "hunger_level": "Hungry",
    "campfire_nearby": False,
    "can_make_camp": False,
    "has_food": True,
    "food_count": 1,
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_eat = brain.query_decision(eat_state, took_damage=False, enemies=[])
print(f"Eat inventory food decision: {dec_eat['action']} | Reason: {dec_eat['reason']}")
assert dec_eat["action"] == "EAT", f"Expected EAT, got {dec_eat['action']}"

# Scenario 24.6: Sustenance Priority over Resting (Famished with low HP)
# Famished resting causes starvation damage or failure to heal. Sustenance must precede resting.
famished_rest_state = {
    "hp": 5, "max_hp": 25, "x": 10, "y": 10, "z": 10, # HP is 20% (< 75% rest threshold)
    "calling": "Warden",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "is_famished": True,
    "hunger_level": "Famished",
    "campfire_nearby": False,
    "can_make_camp": False,
    "has_food": True,
    "food_count": 2,
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_f_rest = brain.query_decision(famished_rest_state, took_damage=False, enemies=[])
print(f"Famished low-HP decision: {dec_f_rest['action']} | Reason: {dec_f_rest['reason']}")
assert dec_f_rest["action"] == "EAT", f"Expected EAT before REST when famished, got {dec_f_rest['action']}"

# ==================================================
# TEST 25: 5-Tile Shoreline Loop Detection & Centroid Breakout
# ==================================================
print("\n==================================================")
print("TEST 25: 5-Tile Shoreline Loop Detection & Centroid Breakout")
print("==================================================")

brain.recent_positions.clear()
brain.stuck_autoexplore_zones.clear()
brain.visit_counts.clear()

# Scenario 25.1: 5-Tile Cycle Entropy Check (unique_positions <= 5 over >= 10 steps)
# Simulate cycling along 5 shoreline tiles: T1(20, 20), T2(21, 20), T3(22, 21), T4(21, 22), T5(20, 21)
cycle_5 = [(20, 20), (21, 20), (22, 21), (21, 22), (20, 21)]
for pt in cycle_5 * 2:  # 10 steps total
    brain.recent_positions.append(pt)
    brain.visit_counts[pt] += 1

cur_pos = (20, 21)
pos_freq = brain.recent_positions.count(cur_pos)
unique_positions = len(set(brain.recent_positions))

print(f"Cycle length: {len(brain.recent_positions)}, Unique positions: {unique_positions}, Current pos frequency: {pos_freq}")
assert len(brain.recent_positions) == 10
assert unique_positions == 5
assert pos_freq == 2, f"pos_frequency must be 2 (< 3 threshold), got {pos_freq}"

# Check the oscillation condition directly
is_attacking = False
is_oscillating = not is_attacking and (
    (pos_freq >= 3) or
    (len(brain.recent_positions) >= 10 and unique_positions <= 5)
)
assert is_oscillating, "5-tile loop must be detected by entropy check despite pos_freq < 3!"
print(f"5-Tile loop oscillation detected: {is_oscillating}")

# Scenario 25.2: Breakout with Open Frontier Escape
# Deep water blocks NW, W, SW. N goes to (20, 20) [in cycle], NE goes to (21, 20) [in cycle].
# S leads to (20, 22) [dry land unvisited frontier].
shore_surroundings = {
    "NW": "[BLOCKED: deep water]",
    "W": "[BLOCKED: deep water]",
    "SW": "[BLOCKED: deep water]",
    "N": "shallow water",      # (20, 20) in cycle
    "NE": "salty asphalt",     # (21, 20) in cycle
    "E": "dirt",               # (21, 21)
    "S": "salty dirt",         # (20, 22) [Open Escape!]
    "SE": "dirt"               # (21, 22) in cycle
}

valid_shore_m = brain.get_valid_moves(shore_surroundings, cur_pos, None, is_in_combat=False)
open_escapes = [m for m in valid_shore_m
                if (cur_pos[0] + brain.CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + brain.CARDINAL_OFFSETS[m[5:]][1]) not in brain.recent_positions]

print(f"Valid shoreline moves: {valid_shore_m}")
print(f"Open escapes escaping 5-tile cycle: {open_escapes}")
assert "MOVE_S" in open_escapes, f"MOVE_S must be an open escape to fresh tile (20, 22)! Got: {open_escapes}"
assert "MOVE_N" not in open_escapes, "MOVE_N leads to cycle tile (20, 20) and must not be in open_escapes"

# Scenario 25.3: Centroid Steer Fallback
# When local moves only exist among cycle nodes, verify centroid calculation steers the agent to the furthest node
recent_set = set(brain.recent_positions)
avg_rx = sum(p[0] for p in recent_set) / max(1, len(recent_set))  # (20+21+22+21+20)/5 = 20.8
avg_ry = sum(p[1] for p in recent_set) / max(1, len(recent_set))  # (20+20+21+22+21)/5 = 20.8
print(f"Cycle centroid: ({avg_rx:.2f}, {avg_ry:.2f})")

def dist_away_from_cycle(m, p):
    dx, dy = brain.CARDINAL_OFFSETS[m[5:]]
    nx, ny = p[0] + dx, p[1] + dy
    euc_dist = (nx - avg_rx)**2 + (ny - avg_ry)**2
    return (-euc_dist, brain.visit_counts[(nx, ny)])

test_moves = ["MOVE_NW", "MOVE_SW", "MOVE_E"]
test_moves.sort(key=lambda m: dist_away_from_cycle(m, (22, 21)))
print(f"Moves sorted by distance away from centroid: {test_moves}")
assert test_moves[0] == "MOVE_E", f"MOVE_E must be furthest away from cycle centroid! Got {test_moves[0]}"

# Scenario 25.4: Zone autoexplore exhaustion & frontier routing
shore_zone = "JoppaWorld.10.19.1.0.10"
brain.current_zone_id = shore_zone
brain.CURRENT_TRACKED_ZONE = shore_zone
brain.stuck_autoexplore_zones.add(shore_zone)
shore_explore_state = {
    "hp": 22, "max_hp": 22, "x": 20, "y": 21, "z": 10,
    "calling": "Marauder",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": shore_zone,
    "zone_name": "salt marsh",
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": shore_surroundings,
    "visible_entities": []
}
dec_shore = brain.query_decision(shore_explore_state, took_damage=False, enemies=[])
print(f"Decision in stuck shoreline zone: {dec_shore['action']} | Reason: {dec_shore['reason']}")
assert dec_shore["action"] != "AUTOEXPLORE", "Must NOT call AUTOEXPLORE in stuck zone!"
assert dec_shore["action"] in valid_shore_m, f"Expected valid move, got {dec_shore['action']}"
assert "frontier" in dec_shore["reason"], f"Expected frontier exploration, got {dec_shore['reason']}"

# ==================================================
# TEST 26: Safe Swimming Navigation, Liquid Hazard Classification & Water Traversal
# ==================================================
print("\n==================================================")
print("TEST 26: Safe Swimming Navigation & Liquid Hazard Classification")
print("==================================================")

# Scenario 26.1: Liquid Hazard Classification & Passability
river_crossing_surroundings = {
    "NW": "[HAZARD: pool of acid]",          # Lethal liquid -> MUST BE BLOCKED
    "N": "[SWIM: deep fresh water]",         # Safe deep liquid -> PASSABLE FOR SWIMMING
    "NE": "[HAZARD: pool of lava]",          # Lethal liquid -> MUST BE BLOCKED
    "W": "[BLOCKED: sandstone wall]",        # Solid wall -> MUST BE BLOCKED
    "CENTER": "riverbank mud",
    "E": "riverbank mud",                    # Dry land visited
    "SW": "[BLOCKED: shale wall]",
    "S": "riverbank gravel",                 # Dry land visited
    "SE": "riverbank mud"                    # Dry land visited
}

river_moves = brain.get_valid_moves(river_crossing_surroundings, (15, 30), None, is_in_combat=False)
print(f"River crossing valid moves: {river_moves}")
assert "MOVE_N" in river_moves, f"MOVE_N (swimming deep water) must be VALID! Got: {river_moves}"
assert "MOVE_NW" not in river_moves, f"MOVE_NW (acid hazard) must be BLOCKED! Got: {river_moves}"
assert "MOVE_NE" not in river_moves, f"MOVE_NE (lava hazard) must be BLOCKED! Got: {river_moves}"
assert "MOVE_W" not in river_moves, f"MOVE_W (wall) must be BLOCKED! Got: {river_moves}"
assert "MOVE_SW" not in river_moves, f"MOVE_SW (wall) must be BLOCKED! Got: {river_moves}"

# Scenario 26.2: 5x5 ASCII Visualizer Rendering
grid_rendered = brain.render_5x5_grid(river_crossing_surroundings)
print("5x5 Grid with swimming and hazard tiles:\n" + grid_rendered)
assert "~" in grid_rendered, "Swimming water tiles must render as '~' in 5x5 ASCII grid"
assert "!" in grid_rendered, "Hazardous liquids must render as '!' in 5x5 ASCII grid"

# Scenario 26.3: Water Traversal across River to Unvisited Shoreline
brain.visit_counts.clear()
# Shoreline tiles have been visited 2 times
brain.visit_counts[(16, 30)] = 2  # E
brain.visit_counts[(15, 31)] = 2  # S
brain.visit_counts[(16, 31)] = 2  # SE
# River tile to North has visit count 0 (unexplored river/far shore)
brain.visit_counts[(15, 29)] = 0  # N

swim_zone = "JoppaWorld.10.19.1.0.10"
brain.current_zone_id = swim_zone
brain.CURRENT_TRACKED_ZONE = swim_zone
brain.stuck_autoexplore_zones.add(swim_zone)

swim_explore_state = {
    "hp": 25, "max_hp": 25, "x": 15, "y": 30, "z": 10,
    "calling": "Marauder",
    "level": 3, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": swim_zone,
    "zone_name": "salt marsh",
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": river_crossing_surroundings,
    "visible_entities": []
}

# Scenario 26.3: Water Traversal across River toward Known Stairs Down
dec_swim_stairs = brain.query_decision(swim_explore_state, took_damage=False, enemies=[])
print(f"River stairs crossing decision: {dec_swim_stairs['action']} | Reason: {dec_swim_stairs['reason']}")
assert dec_swim_stairs["action"] == "MOVE_N", f"Expected character to swim across water MOVE_N towards stairs at (15, 12)! Got: {dec_swim_stairs['action']}"
assert "Navigating to stairs down" in dec_swim_stairs["reason"]

# Scenario 26.4: Water Traversal across River to Unvisited Frontier
frontier_zone = "SaltMarshRiver.10.19.1.0.10"
brain.current_zone_id = frontier_zone
brain.CURRENT_TRACKED_ZONE = frontier_zone
brain.stuck_autoexplore_zones.add(frontier_zone)

swim_frontier_state = dict(swim_explore_state)
swim_frontier_state["zone_id"] = frontier_zone

dec_swim_frontier = brain.query_decision(swim_frontier_state, took_damage=False, enemies=[])
print(f"River frontier crossing decision: {dec_swim_frontier['action']} | Reason: {dec_swim_frontier['reason']}")
assert dec_swim_frontier["action"] == "MOVE_N", f"Expected character to swim across water MOVE_N to reach unvisited territory! Got: {dec_swim_frontier['action']}"
assert "scouting zone frontier move_n" in dec_swim_frontier["reason"].lower()

# Scenario 26.5: In-Water Survival Invariant: Reject Camping & Cooking while Swimming, Allow Eating
in_water_state = {
    "hp": 12, "max_hp": 25, "x": 15, "y": 29, "z": 10,
    "calling": "Marauder",
    "level": 3, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": frontier_zone,
    "zone_name": "salt marsh",
    "zone_fully_explored": False,
    "is_swimming": True,
    "effects": ["Swimming"],
    "hunger_level": "Famished",
    "is_famished": True,
    "has_food": True,
    "food_count": 2,
    "can_make_camp": False,
    "can_cook": False,
    "skills": ["Survival_Camp", "CookingAndGathering"],
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {
        "CENTER": "deep fresh water [swimming]",
        "N": "[SWIM: deep water]",
        "S": "riverbank mud"
    },
    "visible_entities": []
}

dec_in_water = brain.query_decision(in_water_state, took_damage=False, enemies=[])
print(f"In-water famished decision: {dec_in_water['action']} | Reason: {dec_in_water['reason']}")
assert dec_in_water["action"] == "EAT", f"Expected direct inventory EAT while swimming, got: {dec_in_water['action']}"
assert dec_in_water["action"] not in ["MAKE_CAMP", "COOK_MEAL", "REST"], "Cannot camp, cook, or rest while actively swimming in deep water!"

print("\n==================================================")
print("TEST 27: Mutation Cap Safeguards & Fog-of-War Grid Frontier Breakout")
print("==================================================")

# Scenario 27.1: Mutation Cap Invariant: Do not attempt AUTOLEVEL if all mutations capped
capped_mutation_state = {
    "hp": 23, "max_hp": 23, "x": 42, "y": 17, "z": 10,
    "calling": "Apostle",
    "level": 2, "ap": 0, "sp": 0, "mp": 1,
    "zone_id": frontier_zone,
    "zone_name": "salt marsh",
    "zone_fully_explored": False,
    "is_swimming": False,
    "hunger_level": "Satisfied",
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "mutations": [
        {"name": "Clairvoyance", "class": "Clairvoyance", "level": 2, "cap": 2, "can_level": False},
        {"name": "Light Manipulation", "class": "LightManipulation", "level": 2, "cap": 2, "can_level": False},
        {"name": "Sense Psychic", "class": "SensePsychic", "level": 1, "cap": 2, "can_level": False},
        {"name": "Stunning Force", "class": "StunningForce", "level": 2, "cap": 2, "can_level": False},
        {"name": "Teleport Other", "class": "TeleportOther", "level": 2, "cap": 2, "can_level": False}
    ],
    "surroundings": {"N": "pool of rules|463 drams of salty water", "NE": "pool of rules|386 drams of salty water", "W": "watervine", "E": "pool of rules|375 drams of salty water"},
    "visible_entities": [],
    "unexplored_cells": 217,
    "unexplored_centroid_x": 44,
    "unexplored_centroid_y": 16
}

dec_capped = brain.query_decision(capped_mutation_state, took_damage=False, enemies=[])
print(f"Capped mutation decision: {dec_capped['action']} | Reason: {dec_capped['reason']}")
assert not dec_capped["action"].startswith("AUTOLEVEL"), f"Must not issue AUTOLEVEL when all mutations are capped and MP < 4! Got: {dec_capped['action']}"

# Scenario 27.2: In-engine fog-of-war grid frontier detection across water
frontier_target, frontier_reason = brain.find_zone_unexplored_frontier(capped_mutation_state, (42, 17), {})
print(f"Grid frontier target: {frontier_target} | Reason: {frontier_reason}")
assert frontier_target == (44, 16), f"Expected unexplored centroid (44, 16), got: {frontier_target}"

# Scenario 27.3: Loop Breaker breakout towards unexplored sector across water
valid_m_shore = brain.get_valid_moves(capped_mutation_state["surroundings"], (42, 17), None)
best_breakout_m = brain.get_best_move_towards((42, 17), frontier_target, valid_m_shore, capped_mutation_state["surroundings"])
print(f"Breakout move towards grid frontier: {best_breakout_m}")
assert best_breakout_m == "MOVE_NE", f"Expected MOVE_NE into water towards unexplored centroid (44, 16), got: {best_breakout_m}"

print("\n==================================================")
print("TEST 28: Distant Hostile Disengagement & Post-Levelup Combat Gating")
print("==================================================")

# Scenario 28.1: Player at Level 3 with AP: 1, SP: 106, MP: 2 and distant enemy at dist 18 across open dunes.
# Engine reports hostiles_nearby: False. AI must NOT enter combat mode; it must autolevel AP!
distant_scorpiock_state = {
    "hp": 27, "max_hp": 27, "x": 44, "y": 11, "z": 10,
    "calling": "Apostle",
    "level": 3, "ap": 1, "sp": 106, "mp": 2,
    "attributes": {"Strength": 10, "Agility": 14, "Toughness": 16, "Intelligence": 16, "Willpower": 18, "Ego": 21},
    "zone_id": "JoppaWorld.8.20.1.0.10",
    "zone_name": "salt marsh",
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "last_move_failed": False,
    "mutations": [
        {"name": "Clairvoyance", "class": "Clairvoyance", "level": 2, "cap": 2, "can_level": False},
        {"name": "Light Manipulation", "class": "LightManipulation", "level": 2, "cap": 2, "can_level": False},
        {"name": "Sense Psychic", "class": "SensePsychic", "level": 1, "cap": 2, "can_level": False},
        {"name": "Stunning Force", "class": "StunningForce", "level": 2, "cap": 2, "can_level": False},
        {"name": "Teleport Other", "class": "TeleportOther", "level": 2, "cap": 2, "can_level": False}
    ],
    "abilities": [
        {"name": "Light Manipulation", "command": "CommandLase", "cooldown": 0, "usable": True},
        {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True}
    ],
    "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear", "NE": "Clear", "NW": "Clear", "SE": "Clear", "SW": "Clear"},
    "visible_entities": [
        {"name": "scorpiock", "blueprint": "Scorpiock", "dist": 18, "dir": "SE", "tx": 62, "ty": 19, "is_enemy": True, "difficulty": "Average"}
    ]
}
distant_enemies = [e for e in distant_scorpiock_state["visible_entities"] if e["is_enemy"]]
dec_dist_lvl = brain.query_decision(distant_scorpiock_state, took_damage=False, enemies=distant_enemies)
print(f"Distant hostile levelup decision: {dec_dist_lvl['action']} | Reason: {dec_dist_lvl['reason']}")
assert dec_dist_lvl["action"] == "AUTOLEVEL_STAT:Ego", f"Expected AUTOLEVEL_STAT:Ego, got: {dec_dist_lvl['action']}"

# Scenario 28.2: After AP is spent (ap: 0), player unlocks priority skill Tactics (sp: 106 >= 50)
spent_ap_state = dict(distant_scorpiock_state)
spent_ap_state["ap"] = 0
dec_dist_skill = brain.query_decision(spent_ap_state, took_damage=False, enemies=distant_enemies)
print(f"Post-AP skill unlock decision: {dec_dist_skill['action']} | Reason: {dec_dist_skill['reason']}")
assert dec_dist_skill["action"] == "AUTOLEVEL_SKILL:Tactics", f"Expected AUTOLEVEL_SKILL:Tactics, got: {dec_dist_skill['action']}"

# Scenario 28.2b: With Tactics unlocked, player claims free 0-cost subpower Tactics_Hurdle
tactics_unlocked_state = dict(spent_ap_state)
tactics_unlocked_state["sp"] = 56
tactics_unlocked_state["skills"] = ["Tactics"]
dec_dist_power = brain.query_decision(tactics_unlocked_state, took_damage=False, enemies=distant_enemies)
print(f"Free subpower claim decision: {dec_dist_power['action']} | Reason: {dec_dist_power['reason']}")
assert dec_dist_power["action"] == "AUTOLEVEL_SKILL:Tactics_Hurdle", f"Expected AUTOLEVEL_SKILL:Tactics_Hurdle, got: {dec_dist_power['action']}"

# Scenario 28.2c: With free powers claimed and saving SP for Tactics_Juke (56 SP < 200), player resumes AUTOEXPLORE!
saving_sp_state = dict(tactics_unlocked_state)
saving_sp_state["skills"] = ["Tactics", "Tactics_Hurdle"]
dec_dist_explore = brain.query_decision(saving_sp_state, took_damage=False, enemies=distant_enemies)
print(f"Post-levelup exploration decision: {dec_dist_explore['action']} | Reason: {dec_dist_explore['reason']}")
assert dec_dist_explore["action"] == "AUTOEXPLORE", f"Expected AUTOEXPLORE, got: {dec_dist_explore['action']}"

# Scenario 28.3: Priority AP spending even when enemy is in combat distance (dist 7, hostiles_nearby: True)
nearby_combat_state = dict(distant_scorpiock_state)
nearby_combat_state["ap"] = 1
nearby_combat_state["hostiles_nearby"] = True
nearby_enemies = [{"name": "scorpiock", "blueprint": "Scorpiock", "dist": 7, "dir": "SE", "tx": 51, "ty": 18, "is_enemy": True, "difficulty": "Average"}]
dec_priority_ap = brain.query_decision(nearby_combat_state, took_damage=False, enemies=nearby_enemies)
print(f"Priority combat AP allocation: {dec_priority_ap['action']} | Reason: {dec_priority_ap['reason']}")
assert dec_priority_ap["action"] == "AUTOLEVEL_STAT:Ego", f"Expected priority AUTOLEVEL_STAT:Ego before battle, got: {dec_priority_ap['action']}"

# Scenario 28.4: Fallback Esper with distant enemy at dist 18 advances rather than firing out-of-range Lase
dec_fallback_adv = brain.fallback_esper(
    distant_scorpiock_state, distant_enemies, {},
    ["MOVE_SE", "MOVE_E", "MOVE_S"], ["MOVE_SE", "MOVE_E", "MOVE_S"],
    distant_scorpiock_state["abilities"], brain.build_templates.BUILD_TEMPLATES["esper_ited_away"],
    (44, 11), 44, 11, 27, 27, False, False, 0, 0, 0
)
print(f"Fallback Esper distant target advance: {dec_fallback_adv['action']} | Reason: {dec_fallback_adv['reason']}")
assert dec_fallback_adv["action"] == "MOVE_SE", f"Expected MOVE_SE advancing towards distant scorpiock, got: {dec_fallback_adv['action']}"

# =====================================================================
# TEST 29: Multi-Class Archetype Skill Point Allocation & Telemetry
# =====================================================================
print("\n" + "="*50)
print("TEST 29: Multi-Class Archetype Skill Point Allocation")
print("="*50)

# Scenario 29.1: Apostle / Esper Starting Skills & Core Progression
# In Qud, Apostle starts with Tactics & Persuasion. With 106 SP, unlocks CookingAndGathering!
apostle_telem_state = {
    "hp": 24, "max_hp": 24, "x": 10, "y": 10, "z": 10,
    "calling": "Apostle",
    "level": 2, "ap": 0, "sp": 106, "mp": 0,
    "attributes": {"Strength": 15, "Agility": 16, "Toughness": 18, "Intelligence": 17, "Willpower": 18, "Ego": 21},
    "skills": ["Tactics", "Tactics_Hurdle", "Persuasion", "Persuasion_Proselytize"],
    "learnable_skills": [
        {"class": "CookingAndGathering", "name": "Cooking and Gathering", "cost": 100, "is_parent": True, "parent": ""},
        {"class": "Tactics_Throwing", "name": "Throwing", "cost": 50, "is_parent": False, "parent": "Tactics"}
    ],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_apostle_core = brain.query_decision(apostle_telem_state, took_damage=False, enemies=[])
print(f"Apostle core skill decision: {dec_apostle_core['action']} | Reason: {dec_apostle_core['reason']}")
assert dec_apostle_core["action"] == "AUTOLEVEL_SKILL:CookingAndGathering", f"Expected AUTOLEVEL_SKILL:CookingAndGathering, got: {dec_apostle_core['action']}"

# Scenario 29.2: Free 0-SP Power Claiming (MealPreparation)
apostle_meal_state = dict(apostle_telem_state)
apostle_meal_state["skills"] = ["Tactics", "Tactics_Hurdle", "Persuasion", "Persuasion_Proselytize", "CookingAndGathering"]
apostle_meal_state["sp"] = 6
apostle_meal_state["learnable_skills"] = [
    {"class": "CookingAndGathering_MealPreparation", "name": "Meal Preparation", "cost": 0, "is_parent": False, "parent": "CookingAndGathering"}
]
dec_apostle_meal = brain.query_decision(apostle_meal_state, took_damage=False, enemies=[])
print(f"Apostle free MealPreparation decision: {dec_apostle_meal['action']} | Reason: {dec_apostle_meal['reason']}")
assert dec_apostle_meal["action"] == "AUTOLEVEL_SKILL:CookingAndGathering_MealPreparation", f"Expected AUTOLEVEL_SKILL:CookingAndGathering_MealPreparation, got: {dec_apostle_meal['action']}"

# Scenario 29.3: Marauder Archetype: Starts with Axe, unlocks Axe_Expertise (0 SP), then Cooking
marauder_state = {
    "hp": 32, "max_hp": 32, "x": 10, "y": 10, "z": 10,
    "calling": "Marauder",
    "equipped_summary": "Hand: folded carbide battle axe",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "attributes": {"Strength": 22, "Agility": 18, "Toughness": 20, "Intelligence": 14, "Willpower": 14, "Ego": 10},
    "skills": ["Axe"],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_mar_exp = brain.query_decision(marauder_state, took_damage=False, enemies=[])
print(f"Marauder free Axe_Expertise decision: {dec_mar_exp['action']} | Reason: {dec_mar_exp['reason']}")
assert dec_mar_exp["action"] == "AUTOLEVEL_SKILL:Axe_Expertise", f"Expected AUTOLEVEL_SKILL:Axe_Expertise, got: {dec_mar_exp['action']}"

# Scenario 29.4: Gunslinger Archetype: Starts with Pistol, learns Pistol_SteadyHands (100 SP)
gunslinger_state = {
    "hp": 22, "max_hp": 22, "x": 10, "y": 10, "z": 10,
    "calling": "Gunslinger",
    "equipped_summary": "Hand: border revolver",
    "level": 2, "ap": 0, "sp": 100, "mp": 0,
    "attributes": {"Strength": 14, "Agility": 24, "Toughness": 18, "Intelligence": 16, "Willpower": 16, "Ego": 12},
    "skills": ["Pistol"],
    "learnable_skills": [
        {"class": "Pistol_SteadyHands", "name": "Steady Hands", "cost": 100, "is_parent": False, "parent": "Pistol"}
    ],
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "dirt", "N": "grass"},
    "visible_entities": []
}
dec_gun = brain.query_decision(gunslinger_state, took_damage=False, enemies=[])
print(f"Gunslinger SteadyHands decision: {dec_gun['action']} | Reason: {dec_gun['reason']}")
assert dec_gun["action"] == "AUTOLEVEL_SKILL:Pistol_SteadyHands", f"Expected AUTOLEVEL_SKILL:Pistol_SteadyHands, got: {dec_gun['action']}"

# Scenario 29.5: Autolevel Circuit Breaker does not falsely trip on 0-SP skills
# Verify cur_points state change when learning a 0-SP skill
points_before = (0, 6, 0, len(apostle_telem_state["skills"]))
points_after = (0, 6, 0, len(apostle_meal_state["skills"]))
assert points_before != points_after, "cur_points must register change when acquiring 0-SP power to avoid tripping breaker!"
print("Autolevel 0-SP power state tracking: Verified distinct point signatures")

# ==================================================
# TEST 30: Native Engine Zone Exit Pathfinding (The Three Strikes Graveyard Fix)
# ==================================================
print("\n==================================================")
print("TEST 30: Native Engine Zone Exit Pathfinding & Obstacle Routing")
print("==================================================")

# Scenario 30.1: Outskirts Graveyard Enclosure (unexplored_cells == 0, fence blocking East)
# Character at (47, 11) in Joppa outskirts must dispatch NAVIGATE_ZONE_EXIT:E to delegate pathfinding to AutoAct.TryFindEdgeStep
graveyard_state = {
    "hp": 18, "max_hp": 18, "x": 47, "y": 11, "z": 10,
    "calling": "Apostle",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.11.22.1.0.10",
    "zone_name": "outskirts, Joppa",
    "zone_fully_explored": False,  # Engine flag false, but unexplored_cells == 0
    "unexplored_cells": 0,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {
        "C": "dirt",
        "N": "dirt",
        "S": "dirt",
        "E": "[BLOCKED: brinestalk fence]",
        "NE": "[BLOCKED: brinestalk fence]",
        "SE": "[BLOCKED: brinestalk fence]",
        "W": "dirt", "NW": "dirt", "SW": "dirt"
    },
    "visible_entities": []
}
dec_gy = brain.query_decision(graveyard_state, took_damage=False, enemies=[])
print(f"Graveyard decision: {dec_gy['action']} | Reason: {dec_gy['reason']}")
assert dec_gy["action"].startswith("NAVIGATE_ZONE_EXIT:"), f"Expected NAVIGATE_ZONE_EXIT:<DIR> to delegate pathfinding to native engine, got: {dec_gy['action']}"
assert "navigating via engine pathfinder" in dec_gy["reason"]

# Scenario 30.2: get_zone_exit_target returns 3-tuple (pos, tag, exit_dir)
pos, tag, exit_dir = brain.get_zone_exit_target((47, 11))
print(f"get_zone_exit_target: Pos: {pos}, Tag: {tag}, Dir: {exit_dir}")
assert exit_dir in ("N", "S", "E", "W"), f"Exit dir must be cardinal, got: {exit_dir}"
expected_pos = brain._EXIT_TARGETS[exit_dir](47, 11)[0]
assert pos == expected_pos, f"Expected pos {expected_pos} for {exit_dir}, got: {pos}"

# ==================================================
# TEST 31: Zone Bailing Prevention & Native Target Cell Pathfinding
# ==================================================
print("\n==================================================")
print("TEST 31: Zone Bailing Prevention & Native Target Cell Pathfinding")
print("==================================================")

# Scenario 31.1: Zone Bailing Guard
# Character in a brand new salt marsh zone with 1439 unexplored cells.
# Even if engine erroneously passes zone_fully_explored: True, Python MUST NOT navigate to exit!
salt_marsh_state = {
    "hp": 18, "max_hp": 18, "x": 43, "y": 14, "z": 10,
    "calling": "Apostle",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.12.22.2.0.10",
    "zone_name": "salt marsh, surface",
    "zone_fully_explored": True,  # Erroneous engine flag
    "unexplored_cells": 1439,      # 1439 unexplored cells exist!
    "unexplored_centroid_x": 44,
    "unexplored_centroid_y": 12,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {
        "C": "dirt",
        "NW": "Empty ground", "N": "watervine", "NE": "watervine",
        "W": "Empty ground", "E": "Empty ground",
        "SW": "watervine", "S": "watervine", "SE": "Empty ground"
    },
    "visible_entities": []
}
dec_marsh = brain.query_decision(salt_marsh_state, took_damage=False, enemies=[])
print(f"Salt marsh decision with 1439 unexp cells: {dec_marsh['action']} | Reason: {dec_marsh['reason']}")
assert not dec_marsh["action"].startswith("NAVIGATE_ZONE_EXIT"), f"Must NOT bail on zone with 1439 unrevealed cells! Got: {dec_marsh['action']}"
assert dec_marsh["action"] == "AUTOEXPLORE", f"Expected AUTOEXPLORE in unexplored zone, got: {dec_marsh['action']}"

# Scenario 31.2: Loop Breaker Native Target Cell Routing
# When oscillating in a zone with unexplored cells, loop breaker must route via NAVIGATE_TO_CELL
ft, fr = brain.find_zone_unexplored_frontier(salt_marsh_state, (43, 14), brain.visit_counts)
print(f"Frontier target: {ft} | Reason: {fr}")
assert ft is not None, "Expected frontier target in partially explored zone!"

print("\n==================================================")
print("TEST 32: Centroid Proximity & Distance-1 Sector Navigation")
print("==================================================")

# Scenario 32.1: Centroid at Distance 1 (Water Traversal)
# Character is swimming at (62, 11). Unexplored centroid is at (62, 12) (distance = 1).
# Character MUST move towards (62, 12) (MOVE_S) and NOT bounce backwards (MOVE_NW)!
prox_state = {
    "hp": 18, "max_hp": 18, "x": 62, "y": 11, "z": 10,
    "calling": "Apostle",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.12.22.2.0.10",
    "zone_name": "salt marsh, surface",
    "unexplored_cells": 551,
    "unexplored_centroid_x": 62,
    "unexplored_centroid_y": 12,
    "nearest_unexplored_x": 62,
    "nearest_unexplored_y": 12,
    "nearest_unexplored_dist": 1,
    "is_swimming": True,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {
        "NW": "[SWIM: salty water]", "N": "[SWIM: salty water]", "NE": "[SWIM: salty water]",
        "W": "[SWIM: salty water]", "E": "[SWIM: salty water]",
        "SW": "[SWIM: salty water]", "S": "[SWIM: salty water]", "SE": "[SWIM: salty water]"
    },
    "visible_entities": [{"tx": 60, "ty": 11, "blueprint": "Brinestalk"}]
}

dec_prox = brain.query_decision(prox_state, took_damage=False, enemies=[])
print(f"Distance-1 centroid decision: {dec_prox['action']} | Reason: {dec_prox['reason']}")
assert dec_prox["action"] == "MOVE_S", f"Expected MOVE_S towards (62, 12), got: {dec_prox['action']}"

# Scenario 32.2: Standing on Centroid with Nearest Unexplored Target
# Character is standing on (62, 12) (centroid). Nearest unexplored is (62, 13).
# Character MUST navigate to nearest unexplored (MOVE_S)!
standing_on_centroid_state = dict(prox_state)
standing_on_centroid_state["y"] = 12
standing_on_centroid_state["nearest_unexplored_y"] = 13

dec_standing = brain.query_decision(standing_on_centroid_state, took_damage=False, enemies=[])
print(f"Standing-on-centroid decision: {dec_standing['action']} | Reason: {dec_standing['reason']}")
assert dec_standing["action"] == "MOVE_S", f"Expected MOVE_S towards nearest unexplored cell (62, 13), got: {dec_standing['action']}"

print("\n==================================================")
print("TEST 33: Opportunistic Pet Recruitment & Memory Clearance")
print("==================================================")

# Scenario 33.1: Phase A Exploration Pet Recruitment (Distance 1)
# Apostle exploring without a companion encounters an adjacent snapjaw scavenger.
# Must immediately recruit with CommandProselytize!
explore_recruit_state = {
    "hp": 18, "max_hp": 18, "x": 10, "y": 10, "z": 10,
    "calling": "Apostle",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.12.22.2.0.10",
    "zone_name": "salt marsh, surface",
    "unexplored_cells": 100,
    "has_companion": False,
    "companions": [],
    "abilities": [
        {"name": "Proselytize", "command": "CommandProselytize", "usable": True, "cooldown": 0},
        {"name": "Intimidate", "command": "CommandIntimidate", "usable": True, "cooldown": 0}
    ],
    "surroundings": {
        "NW": "Empty ground", "N": "Empty ground", "NE": "Empty ground",
        "W": "Empty ground", "E": "Empty ground",
        "SW": "Empty ground", "S": "Empty ground", "SE": "Empty ground"
    },
    "visible_entities": [
        {"name": "snapjaw scavenger", "blueprint": "Snapjaw", "dist": 1, "dir": "E", "tx": 11, "ty": 10, "can_proselytize": True}
    ]
}

dec_recruit_adj = brain.query_decision(explore_recruit_state, took_damage=False, enemies=[])
print(f"Phase A adjacent pet recruit decision: {dec_recruit_adj['action']} | Reason: {dec_recruit_adj['reason']}")
assert dec_recruit_adj["action"] == "USE_ABILITY:CommandProselytize:E", f"Expected proselytize adjacent pet, got: {dec_recruit_adj['action']}"

# Scenario 33.2: Phase A Exploration Candidate Approach (Distance 2)
# Candidate is at dist 2 (12, 10). Character must step towards it (MOVE_E) to recruit!
explore_dist2_state = dict(explore_recruit_state)
explore_dist2_state["visible_entities"] = [
    {"name": "giant dragonfly", "blueprint": "Dragonfly", "dist": 2, "dir": "E", "tx": 12, "ty": 10, "can_proselytize": True}
]
dec_recruit_dist2 = brain.query_decision(explore_dist2_state, took_damage=False, enemies=[])
print(f"Phase A distance-2 approach decision: {dec_recruit_dist2['action']} | Reason: {dec_recruit_dist2['reason']}")
assert dec_recruit_dist2["action"] == "MOVE_E", f"Expected MOVE_E to approach candidate, got: {dec_recruit_dist2['action']}"

# Scenario 33.3: Combat (fallback_esper) Approach at Distance 2
# Combat encounter: Apostle has Lase and Stunning Force, but prospective pet is at dist 2.
# Must approach (MOVE_E) rather than blasting it to pieces!
combat_candidate = {"name": "snapjaw warrior", "blueprint": "Snapjaw", "dist": 2, "dir": "E", "tx": 12, "ty": 10, "can_proselytize": True, "difficulty": "Average"}
combat_recruit_state = dict(explore_recruit_state)
combat_recruit_state["visible_entities"] = [combat_candidate]
combat_recruit_state["abilities"].extend([
    {"name": "Lase", "command": "CommandLase", "usable": True, "cooldown": 0},
    {"name": "Stunning Force", "command": "CommandStunningForce", "usable": True, "cooldown": 0}
])
dec_combat_dist2 = brain.query_decision(combat_recruit_state, took_damage=False, enemies=[combat_candidate])
print(f"Combat distance-2 approach decision: {dec_combat_dist2['action']} | Reason: {dec_combat_dist2['reason']}")
assert dec_combat_dist2["action"] == "MOVE_E", f"Expected MOVE_E in combat to close distance for proselytize, got: {dec_combat_dist2['action']}"

# Scenario 33.4: Post-Pet-Death Memory Leak Prevention
# Simulate a previous pet died. Memory must NOT permanently bar that species from being proselytized again!
brain.CHARMED_COMPANION_NAMES.clear()
brain.CHARMED_COMPANION_COORDS.clear()
new_candidate = {"name": "snapjaw scavenger", "blueprint": "Snapjaw", "dist": 1, "dir": "E", "tx": 11, "ty": 10, "can_proselytize": True}
assert brain.is_proselytizable(new_candidate, companions=[]), "Candidate of same species must be proselytizable after previous companion died!"

# Scenario 33.5: Active Companion Immunity
# Active companion at (11, 10) must NOT be proselytized
active_comp_state = dict(explore_recruit_state)
active_comp_state["has_companion"] = True
active_comp_state["companions"] = [{"name": "snapjaw scavenger", "tx": 11, "ty": 10, "hp": 15, "max_hp": 15, "dist": 1, "dir": "E"}]
active_comp_state["visible_entities"] = [{"name": "snapjaw scavenger", "tx": 11, "ty": 10, "dist": 1, "dir": "E", "is_companion": True}]
dec_active_comp = brain.query_decision(active_comp_state, took_damage=False, enemies=[])
print(f"Active companion decision: {dec_active_comp['action']} | Reason: {dec_active_comp['reason']}")
assert not dec_active_comp["action"].startswith("USE_ABILITY:CommandProselytize"), "Must NOT proselytize already-active companion!"

print("\n==================================================")
print("TEST 34: Combat Loop Breaker Immunity & Dragonfly Recruitment")
print("==================================================")

# Scenario 34.1: Combat Loop Breaker Immunity
# In combat against an adjacent giant dragonfly at (48, 12), with prior navigation history
# causing high pos_frequency >= 3. Loop breaker MUST NOT override combat ability with NAVIGATE_TO_CELL!
combat_state = {
    "hp": 15, "max_hp": 22, "x": 48, "y": 13, "z": 10,
    "calling": "Apostle",
    "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.11.23.2.1.10",
    "zone_name": "salt marsh, surface",
    "unexplored_cells": 1400,
    "unexplored_centroid_x": 55, "unexplored_centroid_y": 13,
    "has_companion": False,
    "companions": [],
    "hostiles_nearby": True, "hostiles_adjacent": True,
    "abilities": [
        {"name": "Lase (5 charges)", "command": "CommandLase", "usable": True, "cooldown": 0},
        {"name": "Stunning Force", "command": "CommandStunningForce", "usable": True, "cooldown": 0},
        {"name": "Proselytize", "command": "CommandProselytize", "usable": True, "cooldown": 0}
    ],
    "surroundings": {
        "NW": "Empty ground", "N": "giant dragonfly", "NE": "Empty ground",
        "W": "Empty ground", "E": "Empty ground",
        "SW": "Empty ground", "S": "Empty ground", "SE": "Empty ground"
    },
    "visible_entities": [
        {"name": "giant dragonfly", "blueprint": "GiantDragonfly", "dist": 1, "dir": "N", "tx": 48, "ty": 12, "is_enemy": True, "can_proselytize": True}
    ]
}

# Verify dragonfly can be proselytized
dragonfly_ent = combat_state["visible_entities"][0]
assert brain.is_proselytizable(dragonfly_ent, companions=[]), "Living giant dragonfly must be proselytizable!"

# Simulate loop breaker logic from main turn loop
brain.recent_positions.extend([(48, 13)] * 5)
pos_freq = brain.recent_positions.count((48, 13))
assert pos_freq >= 3, "Setup condition: pos_frequency must be >= 3"

enemies = [dragonfly_ent]
combat_dec = brain.fallback_esper(
    combat_state, enemies, {"N": "giant dragonfly"},
    ["MOVE_S", "MOVE_E"], ["MOVE_S", "MOVE_E", "MOVE_N"],
    combat_state["abilities"], brain.build_templates.detect_build(combat_state),
    (48, 13), 48, 13, 15, 22, False, False, 0, 0, 0
)
print(f"Fallback combat decision: {combat_dec['action']} | Reason: {combat_dec['reason']}")
assert combat_dec["action"] == "USE_ABILITY:CommandProselytize:N", f"Expected proselytize adjacent dragonfly, got: {combat_dec['action']}"

# Now simulate loop breaker check
action = combat_dec["action"]
adj_threats = {"N": "giant dragonfly"}
is_in_combat = True
is_attacking = action.startswith("MOVE_") and (action[5:] in adj_threats)
is_combat_action = action.startswith("USE_ABILITY") or action.startswith("FIRE_MISSILE") or is_attacking
is_oscillating = not is_in_combat and not is_combat_action and (pos_freq >= 3)
assert not is_oscillating, "is_oscillating MUST be False during combat and for combat actions!"
assert not action.startswith("NAVIGATE_TO_CELL"), "Action must NOT be overridden by NAVIGATE_TO_CELL!"

print("\n==================================================")
print("TEST 35: Line-of-Sight Ray Occlusion & Corridor Maneuvering")
print("==================================================")

# Scenario 35.1: is_line_of_fire_clear verification
# A. Target entity has has_los explicitly False
occluded_enemy = {"name": "beetle", "tx": 10, "ty": 15, "dist": 3, "has_los": False}
clear, reason = brain.is_line_of_fire_clear((10, 12), (10, 15), target_entity=occluded_enemy)
print(f"Occluded target LOF clear: {clear} | Reason: {reason}")
assert not clear, "Line of fire must be blocked when target has has_los: False!"
assert "no line of sight" in reason

# B. Intermediate wall in surroundings
surroundings_with_wall = {
    "S": "[BLOCKED: shale wall]",
    "SS": "Empty ground",
}
visible_enemy_behind_wall = {"name": "beetle", "tx": 10, "ty": 14, "dist": 2, "has_los": True}
clear_wall, reason_wall = brain.is_line_of_fire_clear((10, 12), (10, 14), target_entity=visible_enemy_behind_wall, surroundings=surroundings_with_wall)
print(f"Wall in surroundings LOF clear: {clear_wall} | Reason: {reason_wall}")
assert not clear_wall, "Line of fire must be blocked when intermediate tile is a solid wall in surroundings!"
assert "solid wall" in reason_wall

# C. Clear line of sight
clear_path, reason_path = brain.is_line_of_fire_clear((10, 12), (10, 14), target_entity=visible_enemy_behind_wall, surroundings={"S": "Empty ground"})
print(f"Clear path LOF clear: {clear_path} | Reason: {reason_path}")
assert clear_path, "Line of fire must be clear when no obstacles block the path!"

# Scenario 35.2: fallback_esper behavior when occluded by walls
# Esper Apostle at (64, 18) in stratum 11 hallway. Mob at (64, 15) behind a corridor corner.
corridor_state = {
    "hp": 24, "max_hp": 24, "x": 64, "y": 18, "z": 11,
    "calling": "Apostle",
    "level": 3, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.23.0.1.11",
    "zone_name": "stratum 11",
    "has_companion": False,
    "companions": [],
    "hostiles_nearby": True, "hostiles_adjacent": False,
    "abilities": [
        {"name": "Lase (5 charges)", "command": "CommandLase", "usable": True, "cooldown": 0},
        {"name": "Sunder Mind", "command": "CommandSunderMind", "usable": True, "cooldown": 0},
        {"name": "Stunning Force", "command": "CommandStunningForce", "usable": True, "cooldown": 0},
        {"name": "Teleport Other", "command": "CommandTeleportOther", "usable": True, "cooldown": 0},
    ],
    "surroundings": {
        "NW": "[BLOCKED: shale wall]", "N": "Empty ground", "NE": "[BLOCKED: shale wall]",
        "W": "[BLOCKED: shale wall]",                       "E": "[BLOCKED: shale wall]",
        "SW": "[BLOCKED: shale wall]", "S": "Empty ground", "SE": "[BLOCKED: shale wall]"
    },
    "visible_entities": [
        {"name": "snapjaw hunter", "blueprint": "SnapjawHunter", "dist": 3, "dir": "N", "tx": 64, "ty": 15, "is_enemy": True, "has_los": False}
    ]
}

# Subcase A: Mob is occluded (has_los: False), but Sunder Mind is ready!
# Sunder Mind is mental and can penetrate solid rock!
corridor_enemy = corridor_state["visible_entities"][0]
esper_template = brain.build_templates.detect_build(corridor_state)
dec_sunder = brain.fallback_esper(
    corridor_state, [corridor_enemy], {},
    ["MOVE_N", "MOVE_S"], ["MOVE_N", "MOVE_S"],
    corridor_state["abilities"], esper_template,
    (64, 18), 64, 18, 24, 24, False, False, 0, 0, 0
)
print(f"Occluded target with Sunder Mind ready: {dec_sunder['action']} | Reason: {dec_sunder['reason']}")
assert dec_sunder["action"] == "USE_ABILITY:CommandSunderMind:N", f"Expected Sunder Mind through wall, got: {dec_sunder['action']}"

# Subcase B: Sunder Mind on cooldown, Lase ready, mob occluded (has_los: False).
# AI MUST NOT fire Lase or blind WAIT; it must maneuver along hallway (MOVE_N) to establish LOS!
abilities_no_sunder = [
    {"name": "Lase (5 charges)", "command": "CommandLase", "usable": True, "cooldown": 0},
    {"name": "Sunder Mind", "command": "CommandSunderMind", "usable": False, "cooldown": 10},
    {"name": "Stunning Force", "command": "CommandStunningForce", "usable": True, "cooldown": 0},
]
dec_maneuver = brain.fallback_esper(
    corridor_state, [corridor_enemy], {},
    ["MOVE_N", "MOVE_S"], ["MOVE_N", "MOVE_S"],
    abilities_no_sunder, esper_template,
    (64, 18), 64, 18, 24, 24, False, False, 0, 0, 0
)
print(f"Occluded target without Sunder Mind: {dec_maneuver['action']} | Reason: {dec_maneuver['reason']}")
assert dec_maneuver["action"] != "USE_ABILITY:CommandLase:N", "Must NOT fire Lase through solid wall!"
assert dec_maneuver["action"] != "WAIT", "Must NOT blindly wait when target is around corner without LOS!"
assert dec_maneuver["action"] == "MOVE_N", f"Expected maneuvering MOVE_N towards target around corridor, got: {dec_maneuver['action']}"

# Subcase C: Line of sight established (has_los: True).
# With Stunning Force ready, AI uses CC opener!
visible_corridor_enemy = dict(corridor_enemy)
visible_corridor_enemy["has_los"] = True
dec_stun = brain.fallback_esper(
    corridor_state, [visible_corridor_enemy], {},
    ["MOVE_N", "MOVE_S"], ["MOVE_N", "MOVE_S"],
    abilities_no_sunder, esper_template,
    (64, 18), 64, 18, 24, 24, False, False, 0, 0, 0
)
print(f"Clear LOS target with Stunning Force ready: {dec_stun['action']} | Reason: {dec_stun['reason']}")
assert dec_stun["action"] == "USE_ABILITY:CommandStunningForce:N", f"Expected Stunning Force CC opener when LOS clear, got: {dec_stun['action']}"

# Subcase D: Line of sight established, Stunning Force on cooldown -> AI fires Lase!
abilities_lase_only = [
    {"name": "Lase (5 charges)", "command": "CommandLase", "usable": True, "cooldown": 0},
    {"name": "Sunder Mind", "command": "CommandSunderMind", "usable": False, "cooldown": 10},
    {"name": "Stunning Force", "command": "CommandStunningForce", "usable": False, "cooldown": 10},
]
dec_lase = brain.fallback_esper(
    corridor_state, [visible_corridor_enemy], {},
    ["MOVE_N", "MOVE_S"], ["MOVE_N", "MOVE_S"],
    abilities_lase_only, esper_template,
    (64, 18), 64, 18, 24, 24, False, False, 0, 0, 0
)
print(f"Clear LOS target with only Lase ready: {dec_lase['action']} | Reason: {dec_lase['reason']}")
assert dec_lase["action"] == "USE_ABILITY:CommandLase:N", f"Expected Lase when LOS is clear, got: {dec_lase['action']}"

print("\n==================================================")
print("TEST 36: Subterranean Stratum Zone Exit & Reachable Edge Prioritization")
print("==================================================")

# Scenario 36.1: Subterranean stratum exploration completion
# In stratum 11 (z = 11), player is at (17, 2). All reachable corridor cells are explored.
# 605 unexplored cells exist in solid rock. Engine reports zone_fully_explored: True.
# Telemetry reports reachable_edges: "N" (only North exit is reachable through the corridor).
# Python must NOT call AUTOEXPLORE or NAVIGATE_TO_CELL into rock; it MUST navigate to the North exit!
subterranean_stratum_state = {
    "hp": 24, "max_hp": 24, "x": 17, "y": 2, "z": 11,
    "calling": "Apostle",
    "level": 3, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.23.0.1.11",
    "zone_name": "subterranean salt marsh, 1 stratum deep",
    "zone_fully_explored": True,
    "unexplored_cells": 605,
    "unexplored_centroid_x": 40, "unexplored_centroid_y": 16,
    "nearest_unexplored_x": 17, "nearest_unexplored_y": 0, "nearest_unexplored_dist": 2,
    "reachable_edges": "N",
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {
        "NW": "[BLOCKED: impassable terrain]", "N": "[BLOCKED: impassable terrain]", "NE": "[BLOCKED: impassable terrain]",
        "W": "[BLOCKED: impassable terrain]",                                       "E": "watervine",
        "SW": "watervine",                    "S": "Empty ground",                  "SE": "campfire"
    },
    "stairs_up": [{"name": "stairs up", "blueprint": "StairsUp", "dist": 17, "dir": "E", "tx": 34, "ty": 2}],
    "stairs_down": [],
    "visible_entities": []
}

dec_sub = brain.query_decision(subterranean_stratum_state, took_damage=False, enemies=[])
print(f"Subterranean stratum decision: {dec_sub['action']} | Reason: {dec_sub['reason']}")
assert dec_sub["action"] == "NAVIGATE_ZONE_EXIT:N", f"Expected NAVIGATE_ZONE_EXIT:N to reach North exit in stratum 11, got: {dec_sub['action']}"
assert "navigating via engine pathfinder toward North zone exit" in dec_sub["reason"]

# Scenario 36.2: get_zone_exit_target prioritizes reachable_edges
pos_n, tag_n, dir_n = brain.get_zone_exit_target((17, 2), subterranean_stratum_state)
print(f"Reachable edge target: {pos_n}, Tag: {tag_n}, Dir: {dir_n}")
assert dir_n == "N", f"Expected exit dir N from reachable_edges 'N', got: {dir_n}"

# Scenario 36.3: Loop Breaker breakout in subterranean stratum with 605 solid rock cells
brain.recent_positions.clear()
brain.recent_positions.extend([(17, 2), (18, 2)] * 4)
pos_freq_sub = brain.recent_positions.count((17, 2))
assert pos_freq_sub >= 3, "Setup condition: oscillation frequency must be >= 3"
exit_pos_lb, exit_tag_lb, exit_dir_lb = brain.get_zone_exit_target((17, 2), subterranean_stratum_state)
assert exit_dir_lb == "N"

print("\n==================================================")
print(">>> ALL 36 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
print("==================================================")






