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

print("\n==================================================")
print(">>> ALL 15 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
print("==================================================")
