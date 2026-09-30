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
    "skills": ["Tactics", "Tactics_Hurdle", "Customs", "Customs_Tactful"],
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

print("\n==================================================")
print(">>> ALL 22 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
print("==================================================")

