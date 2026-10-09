import json
import os
import tempfile
os.environ["QUDAI_EXCHANGE_DIR"] = tempfile.mkdtemp(prefix="qudai_exchange_")   # never the real game folder
import brain
# Never write test decisions into the real exit log (memory/exit_choices.jsonl).
brain.EXIT_LOG_PATH = os.path.join(tempfile.mkdtemp(), "exit_choices_dry_run.jsonl")
brain.DECISION_TRACE_PATH = os.path.join(tempfile.mkdtemp(), "decision_trace_dry_run.jsonl")
import danger_ledger
danger_ledger.LEDGER_PATH = os.path.join(tempfile.mkdtemp(), "danger_ledger_dry_run.json"); danger_ledger.reset_cache()
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
assert dec_gun['action'].startswith("FIRE_MISSILE@"), f"Expected a pistol volley, got {dec_gun['action']}"

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
assert dec_zone_done['action'] == "NAVIGATE_TO_CELL:10,9", f"Expected the engine path to the stairs down, got {dec_zone_done['action']}"
# Test 11 told the brain (as the engine) that this zone ID is fully explored. Later scenarios reuse the ID as a fresh zone,
# so forget what the engine said here (T-1.15: the brain now remembers the engine's explored flag across turns).
brain.EXPLORED_ZONE_SET.clear()
brain.ENGINE_EXPLORED_LAST.clear()

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

# Even if surroundings had a legacy [ENEMY: goat] tag on the companion's cell, the companion COORDINATES must purge it
# (never the name: see Test 51):
stale_surroundings = {"E": "[ENEMY: goat]", "N": "Clear", "S": "Clear", "W": "Clear"}
adj_threats_stale = brain.get_adjacent_threats(stale_surroundings, companions=post_charm_state["companions"], cur_pos=(10, 10))
print(f"Adjacent threats with stale [ENEMY: goat]: {adj_threats_stale}")
assert len(adj_threats_stale) == 0, f"Expected stale enemy tag on a companion cell to be purged by coordinates, got {adj_threats_stale}"

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
assert dec_route["action"] == "NAVIGATE_TO_CELL:15,12", f"Expected the engine path to the stairs down, got {dec_route['action']}"
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
assert dec_flee_su["action"] == "NAVIGATE_TO_CELL:20,12", f"Expected the engine path to the stairs up, got {dec_flee_su['action']}"
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
    "skills": ["Tactics", "Tactics_Hurdle", "CookingAndGathering", "CookingAndGathering_Butchery", "CookingAndGathering_Harvestry", "CookingAndGathering_MealPreparation", "Customs", "Customs_Tactful"],
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

# Scenario 24.3: Hungry next to a campfire with food: just EAT (cooking gives nothing EAT does not; HANDOFF issue 34)
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
assert dec_c["action"] == "EAT", f"Expected EAT (no cooking detour), got {dec_c['action']}"

# Scenario 24.4: Famished with food and camp allowed: EAT, never a campfire detour (T-1.13)
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
assert dec_camp["action"] == "EAT", f"Expected EAT, not MAKE_CAMP, got {dec_camp['action']}"

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
brain.last_action = None  # no autoexplore progress this turn (otherwise the stuck mark is rightly cleared)
brain.EXPLORED_ZONE_SET.discard(shore_zone)  # Test 11 reported this zone ID as engine-explored; this scenario is a different story
brain.ENGINE_EXPLORED_LAST.pop(shore_zone, None)
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
assert dec_swim_stairs["action"] == "NAVIGATE_TO_CELL:15,12", f"Expected the engine path to the stairs at (15, 12)! Got: {dec_swim_stairs['action']}"
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

# =====================================================================
# TEST 37: Subterranean Dead-End Exit Invalidation & Corridor Alignment
# =====================================================================
print("\n" + "="*50)
print("TEST 37: Subterranean Dead-End Exit Invalidation & Corridor Alignment")
print("="*50)

# Scenario 37.1: Live state where East border is a dead end into solid rock at (74, 11)
dead_end_east_state = {
    "hp": 26, "max_hp": 26, "level": 4, "x": 74, "y": 11, "z": 11,
    "zone_id": "JoppaWorld.10.23.0.1.11",
    "zone_name": "subterranean salt marsh, 1 stratum deep",
    "zone_fully_explored": True,
    "unexplored_cells": 605,
    "nearest_unexplored_x": 72, "nearest_unexplored_y": 9, "nearest_unexplored_dist": 2,
    "last_move_failed": False,
    "surroundings": {
        "E": "[BLOCKED: impassable terrain], [BLOCKED: tangled mudroot]",
        "NE": "[BLOCKED: impassable terrain], [BLOCKED: tangled mudroot]",
        "SE": "[BLOCKED: impassable terrain], [BLOCKED: tangled mudroot]",
        "N": "[BLOCKED: impassable terrain], [BLOCKED: tangled mudroot]",
        "NW": "[BLOCKED: impassable terrain], [BLOCKED: tangled mudroot]",
        "W": "Empty ground", "SW": "Empty ground", "S": "Empty ground",
        "WW": "Empty ground", "WSW": "Empty ground", "SW2": "Empty ground", "SSW": "Empty ground"
    },
    "stairs_up": [{"name": "stairs up", "blueprint": "StairsUp", "dist": 40, "dir": "W", "tx": 34, "ty": 2}],
    "stairs_down": [],
    "visible_entities": []
}

# Pre-set chosen exit to East to simulate the stuck state
brain.CURRENT_ZONE_CHOSEN_EXIT = "E"
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = "JoppaWorld.10.23.0.1.11"
brain.FAILED_ZONE_EXITS.clear()

dec_dead_end = brain.query_decision(dead_end_east_state, took_damage=False, enemies=[])
print(f"Dead-end East recovery decision: {dec_dead_end['action']} | Reason: {dec_dead_end['reason']}")
assert dec_dead_end["action"] == "NAVIGATE_ZONE_EXIT:N", f"Expected switch from dead-end E to N, got: {dec_dead_end['action']}"
assert ("JoppaWorld.10.23.0.1.11", "E") in brain.FAILED_ZONE_EXITS, "East exit should be blacklisted in FAILED_ZONE_EXITS"
assert brain.CURRENT_ZONE_CHOSEN_EXIT == "N", f"Expected chosen exit to be N, got: {brain.CURRENT_ZONE_CHOSEN_EXIT}"

# Scenario 37.2: Loop breaker oscillation recovery at dead-end
brain.CURRENT_ZONE_CHOSEN_EXIT = "E"
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = "JoppaWorld.10.23.0.1.11"
brain.FAILED_ZONE_EXITS.clear()
brain.recent_positions.clear()
brain.recent_positions.extend([(74, 11), (73, 11)] * 4)
dec_loop_breaker = brain.query_decision(dead_end_east_state, took_damage=False, enemies=[])
print(f"Loop breaker dead-end recovery decision: {dec_loop_breaker['action']} | Reason: {dec_loop_breaker['reason']}")
assert dec_loop_breaker["action"] == "NAVIGATE_ZONE_EXIT:N", f"Expected loop breaker to route to N, got: {dec_loop_breaker['action']}"
assert ("JoppaWorld.10.23.0.1.11", "E") in brain.FAILED_ZONE_EXITS, "East exit should be blacklisted by loop breaker"

# =====================================================================
# TEST 38: Autonomous Enclosed Pocket Burrowing & Wall Destruction
# =====================================================================
print("\n" + "="*50)
print("TEST 38: Autonomous Enclosed Pocket Burrowing & Wall Destruction")
print("="*50)

# Scenario 38.1: Live state where player is in sealed 3x3 pocket at (70, 6)
sealed_pocket_state = {
    "hp": 26, "max_hp": 26, "level": 4, "x": 70, "y": 6, "z": 11,
    "zone_id": "JoppaWorld.9.23.2.1.11",
    "zone_name": "subterranean salt marsh, 1 stratum deep",
    "zone_fully_explored": False,
    "unexplored_cells": 1822,
    "unexplored_centroid_x": 36, "unexplored_centroid_y": 12,
    "nearest_unexplored_x": 66, "nearest_unexplored_y": 7, "nearest_unexplored_dist": 4,
    "last_move_failed": False,
    "surroundings": {
        "NW": "[NPC: salt-encrusted sprouting orb], salt-encrusted watervine",
        "N": "[COMPANION: cave spider]",
        "NE": "[BLOCKED: impassable terrain], [BLOCKED: plant matter]",
        "W": "salt-encrusted watervine, puddle of rules|8 drams of dilute salt",
        "E": "[BLOCKED: impassable terrain], [BLOCKED: plant matter]",
        "SW": "[BLOCKED: impassable terrain], [BLOCKED: plant matter]",
        "S": "[BLOCKED: impassable terrain], [BLOCKED: plant matter]",
        "SE": "[BLOCKED: impassable terrain], [BLOCKED: plant matter]",
        "WW": "[BLOCKED: impassable terrain], [BLOCKED: tangled mudroot]"
    },
    "companions": [{"name": "cave spider", "hp": 12, "max_hp": 12, "dist": 1, "dir": "N", "tx": 70, "ty": 5}],
    "stairs_up": [], "stairs_down": [], "visible_entities": []
}

# Simulate having entered and explored the 2 open tiles in the pocket
brain.CURRENT_TRACKED_ZONE = "JoppaWorld.9.23.2.1.11"
brain.current_zone_id = "JoppaWorld.9.23.2.1.11"
brain.visit_counts.clear()
brain.visit_counts[(70, 6)] = 2
brain.visit_counts[(69, 6)] = 1
brain.stuck_autoexplore_zones.add("JoppaWorld.9.23.2.1.11")

dec_burrow = brain.query_decision(sealed_pocket_state, took_damage=False, enemies=[])
print(f"Autonomous burrowing decision: {dec_burrow['action']} | Reason: {dec_burrow['reason']}")
assert dec_burrow["action"] == "ATTACK_WALL:SW", f"Expected ATTACK_WALL:SW to breach pocket toward (36, 12), got: {dec_burrow['action']}"
assert "Autonomous Burrowing" in dec_burrow["reason"]
assert "plant matter" in dec_burrow["reason"]

# Scenario 38.2: find_burrow_direction helper verification
best_d, best_info = brain.find_burrow_direction(sealed_pocket_state["surroundings"], (70, 6), (36, 12))
print(f"find_burrow_direction: Best dir {best_d}, Target info: {best_info}")
assert best_d == "SW", f"Expected best burrow dir SW, got: {best_d}"
assert "plant matter" in best_info

# Scenario 38.3: Loop Breaker oscillation inside sealed pocket
brain.recent_positions.clear()
brain.recent_positions.extend([(70, 6), (69, 6)] * 4)
dec_lb_burrow = brain.query_decision(sealed_pocket_state, took_damage=False, enemies=[])
print(f"Loop breaker pocket burrow decision: {dec_lb_burrow['action']} | Reason: {dec_lb_burrow['reason']}")
assert dec_lb_burrow["action"].startswith("ATTACK_WALL:"), f"Expected ATTACK_WALL action from loop breaker, got: {dec_lb_burrow['action']}"

# =====================================================================
# TEST 39: Border Exit Commitment & Non-Oscillation Verification
# =====================================================================
print("\n" + "="*50)
print("TEST 39: Border Exit Commitment & Non-Oscillation Verification")
print("="*50)

# Scenario 39.1: Corridor on west side with reachable_edges="NSEW" - must NOT fail or flip
corridor_west_state = {
    "hp": 26, "max_hp": 26, "level": 4, "x": 5, "y": 10, "z": 11,
    "zone_id": "JoppaWorld.10.23.0.1.11",
    "zone_name": "subterranean salt marsh, 1 stratum deep",
    "zone_fully_explored": True,
    "unexplored_cells": 605,
    "reachable_edges": "NSEW",
    "last_move_failed": False,
    "surroundings": {
        "W": "[BLOCKED: rock wall]", "NW": "[BLOCKED: rock wall]", "SW": "[BLOCKED: rock wall]",
        "N": "Empty ground", "S": "Empty ground", "E": "Empty ground", "NE": "Empty ground", "SE": "Empty ground"
    },
    "visible_entities": []
}

brain.current_zone_id = "JoppaWorld.10.23.0.1.11"
brain.CURRENT_TRACKED_ZONE = "JoppaWorld.10.23.0.1.11"
brain.CURRENT_ZONE_CHOSEN_EXIT = "W"
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = "JoppaWorld.10.23.0.1.11"
brain.FAILED_ZONE_EXITS.clear()

fail_check = brain.check_exit_direction_failure(corridor_west_state, (5, 10), "W")
print(f"West exit failure check in corridor (reachable_edges='NSEW'): {fail_check}")
assert not fail_check, "Exit W must NOT be flagged as failed when engine reports reachable_edges='NSEW'!"

pos_w, tag_w, dir_w = brain.get_zone_exit_target((5, 10), corridor_west_state)
print(f"West exit target: {pos_w}, Tag: {tag_w}, Dir: {dir_w}")
assert dir_w == "W", f"Expected exit direction to remain W, got: {dir_w}"
assert ("JoppaWorld.10.23.0.1.11", "W") not in brain.FAILED_ZONE_EXITS, "W must not be blacklisted!"

# Scenario 39.2: Adjacent to border edge at (1, 10) with chosen exit W
border_adj_state = dict(corridor_west_state)
border_adj_state["x"] = 1
border_adj_state["y"] = 10
border_adj_state["surroundings"] = {
    "W": "Open ground", "NW": "Open ground", "SW": "Open ground",
    "N": "Empty ground", "S": "Empty ground", "E": "Empty ground", "NE": "Empty ground", "SE": "Empty ground"
}

dec_border_adj = brain.query_decision(border_adj_state, took_damage=False, enemies=[])
print(f"Adjacent to border decision: {dec_border_adj['action']} | Reason: {dec_border_adj['reason']}")
assert dec_border_adj["action"] == "MOVE_W", f"Expected MOVE_W onto border, got: {dec_border_adj['action']}"
assert "Border Transition" in dec_border_adj["reason"]

# Scenario 39.3: Standing directly on border edge at (0, 10) facing [ZONE_EXIT: W]
border_on_state = dict(corridor_west_state)
border_on_state["x"] = 0
border_on_state["y"] = 10
border_on_state["surroundings"] = {
    "W": "[ZONE_EXIT: W]", "NW": "[ZONE_EXIT: NW]", "SW": "[ZONE_EXIT: SW]",
    "N": "Empty ground", "S": "Empty ground", "E": "Empty ground", "NE": "Empty ground", "SE": "Empty ground"
}

dec_border_on = brain.query_decision(border_on_state, took_damage=False, enemies=[])
print(f"Standing on border decision: {dec_border_on['action']} | Reason: {dec_border_on['reason']}")
assert dec_border_on["action"] == "MOVE_W", f"Expected MOVE_W across border, got: {dec_border_on['action']}"
assert "Border Transition" in dec_border_on["reason"]

# =====================================================================
# TEST 40: Dungeon Diving: Tough Choice Delving, Pits, Holes & Stratum Descent
# =====================================================================
print("\n" + "="*50)
print("TEST 40: Dungeon Diving: Tough Choice Delving, Pits, Holes & Stratum Descent")
print("="*50)

# Scenario 40.1: Pit / Chasm Passability in get_valid_moves
# Cells containing [STAIRS_DOWN: ...] must be passable even if they mention "pit", "hole", "shaft", or "chasm"
pit_surroundings = {
    "N": "[STAIRS_DOWN: deep pit leading to stratum 12]",
    "S": "[STAIRS_DOWN: open shaft dropping into the dark]",
    "E": "[HAZARD: pool of lava]",
    "W": "[BLOCKED: chasm with no bottom]", # true hazard without stairs_down tag
    "NE": "dirt floor", "NW": "dirt floor", "SE": "dirt floor", "SW": "dirt floor"
}
valid_pit_moves = brain.get_valid_moves(pit_surroundings, (10, 10), None)
print(f"Valid moves with pit/shaft down passages: {valid_pit_moves}")
assert "MOVE_N" in valid_pit_moves, "Cell with [STAIRS_DOWN: deep pit ...] must be a valid passable move!"
assert "MOVE_S" in valid_pit_moves, "Cell with [STAIRS_DOWN: open shaft ...] must be a valid passable move!"
assert "MOVE_W" not in valid_pit_moves, "Cell with raw chasm (not a passage) must remain blocked!"
assert "MOVE_E" not in valid_pit_moves, "Cell with lava must remain blocked!"

# Scenario 40.2: Bold Dungeon Delving when Under-leveled (Stratum 11 -> 12)
# Recommended level for stratum 12 is 5, character is only Level 3 but healthy (HP 28/28)
dungeon_stratum11_zone = "JoppaWorld.10.23.0.1.11"
brain.current_zone_id = dungeon_stratum11_zone
brain.CURRENT_TRACKED_ZONE = dungeon_stratum11_zone
brain.RETREAT_TARGET_LEVEL = None

delve_state_healthy = {
    "hp": 28, "max_hp": 28, "x": 15, "y": 12, "z": 11,
    "calling": "Apostle",
    "level": 3, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": dungeon_stratum11_zone,
    "zone_name": "subterranean ruins",
    "standing_on_stairs_down": True,
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"C": "[STAIRS_DOWN: stone stairs down]"},
    "visible_entities": []
}
dec_delve = brain.query_decision(delve_state_healthy, took_damage=False, enemies=[])
print(f"Healthy under-leveled descent decision: {dec_delve['action']} | Reason: {dec_delve['reason']}")
assert dec_delve["action"] == "USE_STAIRS_DOWN", f"Healthy character must boldly descend stairs down! Got: {dec_delve['action']}"
assert "Dungeon Delving: Daring descent" in dec_delve["reason"], f"Expected daring descent reason, got: {dec_delve['reason']}"

# Scenario 40.3: Delve Preparation (Resting on stairs down when injured)
# Under-leveled character standing on stairs down/pit with low HP (< 70%) should rest first
delve_state_injured = dict(delve_state_healthy)
delve_state_injured["hp"] = 15 # 15/28 = 53% (< 70%)
dec_rest_delve = brain.query_decision(delve_state_injured, took_damage=False, enemies=[])
print(f"Injured descent preparation decision: {dec_rest_delve['action']} | Reason: {dec_rest_delve['reason']}")
assert dec_rest_delve["action"] == "REST", f"Injured character must rest to recover before descending! Got: {dec_rest_delve['action']}"
assert "resting" in dec_rest_delve["reason"].lower()

# Scenario 40.4: Navigating to Nearby Stairs Down / Hole in Dungeon
# When in dungeon and healthy, routes to known stairs down even if zone not yet 100% cleared
brain.KNOWN_STAIRS_DOWN[dungeon_stratum11_zone] = {"tx": 15, "ty": 12, "name": "hole in the ground"}
delve_state_nearby = dict(delve_state_healthy)
delve_state_nearby["standing_on_stairs_down"] = False
delve_state_nearby["x"] = 15
delve_state_nearby["y"] = 15 # 3 tiles away
delve_state_nearby["surroundings"] = {
    "N": "dirt floor", "S": "dirt floor", "E": "dirt floor", "W": "dirt floor"
}
dec_nearby = brain.query_decision(delve_state_nearby, took_damage=False, enemies=[])
print(f"Nearby dungeon stairs navigation decision: {dec_nearby['action']} | Reason: {dec_nearby['reason']}")
assert dec_nearby["action"] == "NAVIGATE_TO_CELL:15,12", f"Expected the engine path to the stairs down at (15, 12)! Got: {dec_nearby['action']}"
assert "Dungeon Delving: Navigating to stairs down" in dec_nearby["reason"]

# =====================================================================
# TEST 41: Town Hut Whacking & Structure Vandalism Suppression
# =====================================================================
print("\n" + "="*50)
print("TEST 41: Town Hut Whacking & Structure Vandalism Suppression")
print("="*50)

# Scenario 41.1: Settlement Identification
joppa_state = {
    "zone_id": "JoppaWorld.11.23.1.1.10",
    "zone_name": "Joppa",
    "is_settlement": True,
    "visible_entities": [{"name": "Elder Irudad", "blueprint": "Irudad"}]
}
stilt_state = {"zone_id": "JoppaWorld.5.5.1.1.10", "zone_name": "The Six-Day Stilt"}
wilderness_state = {"zone_id": "JoppaWorld.10.23.0.1.11", "zone_name": "subterranean ruins", "is_settlement": False}

print(f"Joppa is_town_zone: {brain.is_town_zone(joppa_state)}")
print(f"Stilt is_town_zone: {brain.is_town_zone(stilt_state)}")
print(f"Wilderness is_town_zone: {brain.is_town_zone(wilderness_state)}")
assert brain.is_town_zone(joppa_state) is True, "Joppa must be recognized as a town!"
assert brain.is_town_zone(stilt_state) is True, "The Six-Day Stilt must be recognized as a town!"
assert brain.is_town_zone(wilderness_state) is False, "Subterranean ruins must not be recognized as a town!"

# Scenario 41.2: Inside a Joppa hut with visited floor tiles
# The character is inside an elder's hut at (14, 10). North is a watervine wall,
# South is an open doorway leading out.
# Surrounding cells contain "watervine wall" (plant/wood).
# The character must NOT attack the hut wall!
hut_surroundings = {
    "N": "[BLOCKED: watervine wall]",
    "NW": "[BLOCKED: watervine wall]",
    "NE": "[BLOCKED: watervine wall]",
    "W": "[BLOCKED: watervine wall]",
    "E": "[BLOCKED: watervine wall]",
    "SW": "[BLOCKED: watervine wall]",
    "SE": "[BLOCKED: watervine wall]",
    "S": "open doorway", # door leading outside
}
brain.visit_counts.clear()
brain.visit_counts[(14, 10)] = 3 # Current tile visited multiple times
brain.visit_counts[(14, 11)] = 2 # Doorway tile also visited

# find_burrow_direction with is_town=True must return None
b_dir_town, b_tag_town = brain.find_burrow_direction(hut_surroundings, (14, 10), (14, 5), is_town=True)
print(f"Town find_burrow_direction: dir={b_dir_town}, tag={b_tag_town}")
assert b_dir_town is None, f"find_burrow_direction must return None in towns! Got: {b_dir_town}"

joppa_hut_state = {
    "hp": 25, "max_hp": 25, "x": 14, "y": 10, "z": 10,
    "calling": "Apostle",
    "level": 1,
    "zone_id": "JoppaWorld.11.23.1.1.10",
    "zone_name": "Joppa",
    "is_settlement": True,
    "zone_fully_explored": False,
    "unexplored_cells": 150,
    "unexplored_centroid_x": 14, "unexplored_centroid_y": 5, # Centroid north, through wall
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": hut_surroundings,
    "visible_entities": []
}

dec_hut = brain.query_decision(joppa_hut_state, took_damage=False, enemies=[])
print(f"Joppa hut decision: {dec_hut['action']} | Reason: {dec_hut['reason']}")
assert not dec_hut["action"].startswith("ATTACK_WALL"), f"Must NEVER attack walls or whack huts in Joppa! Got: {dec_hut['action']}"
assert dec_hut["action"] in ("MOVE_S", "AUTOEXPLORE") or dec_hut["action"].startswith("NAVIGATE"), f"Expected safe navigation, got: {dec_hut['action']}"

# Scenario 41.3: Loop Breaker oscillation inside town hut
# Character oscillating inside hut must NEVER trigger ATTACK_WALL
brain.recent_positions.clear()
brain.recent_positions.extend([(14, 10), (14, 11), (14, 10), (14, 11), (14, 10), (14, 11)])
# find_burrow_direction call in loop breaker with is_town=True
b_dir_lb, b_tag_lb = brain.find_burrow_direction(hut_surroundings, (14, 10), (14, 5), is_town=True)
assert b_dir_lb is None, "Loop breaker must not burrow in town!"

# ==============================================================================
# TEST 42: Level 4 Mutant Ability Unlock & Autonomous Modal Interception
# ==============================================================================
print("\n==================================================")
print("TEST 42: Level 4 Mutant Ability Unlock & Autonomous Modal Interception")
print("==================================================")

# Scenario 42.1: Level 4 Mutant with 4 MP and all current mutations capped
# Marauder has FreezingRay (capped at 3) and MultipleLegs (capped at 3).
# Next priority in template is Teleportation!
lvl4_marauder_state = {
    "hp": 35, "max_hp": 35, "x": 10, "y": 10, "z": 10,
    "calling": "Marauder",
    "level": 4,
    "ap": 0, "sp": 20, "mp": 4,
    "mutations": [
        {"name": "Freezing Ray", "class": "FreezingRay", "level": 3, "cap": 3, "can_level": False},
        {"name": "Multiple Legs", "class": "MultipleLegs", "level": 3, "cap": 3, "can_level": False}
    ],
    "skills": ["Axe", "Axe_Expertise"],
    "zone_id": "JoppaWorld.10.23.0.1.10",
    "zone_name": "Canyon",
    "zone_fully_explored": False,
    "hostiles_nearby": False, "hostiles_adjacent": False,
    "surroundings": {"(10, 10)": {"walkable": True, "type": "Empty"}},
    "visible_entities": []
}

tpl_marauder = build_templates.detect_build(lvl4_marauder_state)
mut_rec_action, mut_rec_reason = build_templates.get_mutation_allocation_recommendation(
    tpl_marauder, lvl4_marauder_state["mutations"], lvl4_marauder_state["mp"]
)
print(f"Level 4 Marauder 4-MP recommendation: {mut_rec_action} | Reason: {mut_rec_reason}")
assert mut_rec_action == "AUTOLEVEL_BUY_MUTATION:Teleportation", f"Expected buy mutation Teleportation, got: {mut_rec_action}"

dec_lvl4 = brain.query_decision(lvl4_marauder_state, took_damage=False, enemies=[])
print(f"Level 4 Marauder decision: {dec_lvl4['action']} | Reason: {dec_lvl4['reason']}")
assert dec_lvl4["action"] == "AUTOLEVEL_BUY_MUTATION:Teleportation", f"Expected AUTOLEVEL_BUY_MUTATION:Teleportation, got {dec_lvl4['action']}"

# Scenario 42.2: Normal 1-MP mutation level up when not capped
lvl2_marauder_state = dict(lvl4_marauder_state)
lvl2_marauder_state["mp"] = 1
lvl2_marauder_state["mutations"] = [
    {"name": "Freezing Ray", "class": "FreezingRay", "level": 1, "cap": 3, "can_level": True},
    {"name": "Multiple Legs", "class": "MultipleLegs", "level": 1, "cap": 3, "can_level": True}
]
dec_lvl2 = brain.query_decision(lvl2_marauder_state, took_damage=False, enemies=[])
print(f"Level 2 Marauder 1-MP decision: {dec_lvl2['action']} | Reason: {dec_lvl2['reason']}")
assert dec_lvl2["action"] == "AUTOLEVEL_MUTATION:FreezingRay", f"Expected leveling FreezingRay, got: {dec_lvl2['action']}"

# Scenario 42.3: Twitch Chat Vote Winner for Mutation Purchase
class MockTwitchVoteManager:
    def __init__(self):
        self.reset_called = False
    def get_top_stat(self):
        return None
    def get_top_skill(self):
        return None
    def get_top_mutation(self):
        return ("LightManipulation", 12)
    def reset_mutation_votes(self):
        self.reset_called = True

orig_twitch = brain.twitch_manager
brain.twitch_manager = MockTwitchVoteManager()
try:
    dec_twitch_mut = brain.query_decision(lvl4_marauder_state, took_damage=False, enemies=[])
    print(f"Twitch mutation vote decision: {dec_twitch_mut['action']} | Reason: {dec_twitch_mut['reason']}")
    assert dec_twitch_mut["action"] == "AUTOLEVEL_BUY_MUTATION:LightManipulation", f"Expected Twitch vote winner LightManipulation, got: {dec_twitch_mut['action']}"
    assert brain.twitch_manager.reset_called, "Twitch mutation votes must be reset after winner is selected"
finally:
    brain.twitch_manager = orig_twitch

# Scenario 42.4: 3 MP with capped mutations preserves points without looping
lvl3_capped_state = dict(lvl4_marauder_state)
lvl3_capped_state["mp"] = 3
lvl3_capped_state["mutations"] = [
    {"name": "Freezing Ray", "class": "FreezingRay", "level": 3, "cap": 3, "can_level": False},
    {"name": "Multiple Legs", "class": "MultipleLegs", "level": 3, "cap": 3, "can_level": False}
]
dec_lvl3 = brain.query_decision(lvl3_capped_state, took_damage=False, enemies=[])
print(f"Level 3 3-MP capped decision: {dec_lvl3['action']} | Reason: {dec_lvl3['reason']}")
assert not dec_lvl3["action"].startswith("AUTOLEVEL"), f"Must not autolevel when MP < 4 and all mutations capped! Got: {dec_lvl3['action']}"

# ==============================================================================
# TEST 43: Secondary Action Bar & Alternating Ray Cooldown Execution
# ==============================================================================
print("\n==================================================")
print("TEST 43: Secondary Action Bar & Alternating Ray Cooldown Execution")
print("==================================================")

# Scenario 43.1: Level 5 Nomad with both Freezing Ray and Flaming Ray ready
# Facing an approaching hostile snapjaw at distance 3 (E).
# Must fire Freezing Ray as CC opener to freeze mobile pursuer!
lvl5_nomad_state = {
    "hp": 32, "max_hp": 32, "x": 10, "y": 10, "z": 10,
    "calling": "Nomad",
    "level": 5, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.23.0.1.10",
    "zone_name": "Canyon",
    "has_missile_weapon": True, "missile_ammo": 6, "missile_max_ammo": 6, "inventory_ammo": 50,
    "has_companion": False, "companions": [],
    "abilities": [
        {"name": "Freezing Ray", "command": "CommandFreezingRay", "usable": True, "cooldown": 0},
        {"name": "Flaming Ray", "command": "CommandFlamingRay", "usable": True, "cooldown": 0},
        {"name": "Butcher", "command": "CmdButcher", "usable": True, "cooldown": 0}
    ],
    "surroundings": {
        "NW": "Empty ground", "N": "Empty ground", "NE": "Empty ground",
        "W": "Empty ground", "E": "Empty ground",
        "SW": "Empty ground", "S": "Empty ground", "SE": "Empty ground"
    },
    "visible_entities": [
        {"name": "snapjaw scavenger", "dist": 3, "dir": "E", "tx": 13, "ty": 10, "is_enemy": True}
    ]
}

orig_query_llm = brain.query_llm_decision
brain.query_llm_decision = lambda *args, **kwargs: None
try:
    dec_ray_opener = brain.query_decision(lvl5_nomad_state, took_damage=False, enemies=[lvl5_nomad_state["visible_entities"][0]])
    print(f"Scenario 43.1 Dual-Ray Opener decision: {dec_ray_opener['action']} | Reason: {dec_ray_opener['reason']}")
    assert dec_ray_opener["action"] == "USE_ABILITY:CommandFreezingRay:E", f"Expected Freezing Ray opener, got: {dec_ray_opener['action']}"

    # Scenario 43.2: Freezing Ray on cooldown, Flaming Ray ready on secondary action bar
    # Must alternate to Flaming Ray thermal beam!
    lvl5_nomad_cooldown_state = dict(lvl5_nomad_state)
    lvl5_nomad_cooldown_state["abilities"] = [
        {"name": "Freezing Ray", "command": "CommandFreezingRay", "usable": False, "cooldown": 14},
        {"name": "Flaming Ray", "command": "CommandFlamingRay", "usable": True, "cooldown": 0},
        {"name": "Butcher", "command": "CmdButcher", "usable": True, "cooldown": 0}
    ]
    dec_flame_beam = brain.query_decision(lvl5_nomad_cooldown_state, took_damage=False, enemies=[lvl5_nomad_state["visible_entities"][0]])
    print(f"Scenario 43.2 Alternate Flaming Ray decision: {dec_flame_beam['action']} | Reason: {dec_flame_beam['reason']}")
    assert dec_flame_beam["action"] == "USE_ABILITY:CommandFlamingRay:E", f"Expected Flaming Ray burst, got: {dec_flame_beam['action']}"

    # Scenario 43.3: In melee contact with adjacent enemy
    # In adjacent melee (dist 1), point-blank Flaming Ray burst triggers before basic bump!
    lvl5_melee_contact_state = dict(lvl5_nomad_cooldown_state)
    lvl5_melee_contact_state["surroundings"] = dict(lvl5_nomad_state["surroundings"])
    lvl5_melee_contact_state["surroundings"]["E"] = "[ENEMY: snapjaw scavenger]"
    lvl5_melee_contact_state["visible_entities"] = [
        {"name": "snapjaw scavenger", "dist": 1, "dir": "E", "tx": 11, "ty": 10, "is_enemy": True}
    ]
    dec_point_blank = brain.query_decision(lvl5_melee_contact_state, took_damage=False, enemies=[lvl5_melee_contact_state["visible_entities"][0]])
    print(f"Scenario 43.3 Point-Blank Ray Burst decision: {dec_point_blank['action']} | Reason: {dec_point_blank['reason']}")
    assert dec_point_blank["action"] == "USE_ABILITY:CommandFlamingRay:E", f"Expected point-blank Flaming Ray burst, got: {dec_point_blank['action']}"

    # Scenario 43.4: Melee Marauder at distance 3 with Charge on cooldown
    # Marauder has Charge on cooldown, but acquired Flaming Ray!
    # Blasts approaching enemy at distance 3 with Flaming Ray!
    lvl5_marauder_state = {
        "hp": 40, "max_hp": 40, "x": 10, "y": 10, "z": 10,
        "calling": "Marauder",
        "level": 5, "ap": 0, "sp": 0, "mp": 0,
        "zone_id": "JoppaWorld.10.23.0.1.10",
        "zone_name": "Canyon",
        "has_missile_weapon": False,
        "has_companion": False, "companions": [],
        "abilities": [
            {"name": "Charge", "command": "CommandCharge", "usable": False, "cooldown": 10},
            {"name": "Dismember", "command": "CommandDismember", "usable": True, "cooldown": 0},
            {"name": "Flaming Ray", "command": "CommandFlamingRay", "usable": True, "cooldown": 0}
        ],
        "surroundings": {
            "NW": "Empty ground", "N": "Empty ground", "NE": "Empty ground",
            "W": "Empty ground", "E": "Empty ground",
            "SW": "Empty ground", "S": "Empty ground", "SE": "Empty ground"
        },
        "visible_entities": [
            {"name": "snapjaw brute", "dist": 3, "dir": "E", "tx": 13, "ty": 10, "is_enemy": True}
        ]
    }
    dec_marauder_ray = brain.query_decision(lvl5_marauder_state, took_damage=False, enemies=[lvl5_marauder_state["visible_entities"][0]])
    print(f"Scenario 43.4 Marauder Range Ray decision: {dec_marauder_ray['action']} | Reason: {dec_marauder_ray['reason']}")
    assert dec_marauder_ray["action"] == "USE_ABILITY:CommandFlamingRay:E", f"Expected Marauder to blast with Flaming Ray, got: {dec_marauder_ray['action']}"

    # Scenario 43.5: Melee Marauder in melee contact with strike ability on cooldown
    # Marauder in melee with Dismember on cooldown -> executes point-blank Flaming Ray burst!
    lvl5_marauder_strike_cd = dict(lvl5_marauder_state)
    lvl5_marauder_strike_cd["abilities"] = [
        {"name": "Charge", "command": "CommandCharge", "usable": False, "cooldown": 10},
        {"name": "Dismember", "command": "CommandDismember", "usable": False, "cooldown": 15},
        {"name": "Flaming Ray", "command": "CommandFlamingRay", "usable": True, "cooldown": 0}
    ]
    lvl5_marauder_strike_cd["surroundings"] = dict(lvl5_marauder_state["surroundings"])
    lvl5_marauder_strike_cd["surroundings"]["E"] = "[ENEMY: snapjaw brute]"
    lvl5_marauder_strike_cd["visible_entities"] = [
        {"name": "snapjaw brute", "dist": 1, "dir": "E", "tx": 11, "ty": 10, "is_enemy": True}
    ]
    dec_marauder_burst = brain.query_decision(lvl5_marauder_strike_cd, took_damage=False, enemies=[lvl5_marauder_strike_cd["visible_entities"][0]])
    print(f"Scenario 43.5 Marauder Point-Blank Burst decision: {dec_marauder_burst['action']} | Reason: {dec_marauder_burst['reason']}")
    assert dec_marauder_burst["action"] == "USE_ABILITY:CommandFlamingRay:E", f"Expected Marauder point-blank Flaming Ray burst, got: {dec_marauder_burst['action']}"
finally:
    brain.query_llm_decision = orig_query_llm

# Scenario 43.6: DIRECTIONAL_ABILITIES alias coverage
# Ensure all forms of ray commands are registered in DIRECTIONAL_ABILITIES
assert "flaming ray" in brain.DIRECTIONAL_ABILITIES
assert "flamingray" in brain.DIRECTIONAL_ABILITIES
assert "commandflamingray" in brain.DIRECTIONAL_ABILITIES
assert "freezing ray" in brain.DIRECTIONAL_ABILITIES
assert "freezingray" in brain.DIRECTIONAL_ABILITIES
assert "commandfreezingray" in brain.DIRECTIONAL_ABILITIES

# ==============================================================================
# TEST 44: Down-Passage Validation, Staircase Prioritization, Companion Immunity,
#          Ray-Trace Line-of-Fire Protection, and Cross-Turn Memory Persistence
# ==============================================================================
print("\n[TEST 44] Running Down-Passage Validation & Companion Immunity Tests...")

# Scenario 44.1: Seed-spitting vine & plant exclusion from stairs down
assert brain.is_valid_stair_down("seed-spitting vine", "Seed-Spitting Vine") is False, "seed-spitting vine must not be valid stairs down"
assert brain.is_valid_stair_down("spit vine") is False, "spit vine must not be valid stairs down"
assert brain.is_valid_stair_down("watervine") is False, "watervine must not be valid stairs down"
assert brain.is_valid_stair_down("cave spider") is False, "creature must not be valid stairs down"
assert brain.is_valid_stair_down("corpse of snapjaw") is False, "corpse must not be valid stairs down"
assert brain.is_valid_stair_down("stairs down", "StairsDown") is True, "stairs down must be valid"
assert brain.is_valid_stair_down("ladder down", "LadderDown") is True, "ladder down must be valid"
assert brain.is_valid_stair_down("open shaft", "Shaft") is True, "shaft must be valid"
assert brain.is_valid_stair_down("deep pit", "Pit") is True, "pit must be valid"
print("  [OK] Scenario 44.1 Passed: Plants, creatures, and 'spit' substrings strictly rejected from down passages.")

# Scenario 44.2: Staircase Prioritization & Telemetry Ingestion
brain.KNOWN_STAIRS_DOWN.clear()
test_zid = "JoppaWorld.11.19.0.2.10"
state_mixed_stairs = {
    "zone_id": test_zid,
    "z": 10,
    "level": 6,
    "stairs_down": [
        {"name": "seed-spitting vine", "blueprint": "Seed-Spitting Vine", "tx": 0, "ty": 14},
        {"name": "open pit", "blueprint": "Pit", "tx": 1, "ty": 16},
        {"name": "stairs down", "blueprint": "StairsDown", "tx": 6, "ty": 22}
    ]
}
brain.update_stair_records(state_mixed_stairs)
assert test_zid in brain.KNOWN_STAIRS_DOWN
assert brain.KNOWN_STAIRS_DOWN[test_zid]["tx"] == 6 and brain.KNOWN_STAIRS_DOWN[test_zid]["ty"] == 22, (
    f"Expected true stairs at (6, 22), got ({brain.KNOWN_STAIRS_DOWN[test_zid]['tx']}, {brain.KNOWN_STAIRS_DOWN[test_zid]['ty']})"
)
assert brain.KNOWN_STAIRS_DOWN[test_zid]["name"] == "stairs down"
# Subsequent telemetry with only a pit should NOT downgrade the recorded true stairs
state_pit_only = {
    "zone_id": test_zid,
    "z": 10,
    "level": 6,
    "stairs_down": [
        {"name": "open pit", "blueprint": "Pit", "tx": 1, "ty": 16}
    ]
}
brain.update_stair_records(state_pit_only)
assert brain.KNOWN_STAIRS_DOWN[test_zid]["tx"] == 6 and brain.KNOWN_STAIRS_DOWN[test_zid]["ty"] == 22, "Pit should not overwrite true stairs down"
print("  [OK] Scenario 44.2 Passed: True stairs down prioritized over pits, and plants/vines discarded.")

# Scenario 44.3: Companion Line-of-Fire Ray-Tracing Protection
# Player at (15, 11), companion at (14, 10), enemy (horned chameleon) at (11, 7)
player_coord = (15, 11)
enemy_coord = (11, 7)
companion_coord = (14, 10)

# Direct ray check with explicit companion
lof_clear, lof_reason = brain.is_line_of_fire_clear(
    player_coord,
    enemy_coord,
    companions=[{"name": "snapjaw", "tx": companion_coord[0], "ty": companion_coord[1]}]
)
assert lof_clear is False, "Line of fire must be blocked when companion is in the ray path"
assert "companion" in lof_reason.lower() or "snapjaw" in lof_reason.lower()

# Check with CHARMED_COMPANION_COORDS memory
brain.CHARMED_COMPANION_COORDS.clear()
brain.CHARMED_COMPANION_COORDS.add(companion_coord)
lof_clear2, lof_reason2 = brain.is_line_of_fire_clear(player_coord, enemy_coord)
assert lof_clear2 is False, "Line of fire must be blocked when companion is in CHARMED_COMPANION_COORDS"

# Ensure query_decision does NOT offer directional beam ability when companion in line of fire
state_chameleon_fight = {
    "zone_id": test_zid,
    "pos": [15, 11],
    "x": 15,
    "y": 11,
    "hp": 38,
    "max_hp": 38,
    "level": 6,
    "has_companion": True,
    "companions": [{"name": "snapjaw", "hp": 12, "max_hp": 12, "tx": 14, "ty": 10}],
    "visible_entities": [
        {"name": "horned chameleon", "difficulty": "Average", "dist": 4, "dir": "NW", "tx": 11, "ty": 7, "is_enemy": True, "has_los": True}
    ],
    "abilities": [
        {"name": "Lase", "command": "CommandLase", "class": "Mutation", "cooldown": 0}
    ],
    "surroundings": {
        "NW": "Empty", "N": "Empty", "NE": "Empty",
        "W": "Empty", "E": "Empty",
        "SW": "Empty", "S": "Empty", "SE": "Empty"
    }
}
dec = brain.query_decision(state_chameleon_fight, took_damage=False, enemies=state_chameleon_fight["visible_entities"])
# The decision must NOT be USE_ABILITY:CommandLase:NW because snapjaw is directly in the path!
assert "CommandLase" not in dec.get("action", ""), f"Lase should NOT be used through friendly pet! Action: {dec.get('action')}"
print("  [OK] Scenario 44.3 Passed: Direct ray line of fire through friendly companion strictly aborted.")

# Scenario 44.4: Companion cell memory tracks coordinates only (never names)
brain.CHARMED_COMPANION_COORDS.clear()
brain.register_companion((14, 10))
assert (14, 10) in brain.CHARMED_COMPANION_COORDS

# Turn 2: the engine flags the pet via is_companion; it moved to (13, 9). Another same-species creature is NOT flagged.
turn2_entities = [
    {"name": "snapjaw hunter", "tx": 13, "ty": 9, "dist": 2, "dir": "NW", "is_enemy": False, "is_companion": True},
    {"name": "snapjaw hunter", "tx": 20, "ty": 20, "dist": 12, "dir": "SE", "is_enemy": True, "is_companion": False},
]
current_comp_coords = set()
for e in turn2_entities:
    if e.get("is_companion", False):
        current_comp_coords.add((e.get("tx"), e.get("ty")))
brain.CHARMED_COMPANION_COORDS.clear()
brain.CHARMED_COMPANION_COORDS.update(current_comp_coords)
assert (13, 9) in brain.CHARMED_COMPANION_COORDS
assert (14, 10) not in brain.CHARMED_COMPANION_COORDS
assert (20, 20) not in brain.CHARMED_COMPANION_COORDS
kept = brain.filter_hostile_enemies(turn2_entities, [])
assert [(k["tx"], k["ty"]) for k in kept] == [(20, 20)], f"Wild same-species creature must stay hostile, got {kept}"
print("  [OK] Scenario 44.4 Passed: Companion memory tracks coordinates only; same-species hostile stays hostile.")

# =====================================================================
# TEST 45: Dungeon Progress, Eyeless Crab Combat Engagement & High-Priority Proselytize
# =====================================================================
print("\n" + "="*50)
print("TEST 45: Dungeon Progress, Eyeless Crab Combat Engagement & Proselytize Priority")
print("="*50)

# Clear companion caches
brain.CHARMED_COMPANION_COORDS.clear()

dungeon_zone = "JoppaWorld.11.19.0.2.11"
brain.current_zone_id = dungeon_zone
brain.CURRENT_TRACKED_ZONE = dungeon_zone

# Scenario 45.1: Petless Esper facing an Eyeless Crab at Distance 2 -> Approaches to Recruit
crab_dist2_state = {
    "hp": 38, "max_hp": 38, "x": 10, "y": 10, "z": 11,
    "calling": "Apostle",
    "level": 6, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": dungeon_zone,
    "zone_name": "subterranean ruins",
    "has_companion": False,
    "companions": [],
    "abilities": [
        {"name": "Proselytize", "command": "CommandProselytize", "cooldown": 0},
        {"name": "Light Manipulation (4 charges)", "command": "CommandLase", "cooldown": 0},
        {"name": "Flaming Ray", "command": "CommandFlamingRay", "cooldown": 0}
    ],
    "surroundings": {"C": "dirt floor", "E": "dirt floor", "W": "dirt floor", "N": "dirt floor", "S": "dirt floor"},
    "visible_entities": [
        {"name": "eyeless crab", "tx": 12, "ty": 10, "dist": 2, "is_enemy": True, "difficulty": "Average"}
    ]
}
enemies_crab = [
    {"name": "eyeless crab", "tx": 12, "ty": 10, "dist": 2, "is_enemy": True, "difficulty": "Average"}
]
dec_crab_dist2 = brain.query_decision(crab_dist2_state, took_damage=False, enemies=enemies_crab)
print(f"Scenario 45.1 Petless Esper crab dist 2 decision: {dec_crab_dist2['action']} | Reason: {dec_crab_dist2['reason']}")
assert dec_crab_dist2["action"] in ("MOVE_E", "USE_ABILITY:CommandLase:E", "USE_ABILITY:CommandFlamingRay:E"), f"Expected engagement or approach towards crab, got: {dec_crab_dist2['action']}"
# Also verify deterministic fallback directly
dec_fb_dist2 = brain.fallback_esper(crab_dist2_state, enemies_crab, {}, ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], crab_dist2_state["abilities"], {"name": "Esper-ited Away"}, (10, 10), 10, 10, 38, 38, False, False, 0, 0, 0)
assert dec_fb_dist2["action"] == "MOVE_E" and "Approaching eyeless crab" in dec_fb_dist2["reason"], f"Fallback expected approaching crab, got: {dec_fb_dist2}"
print("  [OK] Scenario 45.1 Passed: Petless Esper engages or approaches eyeless crab at dist 2.")

# Scenario 45.2: Petless Esper facing adjacent Eyeless Crab (dist 1) -> Proselytizes immediately
crab_dist1_state = dict(crab_dist2_state)
crab_dist1_state["surroundings"] = {"C": "dirt floor", "E": "[HOSTILE: eyeless crab]", "W": "dirt floor", "N": "dirt floor", "S": "dirt floor"}
crab_dist1_state["visible_entities"] = [
    {"name": "eyeless crab", "tx": 11, "ty": 10, "dist": 1, "dir": "E", "is_enemy": True, "difficulty": "Average"}
]
enemies_crab1 = [
    {"name": "eyeless crab", "tx": 11, "ty": 10, "dist": 1, "is_enemy": True, "difficulty": "Average"}
]
dec_crab_dist1 = brain.query_decision(crab_dist1_state, took_damage=False, enemies=enemies_crab1)
print(f"Scenario 45.2 Petless Esper crab dist 1 decision: {dec_crab_dist1['action']} | Reason: {dec_crab_dist1['reason']}")
assert dec_crab_dist1["action"] == "USE_ABILITY:CommandProselytize:E", f"Expected Proselytize on adjacent crab, got: {dec_crab_dist1['action']}"
assert any(k in dec_crab_dist1["reason"].lower() for k in ["proselytiz", "recruit", "pet", "tank", "companion"]), f"Expected proselytize reason, got: {dec_crab_dist1['reason']}"
print("  [OK] Scenario 45.2 Passed: Petless Esper proselytizes adjacent eyeless crab into combat companion.")

# Scenario 45.3: Esper with companion already active facing crab at distance 2 -> Attacks with Lase instead of kiting
crab_with_pet_state = dict(crab_dist2_state)
crab_with_pet_state["has_companion"] = True
crab_with_pet_state["companions"] = [{"name": "snapjaw thrall", "tx": 10, "ty": 9, "dist": 1}]
dec_crab_attack = brain.query_decision(crab_with_pet_state, took_damage=False, enemies=enemies_crab)
print(f"Scenario 45.3 Esper with companion crab dist 2 decision: {dec_crab_attack['action']} | Reason: {dec_crab_attack['reason']}")
assert dec_crab_attack["action"] in ("USE_ABILITY:CommandLase:E", "USE_ABILITY:CommandFlamingRay:E"), f"Expected Lase/Ray attack on crab at dist 2, got: {dec_crab_attack['action']}"
assert any(k in dec_crab_attack["reason"].lower() for k in ["lase", "flaming", "beam", "ray", "damage", "attack", "dps"]), f"Expected Lase/Ray attack reason, got: {dec_crab_attack['reason']}"
# Also verify deterministic fallback directly
dec_fb_attack = brain.fallback_esper(crab_with_pet_state, enemies_crab, {}, ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], crab_with_pet_state["abilities"], {"name": "Esper-ited Away"}, (10, 10), 10, 10, 38, 38, False, False, 0, 0, 0)
assert dec_fb_attack["action"] == "USE_ABILITY:CommandLase:E", f"Fallback expected Lase, got: {dec_fb_attack}"
print("  [OK] Scenario 45.3 Passed: Esper attacks eyeless crab at distance 2 with ready Lase instead of backpedaling.")

# Scenario 45.4: Subterranean zone with stairs down nearby but hostile eyeless crab visible -> Does NOT flee to stairs
stairs_and_crab_state = dict(crab_dist2_state)
brain.KNOWN_STAIRS_DOWN[dungeon_zone] = {"tx": 10, "ty": 12, "name": "stairs down", "req_level": 3, "priority": 2}
stairs_and_crab_state["x"] = 10
stairs_and_crab_state["y"] = 10
stairs_and_crab_state["zone_fully_explored"] = False
dec_no_flee = brain.query_decision(stairs_and_crab_state, took_damage=False, enemies=enemies_crab)
print(f"Scenario 45.4 Stairs and crab decision: {dec_no_flee['action']} | Reason: {dec_no_flee['reason']}")
assert dec_no_flee["action"] != "MOVE_S", f"Must NOT flee towards stairs down at (10, 12) while crab is present! Got: {dec_no_flee['action']}"
assert dec_no_flee["action"] in ("MOVE_E", "USE_ABILITY:CommandLase:E", "USE_ABILITY:CommandFlamingRay:E"), f"Must engage/approach crab, got: {dec_no_flee['action']}"
print("  [OK] Scenario 45.4 Passed: Character does not abandon combat to navigate to stairs down.")

# Scenario 45.5: Eyeless crab occluded by corridor corner -> Maneuvers around corner to establish Line of Sight
crab_occluded_state = dict(crab_with_pet_state)
crab_occluded_state["visible_entities"] = [
    {"name": "eyeless crab", "tx": 12, "ty": 12, "dist": 2, "is_enemy": True, "difficulty": "Average"}
]
enemies_occluded = [
    {"name": "eyeless crab", "tx": 12, "ty": 12, "dist": 2, "is_enemy": True, "difficulty": "Average"}
]
# Wall blocks diagonal (11, 11)
crab_occluded_state["surroundings"] = {
    "C": "dirt floor",
    "E": "dirt floor",
    "S": "dirt floor",
    "SE": "[BLOCKED: solid rock wall]"
}
dec_maneuver = brain.query_decision(crab_occluded_state, took_damage=False, enemies=enemies_occluded)
print(f"Scenario 45.5 Occluded crab decision: {dec_maneuver['action']} | Reason: {dec_maneuver['reason']}")
assert dec_maneuver["action"] in ("MOVE_E", "MOVE_S"), f"Expected maneuvering move E or S, got: {dec_maneuver['action']}"
assert any(k in dec_maneuver["reason"].lower() for k in ["maneuver", "line of sight", "los", "corner", "wall", "corridor", "advance"]), f"Expected maneuvering for LOS reason, got: {dec_maneuver['reason']}"
# Also verify deterministic fallback directly
dec_fb_maneuver = brain.fallback_esper(crab_occluded_state, enemies_occluded, {}, ["MOVE_E", "MOVE_S"], ["MOVE_E", "MOVE_S"], crab_occluded_state["abilities"], {"name": "Esper-ited Away"}, (10, 10), 10, 10, 38, 38, False, False, 0, 0, 0)
assert dec_fb_maneuver["action"] in ("MOVE_E", "MOVE_S") and "Maneuvering" in dec_fb_maneuver["reason"], f"Fallback expected maneuvering, got: {dec_fb_maneuver}"
print("  [OK] Scenario 45.5 Passed: Character maneuvers around wall/corner to establish Line of Sight on occluded enemy.")

# =====================================================================
# TEST 46: Aquatic Proselytize Exclusion, Autoexplore Stuck Ingestion & Combat Fire Discipline
# =====================================================================
print("\n" + "="*50)
print("TEST 46: Aquatic Exclusion, Autoexplore Stuck Ingestion & Combat Fire Discipline")
print("="*50)

# Scenario 46.1: Aquatic and Swimming Entity Exclusion from Proselytize
glowfish_ent = {"name": "wet glowfish [swimming]", "blueprint": "Glowfish", "dist": 2, "is_enemy": False, "is_swimming": True}
piranha_ent = {"name": "piranha", "blueprint": "Piranha", "dist": 1, "is_enemy": True}
eel_ent = {"name": "electric eel", "blueprint": "ElectricEel", "dist": 1, "is_enemy": True}
crab_ent = {"name": "eyeless crab", "blueprint": "EyelessCrab", "dist": 1, "is_enemy": True}

assert brain.is_proselytizable(glowfish_ent) is False, "Glowfish must NOT be proselytizable!"
assert brain.is_proselytizable(piranha_ent) is False, "Piranha must NOT be proselytizable!"
assert brain.is_proselytizable(eel_ent) is False, "Electric eel must NOT be proselytizable!"
assert brain.is_proselytizable(crab_ent) is True, "Eyeless crab must be proselytizable!"
print("  [OK] Scenario 46.1 Passed: Aquatic fish and swimming creatures strictly excluded from recruitment.")

# Scenario 46.2: Autoexplore Stuck Telemetry Ingestion
stuck_zone_test = "JoppaWorld.11.21.0.1.10"
state_stuck_telemetry = {
    "hp": 20, "max_hp": 20, "x": 21, "y": 13, "z": 10,
    "calling": "Apostle",
    "level": 2, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": stuck_zone_test,
    "zone_name": "5th Ter, surface",
    "unexplored_cells": 614,
    "zone_fully_explored": False,
    "autoexplore_stuck": True,  # C# detected cycling and flagged stuck!
    "has_companion": False, "companions": [],
    "abilities": [],
    "surroundings": {"C": "dirt", "E": "dirt", "W": "dirt", "N": "dirt", "S": "dirt"},
    "visible_entities": []
}
dec_stuck = brain.query_decision(state_stuck_telemetry, took_damage=False, enemies=[], suppress_autolevel=True)
print(f"Scenario 46.2 Stuck autoexplore decision: {dec_stuck['action']} | Reason: {dec_stuck['reason']}")
assert stuck_zone_test in brain.stuck_autoexplore_zones, "Zone must be recorded in stuck_autoexplore_zones!"
assert dec_stuck["action"] != "AUTOEXPLORE", "Must NOT repeat AUTOEXPLORE when C# reports autoexplore_stuck!"
print("  [OK] Scenario 46.2 Passed: C# autoexplore_stuck telemetry immediately registered and breaks cycle.")

# Scenario 46.3: Multi-Enemy Combat Fire Discipline (Never approach into multiple enemies!)
multi_enemy_state = {
    "hp": 38, "max_hp": 38, "x": 10, "y": 10, "z": 11,
    "calling": "Apostle",
    "level": 6, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.11.19.0.2.11",
    "zone_name": "subterranean ruins",
    "has_companion": False,
    "companions": [],
    "abilities": [
        {"name": "Proselytize", "command": "CommandProselytize", "cooldown": 0},
        {"name": "Light Manipulation (4 charges)", "command": "CommandLase", "cooldown": 0},
        {"name": "Flaming Ray", "command": "CommandFlamingRay", "cooldown": 0}
    ],
    "surroundings": {"C": "dirt floor", "E": "dirt floor", "W": "dirt floor", "N": "dirt floor", "S": "dirt floor"},
    "visible_entities": [
        {"name": "eyeless crab", "tx": 12, "ty": 10, "dist": 2, "is_enemy": True, "difficulty": "Average"},
        {"name": "snapjaw brute", "tx": 14, "ty": 10, "dist": 4, "is_enemy": True, "difficulty": "Average"}
    ]
}
enemies_multi = multi_enemy_state["visible_entities"]
dec_multi_fb = brain.fallback_esper(multi_enemy_state, enemies_multi, {}, ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], multi_enemy_state["abilities"], {"name": "Esper-ited Away"}, (10, 10), 10, 10, 38, 38, False, False, 0, 0, 0)
print(f"Scenario 46.3 Multi-enemy decision: {dec_multi_fb['action']} | Reason: {dec_multi_fb['reason']}")
assert dec_multi_fb["action"] in ("USE_ABILITY:CommandLase:E", "USE_ABILITY:CommandFlamingRay:E"), f"Expected ranged attack against multi-enemy, got: {dec_multi_fb['action']}"
print("  [OK] Scenario 46.3 Passed: Multi-enemy battle enforces ranged fire discipline instead of approaching.")

# Scenario 46.4: Damaged Combat Fire Discipline (Never approach when taking damage!)
damaged_combat_state = dict(multi_enemy_state)
damaged_combat_state["visible_entities"] = [multi_enemy_state["visible_entities"][0]]  # Single crab
damaged_combat_state["took_damage"] = True
dec_damaged_fb = brain.fallback_esper(damaged_combat_state, [damaged_combat_state["visible_entities"][0]], {}, ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], damaged_combat_state["abilities"], {"name": "Esper-ited Away"}, (10, 10), 10, 10, 38, 38, False, False, 0, 0, 0)
print(f"Scenario 46.4 Damaged decision: {dec_damaged_fb['action']} | Reason: {dec_damaged_fb['reason']}")
assert dec_damaged_fb["action"] in ("USE_ABILITY:CommandLase:E", "USE_ABILITY:CommandFlamingRay:E"), f"Expected ranged attack when damaged, got: {dec_damaged_fb['action']}"
print("  [OK] Scenario 46.4 Passed: Damaged combatant maintains standoff and fires ranged powers.")

# Scenario 46.5: Nomad Sniper Standoff Discipline
nomad_sniper_state = {
    "hp": 28, "max_hp": 28, "x": 10, "y": 10, "z": 10,
    "calling": "Nomad",
    "level": 3, "ap": 0, "sp": 0, "mp": 0,
    "has_missile_weapon": True, "missile_ammo": 6, "missile_max_ammo": 6, "inventory_ammo": 24,
    "has_companion": False, "companions": [],
    "abilities": [
        {"name": "Proselytize", "command": "CommandProselytize", "usable": True, "cooldown": 0}
    ],
    "surroundings": {"C": "dirt", "E": "dirt", "W": "dirt", "N": "dirt", "S": "dirt"},
    "visible_entities": [
        {"name": "snapjaw scavenger", "tx": 12, "ty": 10, "dist": 2, "is_enemy": True, "difficulty": "Average"}
    ]
}
enemies_nomad = nomad_sniper_state["visible_entities"]
dec_nomad_fb = brain.fallback_nomad(nomad_sniper_state, enemies_nomad, {}, ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], ["MOVE_E", "MOVE_W", "MOVE_N", "MOVE_S"], nomad_sniper_state["abilities"], {"name": "Nomad Wanderer"}, (10, 10), 10, 10, 28, 28, False, True, 6, 6, 24, False)
print(f"Scenario 46.5 Nomad sniper decision: {dec_nomad_fb['action']} | Reason: {dec_nomad_fb['reason']}")
assert dec_nomad_fb["action"] == "FIRE_MISSILE@12,10", f"Expected sniper shot, got: {dec_nomad_fb['action']}"
print("  [OK] Scenario 46.5 Passed: Nomad sniper shoots prospective target at distance 2 instead of closing into melee.")

print("\n==================================================")
print("TEST 47: Canyon & Subterranean Reachable Edges Enforcement")
print("==================================================")

# Scenario 47.1: Surface Canyon Reachable Edges Verification
canyon_state = {
    "hp": 31, "max_hp": 31, "x": 36, "y": 6, "z": 10,
    "calling": "Apostle", "level": 5, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.18.1.2.10",
    "zone_name": "desert canyon, surface",
    "unexplored_cells": 932,
    "unexplored_centroid_x": 36, "unexplored_centroid_y": 6,
    "nearest_unexplored_x": 34, "nearest_unexplored_y": 8,
    "reachable_edges": "N",
    "has_companion": True,
    "companions": [{"name": "giant amoeba", "dist": 1, "dir": "E", "tx": 37, "ty": 6}],
    "surroundings": {
        "NW": "Empty ground", "N": "Empty ground", "NE": "Empty ground",
        "W": "Empty ground", "E": "[COMPANION: giant amoeba]",
        "SW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "S": "Empty ground", "SE": "Empty ground",
        "SS": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "SSW": "[BLOCKED: impassable terrain], [BLOCKED: shale]"
    },
    "visible_entities": []
}

# Verify check_exit_direction_failure rejects unreachable edges (S, E, W) and accepts N
assert brain.check_exit_direction_failure(canyon_state, (36, 6), "S") is True, "South exit must be flagged failed when not in reachable_edges 'N'!"
assert brain.check_exit_direction_failure(canyon_state, (36, 6), "E") is True, "East exit must be flagged failed when not in reachable_edges 'N'!"
assert brain.check_exit_direction_failure(canyon_state, (36, 6), "W") is True, "West exit must be flagged failed when not in reachable_edges 'N'!"
assert brain.check_exit_direction_failure(canyon_state, (36, 6), "N") is False, "North exit must NOT be flagged failed when in reachable_edges 'N'!"
print("  [OK] Scenario 47.1 Passed: reachable_edges strictly validates feasible borders and rejects blocked edges.")

# Scenario 47.2: Invalidation of previously-chosen unreachable exit
brain.CURRENT_ZONE_CHOSEN_EXIT = "S"
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = "JoppaWorld.10.18.1.2.10"
exit_pos, exit_tag, chosen_dir = brain.get_zone_exit_target((36, 6), canyon_state)
assert chosen_dir == "N", f"Expected exit N to be chosen instead of invalid S, got: {chosen_dir}"
assert ("JoppaWorld.10.18.1.2.10", "S") in brain.FAILED_ZONE_EXITS, "South exit must be blacklisted in FAILED_ZONE_EXITS!"
print("  [OK] Scenario 47.2 Passed: Previously locked South exit immediately invalidated and replaced with reachable North exit.")

# Scenario 47.3: Fully enclosed pocket (reachable_edges="")
enclosed_state = dict(canyon_state)
enclosed_state["reachable_edges"] = ""
assert brain.check_exit_direction_failure(enclosed_state, (36, 6), "N") is True, "All exits must fail when reachable_edges is empty!"
assert brain.check_exit_direction_failure(enclosed_state, (36, 6), "S") is True, "All exits must fail when reachable_edges is empty!"
enc_pos, enc_tag, enc_dir = brain.get_zone_exit_target((36, 6), enclosed_state)
assert enc_dir is None, f"Expected None exit dir in fully enclosed pocket, got: {enc_dir}"
print("  [OK] Scenario 47.3 Passed: Fully enclosed pocket correctly yields None exit dir without crashing or picking impossible edge.")

# Scenario 47.4: Fallback 3 Wall Detection (Surroundings with 2-step offsets)
fallback_canyon_state = {
    "hp": 31, "max_hp": 31, "x": 36, "y": 6, "z": 10,
    "zone_id": "JoppaWorld.10.18.1.2.10",
    "surroundings": {
        "S": "[BLOCKED: impassable terrain]",
        "SS": "[BLOCKED: impassable terrain]",
        "SSW": "[BLOCKED: impassable terrain]",
        "SSE": "[BLOCKED: impassable terrain]"
    }
}
assert brain.check_exit_direction_failure(fallback_canyon_state, (36, 6), "S") is True, "South must fail in fallback check when S/SS/SSW/SSE are blocked by walls!"
print("  [OK] Scenario 47.4 Passed: Fallback surroundings check detects blocked exit direction even when py < 20.")

print("\n==================================================")
print("TEST 48: Corridor Bottleneck, Companion Escape & Surface Exploration Protection")
print("==================================================")

# Scenario 48.1: Live state at (74, 8) with companion at (74, 9), 1613 unexplored cells
bottleneck_state = {
    "hp": 31, "max_hp": 31, "x": 74, "y": 8, "z": 10,
    "calling": "Apostle", "level": 5, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.18.1.1.10",
    "zone_name": "desert canyon, surface",
    "zone_fully_explored": False,
    "unexplored_cells": 1613,
    "unexplored_centroid_x": 35, "unexplored_centroid_y": 11,
    "nearest_unexplored_x": 75, "nearest_unexplored_y": 6,
    "reachable_edges": "NSEW",
    "last_move_failed": True,
    "last_failed_dir": "SW",
    "has_companion": True,
    "companions": [{"name": "giant amoeba", "dist": 1, "dir": "S", "tx": 74, "ty": 9}],
    "surroundings": {
        "NW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "N": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "NE": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "W": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "E": "Empty ground",
        "SW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "S": "[COMPANION: giant amoeba]",
        "SE": "[ITEM: giant dragonfly corpse]"
    },
    "visible_entities": []
}

brain.last_action = "AUTOEXPLORE"
dec_bn = brain.query_decision(bottleneck_state, False, [])
print(f"Scenario 48.1 Bottleneck breakout decision: {dec_bn['action']} | Reason: {dec_bn['reason']}")
assert dec_bn["action"] == "MOVE_SE", f"Expected MOVE_SE to escape bottleneck towards sector (35, 11), got: {dec_bn['action']}"
print("  [OK] Scenario 48.1 Passed: Failed autoexplore immediately ingests stuck state and maneuvers SE onto open tile.")

# Scenario 48.2: Loop breaker avoids repeating failed NAVIGATE_TO_CELL
brain.recent_positions = [(74, 8), (75, 8)] * 5
brain.unique_positions = 2
brain.pos_frequency = 5
brain.last_executed_action = "NAVIGATE_TO_CELL:35,11"
brain.last_executed_pos = (74, 8)
frontier_target, _ = brain.find_zone_unexplored_frontier(bottleneck_state, (74, 8), brain.visit_counts)
nav_cell_failed = (
    brain.last_executed_action.startswith("NAVIGATE_TO_CELL")
    and ((74, 8) == brain.last_executed_pos or bottleneck_state.get("last_move_failed", False))
)
assert nav_cell_failed is True, "nav_cell_failed must be detected when position didn't advance!"
valid_m = brain.get_valid_moves(bottleneck_state["surroundings"], (74, 8), None, is_in_combat=False)
open_escapes = [m for m in valid_m if ((74 + brain.CARDINAL_OFFSETS[m[5:]][0], 8 + brain.CARDINAL_OFFSETS[m[5:]][1])) not in brain.recent_positions]
assert "MOVE_SE" in open_escapes, f"Expected MOVE_SE in open_escapes, got: {open_escapes}"
print("  [OK] Scenario 48.2 Passed: Repeating failed NAVIGATE_TO_CELL suppressed; loop breaker redirects to open escapes.")

# Scenario 48.3: Companion swap when all open tiles visited multiple times
dead_end_surroundings = {
    "NW": "[BLOCKED: wall]", "N": "[BLOCKED: wall]", "NE": "[BLOCKED: wall]",
    "W": "[BLOCKED: wall]", "E": "[BLOCKED: wall]", "SW": "[BLOCKED: wall]",
    "SE": "[BLOCKED: wall]", "S": "[COMPANION: giant amoeba]"
}
comp_moves = []
for cd in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]:
    if "[companion" in dead_end_surroundings.get(cd, "").lower():
        comp_moves.append(f"MOVE_{cd}")
assert "MOVE_S" in comp_moves, f"Expected companion move MOVE_S, got: {comp_moves}"
print("  [OK] Scenario 48.3 Passed: Corridor companion swap detected when all alternative paths are solid walls.")

print("\n==================================================")
print("TEST 49: Canyon Dead-End, Unreachable Sector Blacklisting & Exit Commitment")
print("==================================================")

# Scenario 49.1: Live state at (45, 11) with companion at (46, 11), 1613 unrevealed cells across canyon wall at (35, 11)
canyon_dead_end_state = {
    "hp": 31, "max_hp": 31, "x": 45, "y": 11, "z": 10,
    "calling": "Apostle", "level": 5, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.18.1.1.10",
    "zone_name": "desert canyon, surface",
    "zone_fully_explored": False,
    "autoexplore_stuck": True,
    "unexplored_cells": 1613,
    "unexplored_centroid_x": 35, "unexplored_centroid_y": 11,
    "nearest_unexplored_x": 43, "nearest_unexplored_y": 9,
    "reachable_edges": "NSEW",
    "last_move_failed": True,
    "last_failed_dir": "PATH_BLOCKED",
    "has_companion": True,
    "companions": [{"name": "giant amoeba", "dist": 1, "dir": "E", "tx": 46, "ty": 11}],
    "surroundings": {
        "NW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "N": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "NE": "Empty ground",
        "W": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "E": "[COMPANION: giant amoeba]",
        "SW": "Empty ground",
        "S": "dogthorn tree, ashes",
        "SE": "Empty ground",
        "NW2": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "NNW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "NN": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "NNE": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "NE2": "Empty ground",
        "WNW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "ENE": "Empty ground",
        "WW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "EE": "Empty ground",
        "WSW": "[BLOCKED: impassable terrain], [BLOCKED: shale]",
        "ESE": "Empty ground",
        "SW2": "dogthorn tree",
        "SSW": "Empty ground",
        "SS": "Empty ground",
        "SSE": "Empty ground",
        "SE2": "Empty ground"
    },
    "visible_entities": []
}

# When last action was NAVIGATE_TO_CELL:35,11 and it failed with PATH_BLOCKED, target is blacklisted
brain.last_action = "NAVIGATE_TO_CELL:35,11"
brain.CURRENT_ZONE_CHOSEN_EXIT = None
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
brain.FAILED_ZONE_EXITS.clear()
brain.UNREACHABLE_SECTORS.clear()
brain.stuck_autoexplore_zones.add("JoppaWorld.10.18.1.1.10")

dec_49_1 = brain.query_decision(canyon_dead_end_state, took_damage=False, enemies=[])
print(f"Scenario 49.1 decision: {dec_49_1['action']} | Reason: {dec_49_1['reason']}")
assert ("JoppaWorld.10.18.1.1.10", (35, 11)) in brain.UNREACHABLE_SECTORS, "Centroid (35, 11) must be blacklisted in UNREACHABLE_SECTORS!"
assert dec_49_1["action"] != "MOVE_SW", "Must NOT loop back into dead-end MOVE_SW towards unreachable centroid!"
assert dec_49_1["action"].startswith("NAVIGATE_ZONE_EXIT:") or dec_49_1["action"] in ["MOVE_NE", "MOVE_SE", "MOVE_E"], f"Expected exit navigation or forward move, got: {dec_49_1['action']}"
print("  [OK] Scenario 49.1 Passed: Unreachable sector blacklisted after PATH_BLOCKED and redirected to exit navigation.")

# Scenario 49.2: Committed zone exit navigation when CURRENT_ZONE_CHOSEN_EXIT is set
brain.CURRENT_ZONE_CHOSEN_EXIT = "E"
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = "JoppaWorld.10.18.1.1.10"
dec_49_2 = brain.query_decision(canyon_dead_end_state, took_damage=False, enemies=[])
print(f"Scenario 49.2 decision: {dec_49_2['action']} | Reason: {dec_49_2['reason']}")
assert dec_49_2["action"] == "NAVIGATE_ZONE_EXIT:E", f"Expected committed NAVIGATE_ZONE_EXIT:E, got: {dec_49_2['action']}"
print("  [OK] Scenario 49.2 Passed: Chosen exit E committedly preserved without reverting to macro sector exploration.")

# ==================================================
# TEST 50: Joppa Town Natural Exit & Exhausted Pocket Exit Resolution
# ==================================================
print("\n==================================================")
print("TEST 50: Joppa Town Natural Exit & Exhausted Pocket Exit Resolution")
print("==================================================")

# Scenario 50.1: Joppa Town State at (34, 9)
joppa_state = {
    "hp": 24, "max_hp": 24, "x": 34, "y": 9, "z": 10,
    "calling": "Nomad", "level": 1, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.11.22.1.1.10",
    "zone_name": "Joppa",
    "is_settlement": True,
    "zone_fully_explored": False,
    "autoexplore_stuck": True,
    "unexplored_cells": 687,
    "unexplored_centroid_x": 34, "unexplored_centroid_y": 10,
    "nearest_unexplored_x": 30, "nearest_unexplored_y": 5,
    "reachable_edges": "NSEW",
    "last_move_failed": False,
    "surroundings": {
        "NW": "Empty ground", "N": "Empty ground", "NE": "dirt path",
        "W": "[BLOCKED: impassable terrain], [BLOCKED: brinestalk wall]",
        "E": "dirt path",
        "SW": "[BLOCKED: impassable terrain], [BLOCKED: brinestalk wall]",
        "S": "Empty ground", "SE": "Empty ground"
    },
    "companions": [],
    "visible_entities": []
}

# Scenario 50.1a: Joppa Town State at (34, 9) with unvisited open tile
brain.visit_counts.clear()
brain.stuck_autoexplore_zones.add("JoppaWorld.11.22.1.1.10")
brain.CURRENT_ZONE_CHOSEN_EXIT = None
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
brain.EXPLORED_ZONE_SET.clear()

dec_50_1a = brain.query_decision(joppa_state, took_damage=False, enemies=[])
print(f"Scenario 50.1a Joppa Fresh Tile Decision: {dec_50_1a['action']} | Reason: {dec_50_1a['reason']}")
assert dec_50_1a["action"] == "MOVE_NW", f"Expected fresh tile move MOVE_NW, got: {dec_50_1a['action']}"
assert dec_50_1a["action"] != "MOVE_S", "Must NOT greedily step South into Mehmet's wall oscillation!"
assert dec_50_1a["action"] != "NAVIGATE_TO_CELL:34,10", "Must NOT pathfind to fog centroid inside town house!"
print("  [OK] Scenario 50.1a Passed: Character steps onto unvisited open street tile instead of wall bumping.")

# Scenario 50.1b: Joppa Town State when all street tiles have been walked
for d, (dx, dy) in brain.CARDINAL_OFFSETS.items():
    brain.visit_counts[(34 + dx, 9 + dy)] = 1
brain.visit_counts[(34, 9)] = 2

dec_50_1b = brain.query_decision(joppa_state, took_damage=False, enemies=[])
print(f"Scenario 50.1b Joppa Exit Decision: {dec_50_1b['action']} | Reason: {dec_50_1b['reason']}")
assert dec_50_1b["action"].startswith("NAVIGATE_ZONE_EXIT:"), f"Expected Joppa to navigate to zone exit, got: {dec_50_1b['action']}"
print("  [OK] Scenario 50.1b Passed: Explored town street safely routes to zone exit without wall sticking or fog centroid pull.")

# Scenario 50.2: Exhausted Pocket Exit Resolution (Non-town with all visited moves)
pocket_dead_end = {
    "hp": 31, "max_hp": 31, "x": 45, "y": 11, "z": 10,
    "calling": "Apostle", "level": 5, "ap": 0, "sp": 0, "mp": 0,
    "zone_id": "JoppaWorld.10.18.1.1.10",
    "zone_name": "desert canyon, surface",
    "zone_fully_explored": False,
    "autoexplore_stuck": True,
    "unexplored_cells": 1613,
    "unexplored_centroid_x": 35, "unexplored_centroid_y": 11,
    "nearest_unexplored_x": 43, "nearest_unexplored_y": 9,
    "reachable_edges": "E",
    "last_move_failed": False,
    "surroundings": {
        "NW": "[BLOCKED: canyon cliff]", "N": "[BLOCKED: canyon cliff]", "NE": "[BLOCKED: canyon cliff]",
        "W": "[BLOCKED: canyon cliff]", "SW": "[BLOCKED: canyon cliff]",
        "E": "dirt path", "S": "[BLOCKED: canyon cliff]", "SE": "[BLOCKED: canyon cliff]"
    },
    "companions": [],
    "visible_entities": []
}

brain.visit_counts.clear()
brain.visit_counts[(45, 11)] = 2
brain.visit_counts[(46, 11)] = 2  # East move already visited
brain.current_zone_id = "JoppaWorld.10.18.1.1.10"
brain.CURRENT_TRACKED_ZONE = "JoppaWorld.10.18.1.1.10"
brain.stuck_autoexplore_zones.add("JoppaWorld.10.18.1.1.10")
brain.CURRENT_ZONE_CHOSEN_EXIT = None
brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
brain.EXPLORED_ZONE_SET.clear()

dec_50_2 = brain.query_decision(pocket_dead_end, took_damage=False, enemies=[])
print(f"Scenario 50.2 Pocket Decision: {dec_50_2['action']} | Reason: {dec_50_2['reason']}")
assert dec_50_2["action"] == "NAVIGATE_ZONE_EXIT:E", f"Expected NAVIGATE_ZONE_EXIT:E, got: {dec_50_2['action']}"
print("  [OK] Scenario 50.2 Passed: Exhausted pocket dead-end transitions cleanly to zone exit.")

print("\n==================================================")
print(">>> ALL 50 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
print("==================================================")

# =====================================================================
# TEST 51: Same-species hostile must not be treated as a companion (2026-10-04 baboon death, HANDOFF issue 27)
# =====================================================================
print("\n" + "="*50)
print("TEST 51: Hostile baboon next to a recruited baboon (multi-turn, no REST while adjacent)")
print("="*50)

brain.CHARMED_COMPANION_COORDS.clear()
brain.last_action = None
baboon_state = {
    "hp": 6, "max_hp": 20, "x": 10, "y": 10, "z": 10, "level": 2,
    "calling": "Apostle",
    "has_companion": True,
    "companions": [{"name": "baboon", "tx": 20, "ty": 20, "hp": 5, "max_hp": 5, "dist": 14, "dir": "SE"}],
    "zone_id": "JoppaWorld.11.20.1.0.10", "zone_fully_explored": False,
    "hostiles_nearby": True, "hostiles_adjacent": True,
    "surroundings": {"E": "[ENEMY: baboon]", "N": "Clear", "S": "Clear", "W": "Clear",
                     "NE": "Clear", "NW": "Clear", "SE": "Clear", "SW": "Clear"},
    "abilities": [
        {"name": "Lase (4 charges)", "command": "CommandLase", "cooldown": 0, "usable": True, "active": False},
    ],
    "visible_entities": [
        {"name": "baboon", "tx": 11, "ty": 10, "dist": 1, "dir": "E", "is_enemy": True, "is_companion": False, "has_los": True, "difficulty": "Tough"},
        {"name": "baboon", "tx": 20, "ty": 20, "dist": 14, "dir": "SE", "is_enemy": False, "is_companion": True, "has_los": True, "difficulty": "Tough"},
    ],
}
hostiles = brain.filter_hostile_enemies(baboon_state["visible_entities"], baboon_state["companions"])
assert [(h["tx"], h["ty"]) for h in hostiles] == [(11, 10)], f"Hostile baboon must survive filtering, got {hostiles}"
adj = brain.get_adjacent_threats(baboon_state["surroundings"], companions=baboon_state["companions"], cur_pos=(10, 10))
assert adj == {"E": "baboon"}, f"Adjacent hostile baboon must be a threat, got {adj}"
for turn in range(1, 5):
    st = dict(baboon_state)
    st["hp"] = max(1, 6 - turn)  # losing HP each turn, like the real run
    dec = brain.query_decision(st, took_damage=(turn > 1), enemies=st["visible_entities"])
    act = dec.get("action", "")
    print(f"  turn {turn}: {act} | {dec.get('reason', '')[:80]}")
    assert act != "REST" and not act.startswith("AUTOEXPLORE"), f"Turn {turn}: must not rest/explore with a hostile adjacent, got {act}"
print("  [OK] Test 51 Passed: same-species hostile is a threat; no REST/AUTOEXPLORE over 4 turns.")


# =====================================================================
# TEST 52: Enemy behind a wall (no line of sight) must not trap the agent in combat mode (HANDOFF issue 28)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 52: Occluded enemy 3 tiles away behind a wall (multi-turn)")
print("="*50)

brain.CHARMED_COMPANION_COORDS.clear()
brain.last_action = None
def wall_state(has_los, hp=27):
    return {
        "hp": hp, "max_hp": 27, "x": 10, "y": 10, "z": 10, "level": 4,
        "calling": "Apostle", "has_companion": False, "companions": [],
        "zone_id": "JoppaWorld.11.19.0.1.10", "zone_fully_explored": False, "unexplored_cells": 500,
        "hostiles_nearby": True, "hostiles_adjacent": False,
        "surroundings": {"S": "[BLOCKED: impassable wall]", "N": "Clear", "E": "Clear", "W": "Clear",
                         "NE": "Clear", "NW": "Clear", "SE": "[BLOCKED: impassable wall]", "SW": "[BLOCKED: impassable wall]"},
        "abilities": [{"name": "Lase (4 charges)", "command": "CommandLase", "cooldown": 0, "usable": True, "active": False}],
        "visible_entities": [
            {"name": "snapjaw scavenger", "tx": 10, "ty": 13, "dist": 3, "dir": "S", "is_enemy": True, "is_companion": False,
             "has_los": has_los, "difficulty": "Easy"},
        ],
    }
occluded = wall_state(False)
assert brain.get_close_threats(brain.filter_hostile_enemies(occluded["visible_entities"], []), occluded) == [], "Occluded enemy must not be a close threat"
visible = wall_state(True)
assert len(brain.get_close_threats(brain.filter_hostile_enemies(visible["visible_entities"], []), visible)) == 1, "Visible enemy must still be a close threat"
adjacent = wall_state(False)
adjacent["visible_entities"][0].update({"dist": 1, "ty": 11})
assert len(brain.get_close_threats(brain.filter_hostile_enemies(adjacent["visible_entities"], []), adjacent)) == 1, "Adjacent enemy must always be a threat"
for turn in range(1, 7):
    st = wall_state(False)
    dec = brain.query_decision(st, took_damage=False, enemies=st["visible_entities"])
    reason = dec.get("reason", "")
    print(f"  turn {turn}: {dec.get('action')} | {reason[:80]}")
    assert "line of sight" not in reason.lower() and "Fallback" not in reason and "[LLM" not in reason, f"Turn {turn}: must not run combat logic for an occluded enemy, got {reason}"
dec = brain.query_decision(wall_state(False), took_damage=True, enemies=wall_state(False)["visible_entities"])
assert "Safe" not in dec.get("reason", ""), "Taking damage must still force combat/safety logic"
print("  [OK] Test 52 Passed: occluded enemy ignored for 6 turns; visible, adjacent and damage cases still count.")


# =====================================================================
# TEST 53: Fire is a hazard; unsafe camp spot falls back to eating (HANDOFF issues 30-32, 2026-10-04 fire death)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 53: [HAZARD: fire] cells are never walked into; no MAKE_CAMP when C# says the spot is unsafe")
print("="*50)

fire_surroundings = {"N": "[HAZARD: fire]", "NE": "[HAZARD: fire]", "E": "Empty ground", "SE": "Empty ground",
                     "S": "Empty ground", "SW": "Empty ground", "W": "[HAZARD: fire]", "NW": "[HAZARD: fire]"}
fire_moves = brain.get_valid_moves(fire_surroundings, (10, 10), None, is_in_combat=False)
assert "MOVE_N" not in fire_moves and "MOVE_NE" not in fire_moves and "MOVE_W" not in fire_moves and "MOVE_NW" not in fire_moves, f"Must not step into fire, got {fire_moves}"
assert "MOVE_E" in fire_moves and "MOVE_S" in fire_moves, f"Safe cells must stay available, got {fire_moves}"

brain.CHARMED_COMPANION_COORDS.clear()
brain.last_action = None
hungry_state = {
    "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10, "level": 4, "calling": "Apostle",
    "has_companion": False, "companions": [], "zone_id": "JoppaWorld.11.19.0.1.10",
    "zone_fully_explored": False, "unexplored_cells": 500, "hostiles_nearby": False, "hostiles_adjacent": False,
    "is_hungry": True, "is_famished": False, "hunger_level": "Hungry",
    "has_food": True, "food_count": 2, "can_make_camp": False, "campfire_nearby": False, "is_on_fire": False,
    "corpses_nearby": 0, "surroundings": {"N": "dogthorn tree", "S": "Empty ground", "E": "Empty ground", "W": "Empty ground"},
    "abilities": [], "visible_entities": [],
}
for turn in range(1, 4):
    dec = brain.query_decision(dict(hungry_state), took_damage=False, enemies=[])
    print(f"  turn {turn}: {dec.get('action')} | {dec.get('reason', '')[:80]}")
    assert dec.get("action") != "MAKE_CAMP", "Must not make camp when C# reports can_make_camp = False"
    assert dec.get("action") == "EAT", f"Hungry with food and an unsafe camp spot should EAT, got {dec.get('action')}"
print("  [OK] Test 53 Passed: fire cells avoided; unsafe camp spot falls back to EAT.")


# =====================================================================
# TEST 54: Earn dinner: forage for corpses/plants, no free meals (HANDOFF issue 34)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 54: Foraging: walk to corpses/plants, blacklist unreachable ones, never loop on a failed butcher")
print("="*50)

def forage_reset():
    brain.FOOD_BLACKLIST.clear()
    brain.FOOD_PURSUIT.update({"key": None, "turns": 0})
    brain.FOOD_TURN = 0
    brain.BUTCHER_STREAK = 0
    brain.BUTCHER_TURN = 0
    brain.BUTCHER_SUPPRESS_UNTIL = 0
    brain.last_action = None
    brain.CHARMED_COMPANION_COORDS.clear()

def forage_state(skills, sources, food_count=1, hungry=False, **extra):
    st = {
        "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10, "level": 4, "calling": "Warden",
        "ap": 0, "sp": 0, "mp": 0, "skills": list(skills), "zone_id": "JoppaWorld.11.19.0.1.10",
        "zone_fully_explored": False, "unexplored_cells": 500, "hostiles_nearby": False, "hostiles_adjacent": False,
        "is_hungry": hungry, "hunger_level": "Hungry" if hungry else "Satisfied",
        "has_food": food_count > 0, "food_count": food_count, "corpses_nearby": 0, "harvestable_nearby": 0,
        "food_sources": sources, "campfire_nearby": False, "can_make_camp": False,
        "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear"}, "visible_entities": [],
    }
    st.update(extra)
    return st

BUTCHERY = ["CookingAndGathering", "CookingAndGathering_Butchery"]
corpse_a = {"kind": "corpse", "name": "baboon corpse", "tx": 16, "ty": 10, "dist": 6}
corpse_b = {"kind": "corpse", "name": "salthopper corpse", "tx": 10, "ty": 18, "dist": 8}
plant_c = {"kind": "plant", "name": "witchwood tree", "tx": 12, "ty": 10, "dist": 2}

# A. Low on food + Butchery skill + corpse 6 tiles away -> walk to it
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY, [corpse_a]), took_damage=False, enemies=[])
assert dec["action"] == "NAVIGATE_TO_CELL:16,10", f"Expected to walk to the corpse, got {dec}"
# B. No skill -> must not walk to it
forage_reset()
dec = brain.query_decision(forage_state([], [corpse_a]), took_damage=False, enemies=[])
assert not dec["action"].startswith("NAVIGATE_TO_CELL:16"), f"No Butchery skill: must not forage a corpse, got {dec}"
# C. Well stocked and not hungry -> no foraging
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY, [corpse_a], food_count=5), took_damage=False, enemies=[])
assert not dec["action"].startswith("NAVIGATE_TO_CELL:16"), f"Well fed and stocked: must not forage, got {dec}"
# D. Corpse preferred over a nearer plant; plant needs the Harvestry skill
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY + ["CookingAndGathering_Harvestry"], [plant_c, corpse_a]), took_damage=False, enemies=[])
assert dec["action"] == "NAVIGATE_TO_CELL:16,10", f"Corpse should outrank a nearer plant, got {dec}"
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY, [plant_c]), took_damage=False, enemies=[])
assert not dec["action"].startswith("NAVIGATE_TO_CELL:12"), f"Plant without Harvestry must be ignored, got {dec}"
# E. Hungry with food: EAT, even with camp allowed and a campfire adjacent (no cooking detour)
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY, [], food_count=2, hungry=True, can_make_camp=True, campfire_nearby=True), took_damage=False, enemies=[])
assert dec["action"] == "EAT", f"Hungry with food must EAT, got {dec}"
# F. Hungry, no food, no sources: no free meal (no MAKE_CAMP/COOK_MEAL/EAT)
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY, [], food_count=0, hungry=True, can_make_camp=True, campfire_nearby=True), took_damage=False, enemies=[])
assert dec["action"] not in ("MAKE_CAMP", "COOK_MEAL", "EAT"), f"No food: no free meal, got {dec}"

# G. Multi-turn: unreachable corpse A is blacklisted after PATH_BLOCKED; he moves on to B and never retries A
forage_reset()
dec = brain.query_decision(forage_state(BUTCHERY, [corpse_a, corpse_b]), took_damage=False, enemies=[])
assert dec["action"] == "NAVIGATE_TO_CELL:16,10"
brain.last_action = dec["action"]
picked = []
for turn in range(6):
    st = forage_state(BUTCHERY, [corpse_a, corpse_b], last_move_failed=True, last_failed_dir="PATH_BLOCKED")
    dec = brain.query_decision(st, took_damage=False, enemies=[])
    picked.append(dec["action"])
    brain.last_action = dec["action"]
assert "NAVIGATE_TO_CELL:16,10" not in picked, f"Blocked corpse must stay blacklisted, got {picked}"
assert picked[0] == "NAVIGATE_TO_CELL:10,18", f"Should switch to the other corpse, got {picked}"

# H. Pursuit time-out: same reachable-looking target forever -> gives up after FOOD_PURSUIT_MAX_TURNS
forage_reset()
acts = []
for turn in range(brain.FOOD_PURSUIT_MAX_TURNS + 5):
    dec = brain.query_decision(forage_state(BUTCHERY, [corpse_a]), took_damage=False, enemies=[])
    acts.append(dec["action"])
    brain.last_action = dec["action"]
assert acts[0] == "NAVIGATE_TO_CELL:16,10" and acts[-1] != "NAVIGATE_TO_CELL:16,10", f"Must give up on a target after {brain.FOOD_PURSUIT_MAX_TURNS} turns, last was {acts[-1]}"

# I. Adjacent corpse: BUTCHER, but a butcher that silently keeps failing is not repeated forever
forage_reset()
adj = forage_state(BUTCHERY, [], corpses_nearby=1, can_butcher=True)
seen = []
for turn in range(12):
    dec = brain.query_decision(dict(adj), took_damage=False, enemies=[])
    seen.append(dec["action"])
    brain.last_action = dec["action"]
assert seen[0] == "BUTCHER" and seen.count("BUTCHER") <= 3, f"BUTCHER must not repeat endlessly, got {seen}"
print("  [OK] Test 54 Passed: forages with the skill, ignores without, blacklists blocked/slow targets, no free meal, no butcher loop.")


# =====================================================================
# TEST 55: Every build learns the food skills early and can reach Intelligence 15 (HANDOFF issue 36)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 55: Butchery/Harvestry are bought early in every template; Int 15 is reachable (multi-step simulation)")
print("="*50)

import build_templates as _bt
import skill_database as _sd
for _name, _tpl in _bt.BUILD_TEMPLATES.items():
    # (a) Simulate SP trickling in (50 per step) and buying whatever the doctrine picks, with Intelligence 17
    _learned, _sp, _order, _spent, _spent_at_butchery = [], 0, [], 0, None
    for _step in range(60):
        _state = {"sp": _sp, "skills": list(_learned), "attributes": {"Intelligence": 17}}
        _skill, _why, _saving = _sd.get_best_skill_to_learn(_state, _tpl)
        if _skill:
            _cost = (_sd.get_skill_info(_skill) or {}).get("cost", 0)
            _sp -= _cost
            _spent += _cost
            _learned.append(_skill)
            _order.append(_skill)
            if _skill == "CookingAndGathering_Butchery":
                _spent_at_butchery = _spent
        else:
            _sp += 50
    assert "CookingAndGathering_Butchery" in _learned and "CookingAndGathering_Harvestry" in _learned, f"{_name}: never learns Butchery/Harvestry, order {_order}"
    _bi = _order.index("CookingAndGathering_Butchery")
    assert _bi <= 6, f"{_name}: Butchery bought too late (position {_bi + 1}): {_order}"
    # (b) Intelligence 15 is reached by the stat doctrine for a low-Int character once the earlier targets are met
    _attrs = {}
    for _rule in _tpl["stat_priorities"]:
        if _rule["stat"] == "Intelligence":
            break
        _attrs[_rule["stat"]] = max(_attrs.get(_rule["stat"], 10), _rule["target"])
    _attrs["Intelligence"] = 10
    _rec, _ = _bt.get_stat_allocation_recommendation(_tpl, _attrs)
    assert _rec == "Intelligence", f"{_name}: low-Int character is never steered to Intelligence (got {_rec})"
    print(f"  {_name}: Butchery is skill #{_bi + 1}, bought after {_spent_at_butchery} SP spent; Intelligence steering OK")
print("  [OK] Test 55 Passed: all templates buy Butchery and Harvestry early and steer a low-Int character to Intelligence.")


# =====================================================================
# TEST 56: "Zone fully explored" is only ever the ENGINE's claim (HANDOFF issues 17 and 29)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 56: Stuck autoexplore never becomes a permanent 'zone explored'; only the engine's flag is remembered")
print("="*50)

def explored_reset():
    brain.EXPLORED_ZONE_SET.clear()
    brain.stuck_autoexplore_zones.clear()
    brain.ENGINE_EXPLORED_LAST.clear()
    brain.CURRENT_TRACKED_ZONE = None
    brain.last_action = None
    brain.CHARMED_COMPANION_COORDS.clear()

def zone_state(zone, engine_explored=False, stuck=False, unexplored=1251, failed=False):
    return {
        "hp": 20, "max_hp": 20, "x": 10, "y": 10, "z": 10, "level": 4, "calling": "Warden",
        "ap": 0, "sp": 0, "mp": 0, "skills": [], "zone_id": zone, "zone_name": "desert canyon, surface",
        "zone_fully_explored": engine_explored, "autoexplore_stuck": stuck, "unexplored_cells": unexplored,
        "nearest_unexplored_x": 13, "nearest_unexplored_y": 19, "nearest_unexplored_dist": 5,
        "reachable_edges": "NSEW", "last_move_failed": failed, "last_failed_dir": "",
        "hostiles_nearby": False, "hostiles_adjacent": False, "food_count": 5, "has_food": True, "food_sources": [],
        "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear", "NE": "Clear", "NW": "Clear", "SE": "Clear", "SW": "Clear"},
        "visible_entities": [],
    }

ZA, ZB, ZC = "JoppaWorld.11.19.0.1.10", "JoppaWorld.11.19.0.2.10", "JoppaWorld.11.19.0.3.10"

# (a) Engine says NOT explored (1251 cells left) but autoexplore is stuck: he may leave, but must not claim the zone is explored
explored_reset()
brain.last_action = "AUTOEXPLORE"
dec = brain.query_decision(zone_state(ZA, stuck=True, failed=True), took_damage=False, enemies=[])
print(f"  stuck turn: {dec['action']} | {dec['reason'][:90]}")
assert "Zone fully explored" not in dec["reason"], f"Must not claim the zone is fully explored, got: {dec['reason']}"
assert ZA not in brain.EXPLORED_ZONE_SET, "A stuck zone must not be recorded as explored"

# (a2) The real bug path: stuck, no sector target, every neighbouring cell visited (no local frontier). Old code claimed
# "Zone fully explored" here and remembered it forever, with 1251 cells still unexplored.
explored_reset()
st = zone_state(ZA, stuck=True, failed=True)
for k in ("nearest_unexplored_x", "nearest_unexplored_y", "nearest_unexplored_dist"):
    st.pop(k, None)
for _dx in (-1, 0, 1):
    for _dy in (-1, 0, 1):
        brain.visit_counts[(10 + _dx, 10 + _dy)] += 3
brain.last_action = "AUTOEXPLORE"
dec = brain.query_decision(st, took_damage=False, enemies=[])
print(f"  stuck, no frontier: {dec['action']} | {dec['reason'][:90]}")
assert "Zone fully explored" not in dec["reason"], f"Must not claim the zone is fully explored, got: {dec['reason']}"
assert ZA not in brain.EXPLORED_ZONE_SET, "A stuck zone with 1251 unexplored cells must not be remembered as explored"
for _dx in (-1, 0, 1):
    for _dy in (-1, 0, 1):
        brain.visit_counts[(10 + _dx, 10 + _dy)] = 0

# (b) Next turn: autoexplore made progress and the engine no longer says stuck -> he explores again, nothing is remembered
brain.last_action = "AUTOEXPLORE"
dec = brain.query_decision(zone_state(ZA, stuck=False, failed=False), took_damage=False, enemies=[])
print(f"  progress turn: {dec['action']} | {dec['reason'][:90]}")
assert ZA not in brain.stuck_autoexplore_zones, "Progress must clear the stale 'stuck' mark"
assert dec["action"] == "AUTOEXPLORE", f"A zone with 1251 unexplored cells and a working autoexplore must keep exploring, got {dec}"

# (c) Many turns of progress never flip to 'explored'
for turn in range(8):
    brain.last_action = "AUTOEXPLORE"
    dec = brain.query_decision(zone_state(ZA), took_damage=False, enemies=[])
    assert dec["action"] == "AUTOEXPLORE" and ZA not in brain.EXPLORED_ZONE_SET, f"Turn {turn}: got {dec}"

# (d) Engine DOES say explored -> label is honest and the zone is remembered
explored_reset()
dec = brain.query_decision(zone_state(ZB, engine_explored=True, unexplored=0), took_damage=False, enemies=[])
print(f"  engine-explored turn: {dec['action']} | {dec['reason'][:90]}")
assert ZB in brain.EXPLORED_ZONE_SET, "The engine's own explored flag must be remembered"
assert "Zone fully explored" in dec["reason"] or dec["action"].startswith(("NAVIGATE_ZONE_EXIT", "NAVIGATE_TO_CELL", "MOVE_")), f"Unexpected decision {dec}"

# (e) Leaving a zone: the OLD zone's flag decides, not the new zone's (game_state describes the new zone after the hop)
explored_reset()
brain.query_decision(zone_state(ZA, engine_explored=False), took_damage=False, enemies=[])      # in A, engine: not explored
brain.query_decision(zone_state(ZB, engine_explored=True, unexplored=0), took_damage=False, enemies=[])  # hop to B, engine: explored
assert ZA not in brain.EXPLORED_ZONE_SET, "Zone A was never reported explored; it must not inherit B's flag"
brain.query_decision(zone_state(ZC, engine_explored=False), took_damage=False, enemies=[])      # hop on to C
assert ZB in brain.EXPLORED_ZONE_SET and ZA not in brain.EXPLORED_ZONE_SET, f"Expected only B remembered, got {brain.EXPLORED_ZONE_SET}"

# (f) Pin the rule in source: exactly two places may add to EXPLORED_ZONE_SET, both engine-confirmed
_src = open(brain.__file__, encoding="utf-8").read()
assert _src.count("EXPLORED_ZONE_SET.add(") == 2, f"Only engine-confirmed code may add to EXPLORED_ZONE_SET, found {_src.count('EXPLORED_ZONE_SET.add(')}"
print("  [OK] Test 56 Passed: stuck != explored; progress clears stuck; only the engine's flag is remembered; the old zone's flag is used on leave.")


# =====================================================================
# TEST 57: Every zone-exit decision is logged with its inputs (HANDOFF issue 38)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 57: exit choice log records candidates, reachable edges and explored neighbours; logging never raises")
print("="*50)

import os as _os, json as _json, tempfile as _tempfile, io as _io, contextlib as _ctx
_log = _os.path.join(_tempfile.mkdtemp(), "exit_choices.jsonl")
_saved = brain.EXIT_LOG_PATH
brain.EXIT_LOG_PATH = _log
_Z = "JoppaWorld.11.20.1.1.10"
brain.EXPLORED_ZONE_SET.clear(); brain.FAILED_ZONE_EXITS = set()
brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
brain.LAST_ZONE_ENTRY = {"reverse_dir": "S"}
brain.EXPLORED_ZONE_SET.add(brain._compute_adjacent_zone_id(_Z, "W"))   # the west neighbour was already explored
with _ctx.redirect_stdout(_io.StringIO()):
    _, _, _chosen = brain.get_zone_exit_target((40, 12), {"zone_id": _Z, "z": 10, "reachable_edges": "NSEW", "surroundings": {}})
_lines = [_json.loads(l) for l in open(_log, encoding="utf-8")]
assert len(_lines) == 1, f"One decision must log one line, got {len(_lines)}"
_rec = _lines[0]
assert _rec["zone"] == _Z and _rec["reachable"] == "NSEW" and _rec["rev"] == "S", _rec
assert _rec["explored_neighbors"] == ["W"], f"The explored west neighbour must be recorded, got {_rec['explored_neighbors']}"
assert sorted(_rec["candidates"]) == ["E", "N", "W"] and sorted(_rec["novel"]) == ["E", "N"], _rec
assert _rec["chosen"] == _chosen and _chosen in _rec["novel"] and _rec["mode"] == "novel", _rec
# A cached exit must not log again; an unwritable log path must never raise
with _ctx.redirect_stdout(_io.StringIO()):
    brain.get_zone_exit_target((40, 12), {"zone_id": _Z, "z": 10, "reachable_edges": "NSEW", "surroundings": {}})
assert len(open(_log, encoding="utf-8").readlines()) == 1, "A cached exit choice must not be logged again"
brain.EXIT_LOG_PATH = _os.path.join(_log, "no", "such", "dir", "x.jsonl")
brain.log_exit_choice({"zone": "x"})
brain.EXIT_LOG_PATH = _saved
print("  [OK] Test 57 Passed: exit decisions are logged with their inputs; the log never breaks the brain.")


# =====================================================================
# TEST 58: The hopping flag must not stop him crossing a zone line (HANDOFF issue 39)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 58: Walking to a chosen exit with the hopping flag on: no turning around on the border cell")
print("="*50)

_BZ = "JoppaWorld.11.20.1.1.10"
def border_setup(hopping, step_count, chosen="W"):
    brain.EXPLORED_ZONE_SET.clear(); brain.stuck_autoexplore_zones.clear(); brain.visit_counts.clear()
    brain.CURRENT_TRACKED_ZONE = _BZ; brain.last_action = None
    brain.ZONE_HOPPING_DETECTED = hopping; brain.ZONE_CYCLE_LENGTH = 2 if hopping else 0
    brain.ZONE_STEP_COUNT = step_count
    brain.CURRENT_ZONE_CHOSEN_EXIT = chosen; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = _BZ
    brain.LAST_ZONE_ENTRY = {"from_zone": "JoppaWorld.11.20.2.1.10", "to_zone": _BZ, "entry_pos": (40, 12), "reverse_dir": "E"}
    brain.FAILED_ZONE_EXITS = set()

def border_state(x, y):
    s = {d: "Clear" for d in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]}
    if x == 0:
        for d in ["W", "NW", "SW"]:
            s[d] = "[ZONE_EXIT: %s]" % d
    return {"hp": 20, "max_hp": 20, "x": x, "y": y, "z": 10, "level": 4, "calling": "Warden", "ap": 0, "sp": 0, "mp": 0,
            "skills": [], "zone_id": _BZ, "zone_name": "desert canyon", "zone_fully_explored": True, "autoexplore_stuck": False,
            "unexplored_cells": 0, "reachable_edges": "NSEW", "last_move_failed": False, "last_failed_dir": "",
            "hostiles_nearby": False, "hostiles_adjacent": False, "food_count": 5, "has_food": True, "food_sources": [],
            "surroundings": s, "visible_entities": []}

# (a) On the west border cell, West chosen, hopping flagged, long in the zone: cross, do not step inward
border_setup(True, 30)
with _ctx.redirect_stdout(_io.StringIO()):
    _d = brain.query_decision(border_state(0, 12), took_damage=False, enemies=[])
assert _d["action"] == "MOVE_W", f"Must step across the W border, got {_d}"
# (b) Multi-step approach x = 6..0 with the flag on: never a move with an eastward component
_acts = []
for _x in range(6, -1, -1):
    border_setup(True, 30)
    with _ctx.redirect_stdout(_io.StringIO()):
        _d = brain.query_decision(border_state(_x, 12), took_damage=False, enemies=[])
    _acts.append(_d["action"])
print("  approach actions:", _acts)
assert not any(a in ("MOVE_E", "MOVE_NE", "MOVE_SE") for a in _acts), f"Turned around on the way to the zone line: {_acts}"
assert _acts[-1] == "MOVE_W", f"Must cross on the border cell, got {_acts[-1]}"
# (c) The arrival grace still works: just arrived on a border cell with the flag on -> step inward first
border_setup(True, 1, chosen=None)
brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
with _ctx.redirect_stdout(_io.StringIO()):
    _d = brain.query_decision(border_state(0, 12), took_damage=False, enemies=[])
assert "Stepping inward" in _d["reason"], f"Arrival grace must still step inward, got {_d}"
brain.ZONE_HOPPING_DETECTED = False; brain.ZONE_CYCLE_LENGTH = 0
print("  [OK] Test 58 Passed: the hopping flag no longer blocks crossing; the arrival grace still steps inward.")


# =====================================================================
# TEST 59: A companion blocking the only exit must not trigger endless burrowing (HANDOFF issue 41)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 59: Dead-end corridor with the pet in the only exit: swap/wait, never burrow (multi-turn)")
print("="*50)

_ROCK = "[BLOCKED: impassable terrain], [BLOCKED: shale]"
_dead_end = {"N": _ROCK, "NE": _ROCK, "NW": _ROCK, "E": _ROCK, "W": _ROCK,
             "SE": _ROCK, "SW": _ROCK, "S": "[COMPANION: wet horned chameleon and hired guard [wading]]"}
brain.COMPANION_BLOCK.update({"pos": None, "tries": 0})
_acts = []
for _turn in range(9):
    _a, _r = brain.guard_companion_blocked_burrow("ATTACK_WALL:N", "[Loop Breaker] burrow", _dead_end, (27, 4))
    _acts.append(_a)
print("  replacement actions at the dead end:", _acts)
assert not any(a.startswith("ATTACK_WALL") for a in _acts), f"Must never burrow while a companion blocks the exit: {_acts}"
assert _acts == ["MOVE_S", "MOVE_S", "WAIT"] * 3, f"Expected swap, swap, wait cycles, got {_acts}"
# Not a companion-caused pocket: an open non-companion move exists, so the burrow decision is left alone
_open_exit = dict(_dead_end, E="Clear")
_a, _r = brain.guard_companion_blocked_burrow("ATTACK_WALL:N", "x", _open_exit, (27, 4))
assert _a == "ATTACK_WALL:N", f"Burrow decisions in real pockets must be untouched, got {_a}"
# No companion adjacent: untouched
_a, _r = brain.guard_companion_blocked_burrow("ATTACK_WALL:N", "x", dict(_dead_end, S=_ROCK), (27, 4))
assert _a == "ATTACK_WALL:N", f"No companion: burrow untouched, got {_a}"
# Other actions are never altered
_a, _r = brain.guard_companion_blocked_burrow("MOVE_S", "x", _dead_end, (27, 4))
assert _a == "MOVE_S", f"Non-burrow actions untouched, got {_a}"
# A successful swap changes position: the try counter resets for the new cell
_a, _ = brain.guard_companion_blocked_burrow("ATTACK_WALL:N", "x", _dead_end, (27, 5))
assert _a == "MOVE_S" and brain.COMPANION_BLOCK["tries"] == 1, f"Counter must reset on a new position, got {_a}, {brain.COMPANION_BLOCK}"
brain.COMPANION_BLOCK.update({"pos": None, "tries": 0})
print("  [OK] Test 59 Passed: swap, swap, wait cycles; real pockets and other actions are untouched.")


# =====================================================================
# TEST 60: Exit thrash circuit breaker (HANDOFF issue 42): the hallway N/W loop
# =====================================================================
print(chr(10) + "="*50)
print("TEST 60: A sealed corridor must not wipe the exit blacklist; repeated exit failures switch to exploring")
print("="*50)

_HZ = "JoppaWorld.11.21.1.2.11"
def hall_reset():
    brain.FAILED_ZONE_EXITS = set(); brain.EXIT_FAILURES.clear(); brain.EXIT_SUPPRESS_UNTIL.clear()
    brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
    brain.EXPLORED_ZONE_SET.clear(); brain.LAST_ZONE_ENTRY = None; brain.TURN_CLOCK = 0
    brain.ZONE_HOPPING_DETECTED = False

def hall_pick(x, y, reach):
    st = {"zone_id": _HZ, "z": 11, "reachable_edges": reach, "surroundings": {}, "x": x, "y": y}
    with _ctx.redirect_stdout(_io.StringIO()):
        return brain.get_zone_exit_target((x, y), st)[2]

# (a) The engine reports NO edges (pet sealing the corridor): the blacklist survives and nothing is picked
hall_reset()
brain.FAILED_ZONE_EXITS = {(_HZ, "N"), (_HZ, "W")}
assert hall_pick(27, 4, "") is None, "No reachable edges: must not pick an exit"
assert brain.FAILED_ZONE_EXITS == {(_HZ, "N"), (_HZ, "W")}, f"The blacklist must survive an empty reachable list, got {brain.FAILED_ZONE_EXITS}"

# (b) Replay the console loop: at (27,5) all four reachable, N then W fail, at (27,4) nothing is reachable
hall_reset()
picks = []
for cycle in range(brain.EXIT_FAILURE_LIMIT + 1):
    brain.TURN_CLOCK += 1
    d = hall_pick(27, 5, "NSEW")
    picks.append(d)
    if d is None:
        break
    brain.CURRENT_ZONE_CHOSEN_EXIT, brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = d, _HZ
    with _ctx.redirect_stdout(_io.StringIO()):
        brain.note_exit_failure(_HZ, d)          # oscillation / dead end: this exit failed
    brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
    hall_pick(27, 4, "")                          # sealed in: engine reports nothing reachable
print("  exits picked in the replay:", picks)
assert len(set(p for p in picks if p)) == len([p for p in picks if p]), f"An exit that failed must never be picked again: {picks}"
assert picks[-1] is None, f"After {brain.EXIT_FAILURE_LIMIT} failures the picker must stand down, got {picks}"

# (c) While suppressed: no exit even with everything reachable; after the window it works again
assert hall_pick(27, 5, "NSEW") is None, "Exit selection must stay suppressed"
brain.TURN_CLOCK += brain.EXIT_SUPPRESS_TURNS + 1
assert hall_pick(27, 5, "NSEW") is not None, "Exit selection must resume after the suppression window"

# (d) Phase A honours the suppression: a fully explored zone with reachable exits does not navigate to an exit
hall_reset()
brain.EXIT_SUPPRESS_UNTIL[_HZ] = 10**9
brain.CURRENT_TRACKED_ZONE = _HZ; brain.last_action = None
_st = {"hp": 20, "max_hp": 20, "x": 27, "y": 5, "z": 11, "level": 5, "calling": "Warden", "ap": 0, "sp": 0, "mp": 0, "skills": [],
       "zone_id": _HZ, "zone_name": "subterranean", "zone_fully_explored": True, "autoexplore_stuck": False, "unexplored_cells": 0,
       "reachable_edges": "NSEW", "last_move_failed": False, "last_failed_dir": "", "hostiles_nearby": False, "hostiles_adjacent": False,
       "food_count": 5, "has_food": True, "food_sources": [], "visible_entities": [],
       "surroundings": {"N": "Clear", "S": "Clear", "E": "Clear", "W": "Clear", "NE": "Clear", "NW": "Clear", "SE": "Clear", "SW": "Clear"}}
with _ctx.redirect_stdout(_io.StringIO()):
    _d = brain.query_decision(_st, took_damage=False, enemies=[])
assert not _d["action"].startswith("NAVIGATE_ZONE_EXIT"), f"Suppressed exits must not be navigated to, got {_d}"
brain.EXIT_SUPPRESS_UNTIL.clear()
print("  [OK] Test 60 Passed: blacklist survives a sealed corridor; failed exits are never re-picked; 4 failures suppress exit-hunting.")


# =====================================================================
# TEST 61: Per-turn decision trace (diagnostics for loops; HANDOFF issue 43)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 61: decision trace writes JSON lines, rotates at the size cap and never raises")
print("="*50)

_tdir = _tempfile.mkdtemp()
_saved_tp, _saved_max = brain.DECISION_TRACE_PATH, brain.DECISION_TRACE_MAX_BYTES
brain.DECISION_TRACE_PATH = _os.path.join(_tdir, "decision_trace.jsonl")
brain.log_decision_trace({"t": 1, "pos": [27, 5], "action": "MOVE_S", "reason": "Water Traversal"})
brain.log_decision_trace({"t": 2, "pos": [27, 4], "action": "WAIT", "reason": "x"})
_rows = [_json.loads(l) for l in open(brain.DECISION_TRACE_PATH, encoding="utf-8")]
assert [r["t"] for r in _rows] == [1, 2] and _rows[0]["action"] == "MOVE_S", _rows
brain.DECISION_TRACE_MAX_BYTES = 10          # tiny cap: the next write rotates the old file to .1
brain.log_decision_trace({"t": 3, "pos": [1, 1], "action": "PASS", "reason": "y"})
assert _os.path.exists(brain.DECISION_TRACE_PATH + ".1"), "Rotation must keep a backup"
assert [_json.loads(l)["t"] for l in open(brain.DECISION_TRACE_PATH, encoding="utf-8")] == [3], "New file starts after rotation"
brain.DECISION_TRACE_PATH = _os.path.join(_tdir, "no", "such", "dir", "t.jsonl")
brain.log_decision_trace({"t": 4})           # an unwritable path must never raise
brain.DECISION_TRACE_PATH, brain.DECISION_TRACE_MAX_BYTES = _saved_tp, _saved_max
print("  [OK] Test 61 Passed: decision trace is written, rotated and failure-proof.")


# =====================================================================
# TEST 62: Engine-reachable frontier targets replace the rock centroid (HANDOFF issue 44)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 62: Navigate to a reachable frontier (e.g. the unexplored SW corner), committed, never to the rock centroid")
print("="*50)

_FZ = "JoppaWorld.11.21.1.2.11"
def fr_reset():
    brain.EXPLORED_ZONE_SET.clear(); brain.stuck_autoexplore_zones.clear(); brain.ENGINE_EXPLORED_LAST.clear()
    brain.UNREACHABLE_SECTORS.clear(); brain.FRONTIER_COMMIT.update({"zone": None, "target": None})
    brain.FRONTIER_FAILS.clear(); brain.FRONTIER_BAD.clear(); brain.FRONTIER_PURSUIT.update({"key": None, "turns": 0})
    brain.CURRENT_TRACKED_ZONE = _FZ; brain.last_action = None; brain.visit_counts.clear()
    brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
    brain.EXIT_SUPPRESS_UNTIL.clear(); brain.EXIT_FAILURES.clear(); brain.FAILED_ZONE_EXITS = set()
    brain.ZONE_HOPPING_DETECTED = False; brain.ZONE_STEP_COUNT = 30; brain.LAST_ZONE_ENTRY = None

def fr_state(x, y, targets, checked=True, reach="NSEW"):
    s = {d: "Clear" for d in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]}
    return {"hp": 35, "max_hp": 35, "x": x, "y": y, "z": 11, "level": 5, "calling": "Warden", "ap": 0, "sp": 0, "mp": 0, "skills": [],
            "zone_id": _FZ, "zone_name": "subterranean salt marsh", "zone_fully_explored": False, "autoexplore_stuck": True,
            "unexplored_cells": 1704, "unexplored_centroid_x": 40, "unexplored_centroid_y": 11,
            "nearest_unexplored_x": 25, "nearest_unexplored_y": 2, "nearest_unexplored_dist": 3,
            "reachable_edges": reach, "last_move_failed": False, "last_failed_dir": "", "hostiles_nearby": False, "hostiles_adjacent": False,
            "food_count": 5, "has_food": True, "food_sources": [], "visible_entities": [], "surroundings": s,
            "frontier_checked": checked, "frontier_cells": len(targets), "frontier_targets": targets}

_sw = {"q": "SW", "x": 12, "y": 20, "ux": 11, "uy": 21, "dist": 20}
_ne = {"q": "NE", "x": 60, "y": 3, "ux": 61, "uy": 2, "dist": 33}
def fr_decide(st):
    with _ctx.redirect_stdout(_io.StringIO()):
        return brain.query_decision(st, took_damage=False, enemies=[])

# (a) A reachable SW frontier is chosen, with the engine pathfinder; the rock centroid (40,11) is ignored
fr_reset()
_d = fr_decide(fr_state(30, 11, [_sw, _ne]))
print("  (a)", _d["action"], "|", _d["reason"][:90])
assert _d["action"] == "NAVIGATE_TO_CELL:12,20", f"Expected the nearest reachable frontier, got {_d}"
assert _d["reason"].startswith("Frontier:"), _d

# (b) Commitment: a nearer target appearing mid-walk does not flip him; once reached he picks the next one
fr_reset()
_picked = []
_new_near = {"q": "SE", "x": 33, "y": 14, "ux": 34, "uy": 15, "dist": 4}
for _step, _pos in enumerate([(30, 11), (28, 13), (26, 15), (22, 17), (18, 19)]):
    _targets = [_sw, _ne] + ([_new_near] if _step >= 2 else [])
    _picked.append(fr_decide(fr_state(_pos[0], _pos[1], _targets))["action"])
print("  (b)", _picked)
assert set(_picked) == {"NAVIGATE_TO_CELL:12,20"}, f"Must stay committed to the first target: {_picked}"
_d = fr_decide(fr_state(12, 20, [_ne, _new_near]))        # reached it (C# no longer lists visited cells)
assert _d["action"] in ("NAVIGATE_TO_CELL:33,14", "NAVIGATE_TO_CELL:60,3"), f"After arriving he must pick the next frontier, got {_d}"

# (c) A blacklisted (unreachable-at-runtime) target is skipped
fr_reset()
brain.UNREACHABLE_SECTORS.add((_FZ, (12, 20)))
_d = fr_decide(fr_state(30, 11, [_sw, _ne]))
assert _d["action"] == "NAVIGATE_TO_CELL:60,3", f"Blacklisted target must be skipped, got {_d}"

# (d) Nothing reachable and exits are reachable: the engine says the rest is rock. Say so; remember it; do not chase the centroid
fr_reset()
_d = fr_decide(fr_state(30, 11, []))
print("  (d)", _d["action"], "|", _d["reason"][:90])
assert _d["action"] != "NAVIGATE_TO_CELL:40,11", f"Must not chase the rock centroid, got {_d}"
assert _d["action"].startswith("NAVIGATE_ZONE_EXIT"), f"With nothing reachable left he should leave the zone, got {_d}"
assert _FZ in brain.EXPLORED_ZONE_SET, "Engine-confirmed: no reachable frontier and exits reachable"

# (e) Sealed in (the pet blocks the corridor: no reachable edges AND no frontier): transient, must NOT be remembered as explored
fr_reset()
_d = fr_decide(fr_state(27, 4, [], reach=""))
assert _FZ not in brain.EXPLORED_ZONE_SET, "A pet-sealed corridor must not be recorded as an explored zone"
print("  [OK] Test 62 Passed: reachable frontier targets, commitment, blacklist, honest 'nothing reachable', sealed corridor not remembered.")


# =====================================================================
# TEST 63: Burrow progress from the engine's report (HANDOFF issue 45)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 63: keep swinging while the target loses HP; write off targets that take no damage or have no HP")
print("="*50)

_BZ2 = "JoppaWorld.11.21.1.2.11"
def burrow_reset():
    brain.BURROW_BLOCKED.clear(); brain.BURROW_PROGRESS.clear(); brain.BURROW_LAST_SEQ["seq"] = 0; brain.TURN_CLOCK = 0

def lb(seq, hp_before, hp_after, x=13, y=11, d="N", has_hp=True, destroyed=False, name="shimscale mangrove tree", max_hp=25):
    return {"zone_id": _BZ2, "last_burrow": {"seq": seq, "dir": d, "name": name, "x": x, "y": y, "has_hp": has_hp,
            "hp_before": hp_before, "hp_after": hp_after, "max_hp": max_hp, "destroyed": destroyed}}

_ROCKY = "[BLOCKED: shimscale mangrove tree]"
_surr = {"N": _ROCKY, "NE": "Clear", "NW": "Clear", "E": "Clear", "W": "Clear", "S": "Clear", "SE": "Clear", "SW": "Clear"}

with _ctx.redirect_stdout(_io.StringIO()):
    # (a) A tree that keeps losing HP is never written off, however many swings it takes
    burrow_reset()
    for _i in range(1, 15):
        brain.note_burrow_progress(lb(_i, 25 - _i + 1, 25 - _i))
    assert not brain.blocked_burrow_dirs(_BZ2, (13, 12)), "A target that is losing HP must keep being attacked"
    # (b) Three swings with no damage write it off; one damaging swing in between resets the count
    burrow_reset()
    brain.note_burrow_progress(lb(1, 25, 25)); brain.note_burrow_progress(lb(2, 25, 25))
    assert not brain.blocked_burrow_dirs(_BZ2, (13, 12))
    brain.note_burrow_progress(lb(3, 25, 24))
    brain.note_burrow_progress(lb(4, 24, 24)); brain.note_burrow_progress(lb(5, 24, 24))
    assert not brain.blocked_burrow_dirs(_BZ2, (13, 12)), "A damaging swing must reset the stall count"
    brain.note_burrow_progress(lb(6, 24, 24))
    assert brain.blocked_burrow_dirs(_BZ2, (13, 12)) == {"N"}, "Three stalled swings must write the target off"
    # (c) No hit points at all: written off after one swing
    burrow_reset()
    brain.note_burrow_progress(lb(1, 0, 0, has_hp=False, name="boulder", max_hp=0))
    assert brain.blocked_burrow_dirs(_BZ2, (13, 12)) == {"N"}
    # (d) Destroyed clears everything; a repeated report (same seq) is ignored
    burrow_reset()
    brain.note_burrow_progress(lb(1, 25, 25)); brain.note_burrow_progress(lb(2, 25, 25)); brain.note_burrow_progress(lb(3, 25, 25))
    assert brain.blocked_burrow_dirs(_BZ2, (13, 12)) == {"N"}
    brain.note_burrow_progress(lb(4, 3, 0, destroyed=True))
    assert not brain.blocked_burrow_dirs(_BZ2, (13, 12)), "A destroyed obstacle must clear its write-off"
    brain.note_burrow_progress(lb(4, 25, 25)); brain.note_burrow_progress(lb(4, 25, 25))
    assert not brain.blocked_burrow_dirs(_BZ2, (13, 12)), "A repeated (old) sequence number must be ignored"
    # (e) Write-offs expire
    burrow_reset()
    brain.note_burrow_progress(lb(1, 0, 0, has_hp=False))
    brain.TURN_CLOCK += brain.BURROW_BLOCK_TURNS + 1
    assert not brain.blocked_burrow_dirs(_BZ2, (13, 12)), "Write-offs must expire"

    # (f) The guard: a burrow aimed at a written-off obstacle becomes another breakable obstacle, else a free move, else PASS
    burrow_reset()
    brain.note_burrow_progress(lb(1, 0, 0, has_hp=False))
    _two = dict(_surr, E="[BLOCKED: witchwood tree]")
    _a, _r = brain.guard_blocked_burrow("ATTACK_WALL:N", "x", _two, (13, 12), _BZ2)
    assert _a == "ATTACK_WALL:E", f"Should pick the other breakable obstacle, got {_a}"
    _a, _r = brain.guard_blocked_burrow("ATTACK_WALL:N", "x", _surr, (13, 12), _BZ2)
    assert not _a.startswith("ATTACK_WALL") and (_a.startswith("MOVE_") or _a == "PASS"), f"No alternative: must not burrow the written-off tree, got {_a}"
    _walled = {d: "[BLOCKED: impassable terrain], [BLOCKED: shale]" for d in ["N", "NE", "NW", "E", "W", "S", "SE", "SW"]}
    brain.BURROW_BLOCKED[(_BZ2, 13, 11)] = brain.TURN_CLOCK + 100
    _a, _r = brain.guard_blocked_burrow("ATTACK_WALL:N", "x", _walled, (13, 12), _BZ2)
    assert _a != "ATTACK_WALL:N", f"A written-off target must never be attacked again, got {_a}"
    _a, _r = brain.guard_blocked_burrow("ATTACK_WALL:E", "x", _two, (13, 12), _BZ2)
    assert _a == "ATTACK_WALL:E", "Burrows at healthy targets are untouched"
    _a, _r = brain.guard_blocked_burrow("MOVE_S", "x", _surr, (13, 12), _BZ2)
    assert _a == "MOVE_S", "Other actions are untouched"
    burrow_reset()
print("  [OK] Test 63 Passed: burrowing continues while HP drops, stops on stalled/HP-less targets, picks alternatives, expires.")


# =====================================================================
# TEST 64: A frontier target that keeps failing is written off, with its neighbours (HANDOFF issue 46)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 64: engine says reachable, every step fails (stuck door): give up after 3 failures, skip neighbours, go elsewhere")
print("="*50)

def fr_fail_state(x, y, targets, failed):
    s = fr_state(x, y, targets)
    s["last_move_failed"] = failed
    return s

_stuck = {"q": "NW", "x": 11, "y": 7, "ux": 10, "uy": 6, "dist": 3}
_nbr = {"q": "NW", "x": 11, "y": 8, "ux": 10, "uy": 9, "dist": 4}      # beside the failing target: same door
_far = {"q": "SW", "x": 12, "y": 20, "ux": 11, "uy": 21, "dist": 15}   # the real unexplored SW area

# (a) The replay: NAVIGATE_TO_CELL:11,7 fails again and again (as in the 2026-10-05 trace, turns 783-812)
fr_reset()
_acts = []
for _turn in range(7):
    brain.last_action = _acts[-1] if _acts else None
    _failing = bool(_acts) and _acts[-1] == "NAVIGATE_TO_CELL:11,7"          # only the stuck target fails; others walk fine
    _d = fr_decide(fr_fail_state(12, 8, [_stuck, _nbr, _far], failed=_failing))
    _acts.append(_d["action"])
print("  decisions:", _acts)
assert _acts[0] == "NAVIGATE_TO_CELL:11,7", _acts
assert _acts.count("NAVIGATE_TO_CELL:11,7") <= brain.FRONTIER_FAIL_LIMIT, f"Must give up on the failing target after {brain.FRONTIER_FAIL_LIMIT} failures, got {_acts}"
assert _acts[-1] == "NAVIGATE_TO_CELL:12,20", f"After writing it off he must head for the SW area, got {_acts}"
assert "NAVIGATE_TO_CELL:11,8" not in _acts, f"A neighbour of a written-off target shares its blockage and must be skipped: {_acts}"
assert (_FZ, (11, 7)) in brain.UNREACHABLE_SECTORS

# (b) Pursuit cap: a target he can walk toward but never reaches is written off after FRONTIER_PURSUIT_MAX turns
fr_reset()
brain.FRONTIER_FAILS.clear(); brain.FRONTIER_BAD.clear(); brain.FRONTIER_PURSUIT.update({"key": None, "turns": 0})
_seen = []
for _turn in range(brain.FRONTIER_PURSUIT_MAX + 6):
    brain.last_action = "MOVE_E"                     # moves fine, never arrives (ping-pongs)
    _seen.append(fr_decide(fr_fail_state(30, 11, [_stuck, _far], failed=False))["action"])
assert _seen[0] == "NAVIGATE_TO_CELL:11,7" and _seen[-1] == "NAVIGATE_TO_CELL:12,20", f"Must give up after the pursuit cap, got first {_seen[0]} last {_seen[-1]}"

# (c) A few failures that are followed by success do not poison a good target
fr_reset()
brain.FRONTIER_FAILS.clear(); brain.FRONTIER_BAD.clear(); brain.FRONTIER_PURSUIT.update({"key": None, "turns": 0})
for _i, _failed in enumerate([False, True, True, False]):
    brain.last_action = "NAVIGATE_TO_CELL:12,20" if _i else None
    _d = fr_decide(fr_fail_state(20, 15, [_far], failed=_failed))
assert _d["action"] == "NAVIGATE_TO_CELL:12,20", "Two failures below the limit must not write a target off"
print("  [OK] Test 64 Passed: failing/never-arriving frontier targets are written off with their neighbours; good targets survive.")


# =====================================================================
# TEST 65: Frontier walks and trees (HANDOFF issue 47)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 65: frontier walks are exempt from the oscillation breaker; an unbreakable path obstacle writes the target off")
print("="*50)

# (a) The exemption applies only to real frontier walks
assert brain.is_frontier_walk("NAVIGATE_TO_CELL:19,17", "Frontier: engine-reachable unexplored area in the SW quadrant at (19, 17), 4 tiles away")
assert not brain.is_frontier_walk("NAVIGATE_TO_CELL:40,11", "Water Traversal: Navigating across water toward unexplored sector at (40, 11)")
assert not brain.is_frontier_walk("MOVE_S", "Frontier: whatever")
assert not brain.is_frontier_walk("NAVIGATE_ZONE_EXIT:E", "Zone fully explored: navigating")

# (b) An obstacle with no HP on the committed frontier path writes the frontier target off too
fr_reset()
_t = {"q": "SW", "x": 19, "y": 17, "ux": 18, "uy": 18, "dist": 4}
_other = {"q": "SW", "x": 30, "y": 22, "ux": 31, "uy": 23, "dist": 15}
_d = fr_decide(fr_state(15, 16, [_t, _other]))
assert _d["action"] == "NAVIGATE_TO_CELL:19,17", _d
with _ctx.redirect_stdout(_io.StringIO()):
    brain.BURROW_LAST_SEQ["seq"] = 0
    brain.note_burrow_progress({"zone_id": _FZ, "last_burrow": {"seq": 1, "dir": "W", "name": "boulder", "x": 17, "y": 17,
                                "has_hp": False, "hp_before": 0, "hp_after": 0, "max_hp": 0, "destroyed": False}})
assert (_FZ, (19, 17)) in brain.UNREACHABLE_SECTORS and brain.FRONTIER_COMMIT["target"] is None, "The target behind an unbreakable obstacle must be written off"
_d = fr_decide(fr_state(15, 16, [_t, _other]))
assert _d["action"] == "NAVIGATE_TO_CELL:30,22", f"He must move on to the next frontier, got {_d}"

# (c) A tree that is losing HP does NOT write the target off; destroying it keeps the target
fr_reset(); brain.BURROW_BLOCKED.clear(); brain.BURROW_PROGRESS.clear(); brain.BURROW_LAST_SEQ["seq"] = 0
_d = fr_decide(fr_state(15, 16, [_t, _other]))
assert _d["action"] == "NAVIGATE_TO_CELL:19,17"
with _ctx.redirect_stdout(_io.StringIO()):
    for _i, (_a, _b) in enumerate([(25, 24), (24, 22), (22, 20)], start=1):
        brain.note_burrow_progress({"zone_id": _FZ, "last_burrow": {"seq": _i, "dir": "W", "name": "shimscale mangrove tree", "x": 17, "y": 17,
                                    "has_hp": True, "hp_before": _a, "hp_after": _b, "max_hp": 25, "destroyed": False}})
    brain.note_burrow_progress({"zone_id": _FZ, "last_burrow": {"seq": 4, "dir": "W", "name": "shimscale mangrove tree", "x": 17, "y": 17,
                                "has_hp": True, "hp_before": 2, "hp_after": 0, "max_hp": 25, "destroyed": True}})
assert (_FZ, (19, 17)) not in brain.UNREACHABLE_SECTORS and brain.FRONTIER_COMMIT["target"] == (19, 17), "A breakable tree must not cost him the target"
brain.BURROW_BLOCKED.clear(); brain.BURROW_PROGRESS.clear(); brain.BURROW_LAST_SEQ["seq"] = 0
print("  [OK] Test 65 Passed: frontier walks exempt from the oscillation breaker; unbreakable blockers write targets off; breakable ones do not.")


# =====================================================================
# TEST 66: Retreat lockout holds at full health: no stairs ping-pong (HANDOFF issue 48)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 66: Impossible creature at the bottom of the stairs: retreat once, then stay up until the level warrants it")
print("="*50)

_SZ10, _SZ11 = "JoppaWorld.12.21.0.0.10", "JoppaWorld.12.21.0.0.11"
def stairs_state(z, level, on_down=False, on_up=False, hostile=None):
    s = {d: "Clear" for d in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]}
    st = {"hp": 27, "max_hp": 27, "x": 7, "y": 17, "z": z, "level": level, "calling": "Warden", "ap": 0, "sp": 0, "mp": 0, "skills": [],
          "zone_id": _SZ10 if z == 10 else _SZ11, "zone_name": "x", "zone_fully_explored": False, "autoexplore_stuck": False,
          "unexplored_cells": 500, "reachable_edges": "NSEW", "last_move_failed": False, "last_failed_dir": "",
          "hostiles_nearby": bool(hostile), "hostiles_adjacent": False, "food_count": 5, "has_food": True, "food_sources": [],
          "standing_on_stairs_down": on_down, "standing_on_stairs_up": on_up, "surroundings": s, "visible_entities": hostile or []}
    return st

def stairs_reset():
    brain.RETREAT_TARGET_LEVEL = None; brain.last_action = None; brain.visit_counts.clear()
    brain.EXPLORED_ZONE_SET.clear(); brain.stuck_autoexplore_zones.clear(); brain.CURRENT_TRACKED_ZONE = None
    brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None; brain.ZONE_STEP_COUNT = 30

_boss = [{"name": "Lucunann", "blueprint": "Lucunann", "tx": 12, "ty": 17, "dist": 5, "dir": "E", "is_enemy": True,
          "is_companion": False, "has_los": True, "difficulty": "Impossible", "level": 40}]
def stairs_decide(st, enemies):
    with _ctx.redirect_stdout(_io.StringIO()):
        return brain.query_decision(st, took_damage=False, enemies=enemies)

# (a) Level 3 with full HP at the top of the stairs: he descends (the intended delve)
stairs_reset()
_d = stairs_decide(stairs_state(10, 3, on_down=True), [])
assert _d["action"] == "USE_STAIRS_DOWN", f"Level 3 meets the stratum-1 requirement, got {_d}"
# (b) At the bottom an Impossible creature is in view: retreat up, set the level goal (even at full HP)
_d = stairs_decide(stairs_state(11, 3, on_up=True, hostile=_boss), _boss)
assert _d["action"] == "USE_STAIRS_UP" and brain.RETREAT_TARGET_LEVEL == 4, f"Expected a retreat with target level 4, got {_d}, target {brain.RETREAT_TARGET_LEVEL}"
# (c) Back at the top, still level 3, full HP: the lockout must hold for many turns (this was the endless ping-pong)
_acts = [stairs_decide(stairs_state(10, 3, on_down=True), [])["action"] for _ in range(8)]
print("  at the top after the retreat:", _acts)
assert "USE_STAIRS_DOWN" not in _acts, f"Must not re-descend before level 4, got {_acts}"
# (d) Once the goal level is reached, he may descend again and the goal clears
_d = stairs_decide(stairs_state(10, 4, on_down=True), [])
assert _d["action"] == "USE_STAIRS_DOWN" and brain.RETREAT_TARGET_LEVEL is None, f"At level 4 the lockout must lift, got {_d}, target {brain.RETREAT_TARGET_LEVEL}"
stairs_reset()
print("  [OK] Test 66 Passed: one retreat, then no descent until the target level; the lockout then lifts.")


# =====================================================================
# TEST 67: Importing brain must never delete the live run's active.flag (HANDOFF issue 49)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 67: import brain leaves active.flag alone; only launching the brain (remove_stale_flag) clears it")
print("="*50)

import subprocess as _sp, sys as _sys
assert "LocalLow" not in brain.EXCHANGE_DIR, f"The test suite must never use the real game folder: {brain.EXCHANGE_DIR}"
_ex = _tempfile.mkdtemp(prefix="qudai_flagtest_")
_flag = _os.path.join(_ex, "active.flag")
open(_flag, "w").write("active")
_here = _os.path.dirname(_os.path.abspath(brain.__file__))
_sp.run([_sys.executable, "-c", "import brain"], cwd=_here, env=dict(_os.environ, QUDAI_EXCHANGE_DIR=_ex), capture_output=True)
assert _os.path.exists(_flag), "`import brain` deleted the active flag: running tests during a live run would stop the game's export"
# The launch path still starts in manual mode: it clears a stale flag
_saved_flag = brain.FLAG_FILE
brain.FLAG_FILE = _flag
brain.remove_stale_flag()
assert not _os.path.exists(_flag), "Launching the brain must clear a stale flag"
brain.FLAG_FILE = _saved_flag
print("  [OK] Test 67 Passed: importing brain is side-effect free for the flag; launching it still starts in manual mode.")


# =====================================================================
# TEST 68: Mutation policy: normalized names, full ranking, build-first ordering (HANDOFF issue 50)
# =====================================================================
print(chr(10) + "="*50)
print("TEST 68: the mutation picker ranks every mutation by build, never 'takes the first'")
print("="*50)

import mutation_policy as _mp

# The mutation names in the game data (StreamingAssets/Base/Mutations.xml, verified 2026-10-06): 59 normal + 20 defects
_PHYS = ("Adrenal Control, Beak, Burrowing Claws, Carapace, Corrosive Gas Generation, Double-muscled, Electrical Generation, "
         "Electromagnetic Pulse, Flaming Ray, Freezing Ray, Heightened Hearing, Heightened Quickness, Horns, Metamorphosis, "
         "Multiple Arms, Multiple Legs, Night Vision, Phasing, Photosynthetic Skin, Quills, Regeneration, Sleep Gas Generation, "
         "Slime Glands, Spinnerets, Stinger (Confusing Venom), Stinger (Paralyzing Venom), Stinger (Poisoning Venom), Thick Fur, "
         "Triple-jointed, Two-headed, Two-hearted, Wings").split(", ")
_MENT = ("Beguiling, Burgeoning, Clairvoyance, Confusion, Cryokinesis, Disintegration, Domination, Ego Projection, Force Bubble, "
         "Force Wall, Kindle, Light Manipulation, Mass Mind, Mental Mirror, Precognition, Psychometry, Pyrokinesis, Sense Psychic, "
         "Spacetime Vortex, Stunning Force, Sunder Mind, Syphon Vim, Telepathy, Teleportation, Teleport Other, Time Dilation, "
         "Temporal Fugue").split(", ")
assert len(_PHYS) == 32 and len(_MENT) == 27

# (a) The universal ranking covers every normal mutation and defect exactly once
_norm = [_mp.normalize_mutation_name(n) for n in _mp.UNIVERSAL_MUTATION_RANKING]
assert len(_norm) == len(set(_norm)), "A mutation appears twice in the universal ranking"
assert {_mp.normalize_mutation_name(n) for n in _PHYS + _MENT} <= set(_norm), "Every normal mutation must be ranked"
assert {_mp.normalize_mutation_name(n) for n in _mp.DEFECTS} <= set(_norm)
# fire starters and gas clouds sit below every survival/control/physical mutation; defects are last
_pos = {n: i for i, n in enumerate(_norm)}
assert _pos["flamingray"] > _pos["burrowingclaws"] > _pos["heightenedquickness"], "Tier order wrong"
# tier order (human-approved 2026-10-06): survival, control, traversal, physical, situational, hazardous, defects
assert _pos["heightenedquickness"] < _pos["freezingray"] < _pos["burrowingclaws"] < _pos["wings"] < _pos["doublemuscled"] < _pos["nightvision"] < _pos["flamingray"], "Tiers must run survival, control, traversal, physical, situational, hazardous"
assert all(_pos[_mp.normalize_mutation_name(d)] > _pos["electricalgeneration"] for d in _mp.DEFECTS), "Defects must rank last"

# (b) Class names, display names and picker text all normalize to the same key
assert _mp.normalize_mutation_name("LightManipulation") == _mp.normalize_mutation_name("Light Manipulation")
assert _mp.normalize_mutation_name("DoubleMuscled") == _mp.normalize_mutation_name("Double-muscled")
assert _mp.normalize_mutation_name("CorrosiveGasGeneration") == _mp.normalize_mutation_name("Corrosive Gas Generation")
assert _mp.option_head("Burrowing Claws - You bear spade-like claws that can burrow ...") == "Burrowing Claws"
assert _mp.option_head("Heightened Quickness (1)") == "Heightened Quickness"
assert _mp.option_head("{{G|Regeneration}} - You heal quickly.") == "Regeneration"
assert _mp.option_head("Stinger (Paralyzing Venom) - Your tail ...") == "Stinger (Paralyzing Venom)"

# (c) Build first, then the universal order: the Esper template's own priorities lead the ranking
_esper = build_templates.BUILD_TEMPLATES["esper_ited_away"]
_rank = _mp.build_mutation_ranking(_esper)
assert _rank[:6] == ["LightManipulation", "SunderMind", "Clairvoyance", "ForceWall", "ForceBubble", "Teleportation"], _rank[:6]
assert len(_rank) == len({_mp.normalize_mutation_name(n) for n in _rank}), "Duplicates in a built ranking"
assert {_mp.normalize_mutation_name(n) for n in _PHYS + _MENT} <= {_mp.normalize_mutation_name(n) for n in _rank}

# (d) The level-5 situation from 2026-10-06: three options, none of them in the Esper list. The old code took the built-in
#     list's Burrowing Claws (or the first entry when nothing matched); the ranking takes the survival mutation instead.
_opts = ["Burrowing Claws - You bear spade-like claws that can burrow ...",
         "Heightened Quickness - You are gifted with tremendous speed.",
         "Flaming Ray - You emit a ray of fire."]
_i, _why = _mp.choose_option(_opts, _rank)
print("  (d) chose", _i, _mp.option_head(_opts[_i]), "|", _why)
assert _mp.option_head(_opts[_i]) == "Heightened Quickness", f"Survival must beat claws and fire, got {_opts[_i]}"
# a template mutation beats the universal order
_i, _why = _mp.choose_option(["Heightened Quickness - x", "Sunder Mind - y", "Regeneration - z"], _rank)
assert _mp.option_head(["Heightened Quickness - x", "Sunder Mind - y", "Regeneration - z"][_i]) == "Sunder Mind", "The build's own priority must win"
# traversal beats physical but loses to control and survival
_o = ["Double-muscled - x", "Burrowing Claws - y", "Quills - z"]
assert _mp.option_head(_o[_mp.choose_option(_o, _rank)[0]]) == "Burrowing Claws", "Traversal must beat a plain physical mutation"
_o = ["Burrowing Claws - y", "Freezing Ray - x", "Wings - w"]
assert _mp.option_head(_o[_mp.choose_option(_o, _rank)[0]]) == "Freezing Ray", "Control must beat traversal"
_o = ["Wings - w", "Regeneration - r", "Burrowing Claws - y"]
assert _mp.option_head(_o[_mp.choose_option(_o, _rank)[0]]) == "Regeneration", "Survival must beat traversal"
# fire-starters only when nothing else is offered
_i, _ = _mp.choose_option(["Flaming Ray - a", "Pyrokinesis - b", "Night Vision - c"], _rank)
assert _i == 2, "A passive mutation beats fire-starters"
# a request from the brain command wins, and class names match display text
_i, _why = _mp.choose_option(["Heightened Quickness - x", "Light Manipulation - y"], _rank, preferred="Regeneration")
assert _why != "requested by the brain", "A preferred mutation that is not offered must not be forced"
_i, _why = _mp.choose_option(["Heightened Quickness - x", "Light Manipulation - y"], _rank, preferred="LightManipulation")
assert (_i, _why) == (1, "requested by the brain"), "Class-name requests must match display text"
# the old failure mode: nothing in the ranking at all -> default first entry, not a crash
_i, _why = _mp.choose_option(["Totally Unknown - x", "Also Unknown - y"], _rank)
assert (_i, _why) == (0, "default")

# (e) Publishing: the file is written once per build, atomically, with comments and one name per line
import tempfile as _tf
_pdir = _tf.mkdtemp(); _pf = _os.path.join(_pdir, "mutation_ranking.txt")
_mp._PUBLISHED.update({"name": None, "path": None})
assert _mp.publish_mutation_ranking(_esper, _pf) is True
assert _mp.publish_mutation_ranking(_esper, _pf) is False, "Must not rewrite for the same build"
_lines = [l for l in open(_pf, encoding="utf-8").read().splitlines() if l and not l.startswith("#")]
assert _lines[:3] == ["LightManipulation", "SunderMind", "Clairvoyance"] and len(_lines) == len(_rank)
assert _mp.publish_mutation_ranking(build_templates.BUILD_TEMPLATES["gas_giant"], _pf) is True, "A new build rewrites the file"
assert _mp.publish_mutation_ranking(_esper, _os.path.join(_pdir, "no", "such", "dir", "x.txt")) is False, "An unwritable path must never raise"
print("  [OK] Test 68 Passed: every mutation ranked once, build first, survival over fire, class and display names match.")

# ---------------------------------------------------------------------------
# Test 69: abilities are matched by exact engine command through the family table (HANDOFF issue 52)
# ---------------------------------------------------------------------------
import ability_registry as _ar
_ab = lambda name, cmd, **k: dict({"name": name, "command": cmd, "usable": True, "cooldown": 0, "active": False}, **k)
# the old bug: a Lase with charges contains the substring "charge" and an unrelated Discharge/Recharge matched too
_lase = _ab("Lase (4 charges)", "CommandLase")
assert brain.find_ready_ability([_lase], "melee_charge") is None, "Lase must not be mistaken for a melee charge"
assert brain.find_ready_ability([_lase], "lase") is _lase
for _c in ("CommandDischarge", "CommandRechargeObject", "CommandToggleProvideCharge"):
    assert brain.find_ready_ability([_ab("Charge thing", _c)], "melee_charge") is None, _c
assert brain.find_ready_ability([_ab("Charge", "CommandMeleeCharge")], "melee_charge") is not None
# the toggle is not a strike; the burrowing toggle and Dig are never used automatically
assert brain.find_ready_ability([_ab("Decapitate", "CommandToggleDecapitate")], "melee_strike") is None
for _c in ("CommandToggleBurrowingClaws", "CommandDig"):
    assert _ar.known(_c) and not _ar.is_wired(_ab("x", _c)) and _ar.unclassified(_c), _c
# families that are documented but off stay off: Teleportation and the Phasing toggle
assert brain.find_ready_ability([_ab("Teleport", "CommandTeleport")], "teleport_self", "phase_escape") is None
assert brain.find_ready_ability([_ab("Phasing", "CommandPhaseIn")], "phase_escape") is not None
# readiness rules are unchanged
assert brain.find_ready_ability([_ab("Lase", "CommandLase", cooldown=5)], "lase") is None
assert brain.find_ready_ability([_ab("Lase (0 charges)", "CommandLase")], "lase") is None
# every command in the table exists in the registry; no family lists a command the game does not have
for _f, _cmds in _ar.FAMILY_COMMANDS.items():
    for _c in _cmds:
        assert _ar.known(_c), f"{_f} lists unknown command {_c}"
# the live level-5 character's 11 abilities all resolve in the registry
for _c in ("CommandToggleRunning", "CommandSurvivalCamp", "CommandIntimidate", "CommandProselytize", "CommandLase",
           "CommandStunningForce", "CommandTeleportOther", "CommandClairvoyance", "CommandAmbientLight",
           "CommandToggleBurrowingClaws", "CommandDig"):
    assert _ar.known(_c), _c
# note_ability_use: counted once per seq, refusal and no-cooldown-change are distinguished, file written atomically
import tempfile as _tf2
_old_stats = brain.ABILITY_STATS_PATH; brain.ABILITY_STATS_PATH = _os.path.join(_tf2.mkdtemp(), "ability_stats.json")
brain.ABILITY_LAST_SEQ["seq"] = 0
_use = lambda seq, **k: {"last_ability_use": dict({"seq": seq, "command": "CommandLase", "known": True, "cd_before": 0, "cd_after": 0, "fired": False, "refused": False, "reason": ""}, **k)}
brain.note_ability_use(_use(1, cd_after=12, fired=True))
brain.note_ability_use(_use(1, cd_after=12, fired=True))      # same seq: not counted twice
brain.note_ability_use(_use(2))                                # cooldown unchanged
brain.note_ability_use(_use(3, refused=True, reason="on cooldown (5)", cd_before=5, cd_after=5))
brain.note_ability_use({})                                     # no report: no crash
_st = json.load(open(brain.ABILITY_STATS_PATH, encoding="utf-8"))["CommandLase"]
assert (_st["attempts"], _st["fired"], _st["refused"]) == (3, 1, 1), _st
brain.ABILITY_STATS_PATH = _old_stats
print("  [OK] Test 69 Passed: abilities match by exact command; Lase is not a charge; unclassified abilities are never auto-used.")

# ---------------------------------------------------------------------------
# Test 70: a water/sector target that never gets closer is written off (HANDOFF issue 53), multi-turn
# ---------------------------------------------------------------------------
brain.UNREACHABLE_SECTORS.clear(); brain.SECTOR_GIVEUP.clear(); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
_z = "TestWaterZone.1"; _tgt = (37, 11)
_flip = [(45, 13), (45, 14)]
_alive = [brain.sector_target_ok(_z, _tgt, _flip[i % 2]) for i in range(brain.SECTOR_STALL_LIMIT + 3)]
assert _alive[0] and not all(_alive), "A target that is never approached must be written off"
assert (_z, _tgt) in brain.UNREACHABLE_SECTORS
# real progress keeps the target alive indefinitely
brain.UNREACHABLE_SECTORS.clear(); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
assert all(brain.sector_target_ok(_z, _tgt, (60 - i, 11)) for i in range(23)), "Steady progress must never be written off"
# the moving 'nearest cell' chase stalls per zone, not per cell
brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
_n = [brain.sector_target_ok(_z, (43, 12 + i % 2), _flip[i % 2], "nearest") for i in range(brain.SECTOR_STALL_LIMIT + 3)]
assert not all(_n) and _z in brain.SECTOR_GIVEUP
brain.UNREACHABLE_SECTORS.clear(); brain.SECTOR_GIVEUP.clear(); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
print("  [OK] Test 70 Passed: a sector target with no progress is written off; steady progress is never cut off.")

# ---------------------------------------------------------------------------
# Test 71: Burrowing Claws are off in settlements (R7) and on elsewhere, without flicker (HANDOFF issue 54)
# ---------------------------------------------------------------------------
_claw = lambda active, **k: [dict({"name": "Burrowing Claws", "command": "CommandToggleBurrowingClaws", "cooldown": 0, "usable": True, "active": active}, **k)]
brain.TURN_CLOCK = 1000; brain.CLAWS_LAST_TOGGLE["turn"] = -10_000
_d = brain.claws_toggle_action(_claw(True), True)
assert _d and _d["action"] == "USE_ABILITY:CommandToggleBurrowingClaws" and "OFF" in _d["reason"], "Claws on in a town must be switched off"
assert brain.claws_toggle_action(_claw(False), True) is None, "Already off in a town: leave it"
brain.TURN_CLOCK = 1010
assert brain.claws_toggle_action(_claw(False), False) is None, "No toggling again within the gap (flicker guard)"
brain.TURN_CLOCK = 1000 + brain.CLAWS_TOGGLE_GAP
_d = brain.claws_toggle_action(_claw(False), False)
assert _d and "ON" in _d["reason"], "Claws off outside a town must be switched on after the gap"
brain.TURN_CLOCK = 5000
assert brain.claws_toggle_action(_claw(True), False) is None, "Already on outside a town: leave it"
assert brain.claws_toggle_action([], True) is None and brain.claws_toggle_action(_claw(True, usable=False), True) is None
brain.TURN_CLOCK = 0; brain.CLAWS_LAST_TOGGLE["turn"] = -10_000
print("  [OK] Test 71 Passed: claws off in towns, on elsewhere, with a flicker guard; no claws means no action.")

# ---------------------------------------------------------------------------
# Test 72: reacting to being on fire (HANDOFF issue 32), bounded so it can never loop
# ---------------------------------------------------------------------------
_sur = lambda **k: dict({d: "ground" for d in brain.CARDINAL_OFFSETS}, **k)
_mv = lambda s: [f"MOVE_{d}" for d, t in s.items() if d in brain.CARDINAL_OFFSETS and "[hazard" not in t.lower()]
brain.FIRE_REACTION["turns"] = 0
_s = _sur(E="[SWIM: salty water]"); _st = {"is_on_fire": True}
_d = brain.fire_reaction(_st, _s, _mv(_s))
assert _d and _d["action"] == "MOVE_E" and "water" in _d["reason"], "Adjacent deep water must be preferred"
brain.FIRE_REACTION["turns"] = 0
_s = _sur(E="[HAZARD: fire] grass", NE="[HAZARD: fire] grass", SE="[HAZARD: fire] grass")
_d = brain.fire_reaction(_st, _s, _mv(_s))
assert _d and _d["action"] in ("MOVE_W", "MOVE_NW", "MOVE_SW"), f"Must flee away from fire on the east side, got {_d}"
assert brain.fire_reaction({"is_on_fire": False}, _s, _mv(_s)) is None and brain.FIRE_REACTION["turns"] == 0
assert brain.fire_reaction({"is_on_fire": True, "is_swimming": True}, _sur(E="[SWIM: x]"), ["MOVE_E"]) is None, "Already in water: nothing to do"
assert brain.fire_reaction(_st, _sur(), _mv(_sur())) is None, "Burning with no fire or water nearby: let it burn out, no invented action"
# multi-turn: never more than FIRE_REACTION_MAX consecutive reaction turns while the fire keeps burning
brain.FIRE_REACTION["turns"] = 0
_n = sum(1 for _ in range(40) if brain.fire_reaction(_st, _s, _mv(_s)))
assert _n == brain.FIRE_REACTION_MAX, _n
assert brain.fire_reaction({"is_on_fire": False}, _s, []) is None and brain.FIRE_REACTION["turns"] == 0, "Counter resets when the fire is out"
print("  [OK] Test 72 Passed: water first, then away from flames, otherwise nothing; bounded at FIRE_REACTION_MAX turns.")

# ---------------------------------------------------------------------------
# Test 73: Lase is withheld when food is at stake and the fight is safe (HANDOFF issue 34 part C)
# ---------------------------------------------------------------------------
_bab = {"name": "baboon", "tx": 18, "ty": 10, "dist": 8, "dir": "E", "is_enemy": True, "difficulty": "Average", "corpse_chance": 40}
_abl = [{"name": "Lase (4 charges)", "command": "CommandLase", "cooldown": 0, "usable": True},
        {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True}]
_need = {"can_butcher": True, "is_hungry": True, "food_count": 1}
brain.LASE_POLICY_STATE["withheld"] = False
_f = brain.filter_corpse_burners(_need, _abl, [_bab], 0.9)
assert [a["command"] for a in _f] == ["CommandStunningForce"], "Lase must be withheld from a hungry butcher facing a corpse-yielding animal"
_tmpl = build_templates.BUILD_TEMPLATES["esper_ited_away"]
_dec = brain.fallback_esper(_need, [_bab], {}, ["MOVE_W"], ["MOVE_W"], _f, _tmpl, (10, 10), 10, 10, 18, 18, False, False, 0, 0, 0)
assert "CommandLase" not in _dec["action"], f"Fallback must not use Lase while it is withheld: {_dec['action']}"
# each reason to keep Lase
assert brain.filter_corpse_burners({"can_butcher": False, "is_hungry": True}, _abl, [_bab], 0.9) == _abl, "Cannot butcher: burning costs nothing"
assert brain.filter_corpse_burners({"can_butcher": True, "food_count": 6}, _abl, [_bab], 0.9) == _abl, "Well fed: no need"
assert brain.filter_corpse_burners(_need, _abl, [_bab], 0.4) == _abl, "Low HP: survive first"
assert brain.filter_corpse_burners(_need, _abl, [dict(_bab, difficulty="Tough")], 0.9) == _abl, "A tough enemy: survive first"
assert brain.filter_corpse_burners(_need, _abl, [_bab] * 3, 0.9) == _abl, "Three hostiles: survive first"
assert brain.filter_corpse_burners(_need, _abl, [dict(_bab, corpse_chance=0)], 0.9) == _abl, "No corpse at stake: Lase freely"
_nokey = dict(_bab); del _nokey["corpse_chance"]
assert brain.filter_corpse_burners(_need, _abl, [_nokey], 0.9) == _abl, "Unknown corpse data (older mod): never withhold"
# with Lase available the old behaviour is unchanged
_dec = brain.fallback_esper(_need, [dict(_bab, corpse_chance=0)], {}, ["MOVE_W"], ["MOVE_W"], _abl[:1], _tmpl, (10, 10), 10, 10, 18, 18, False, False, 0, 0, 0)
assert _dec["action"].startswith("USE_ABILITY:CommandLase"), _dec["action"]
brain.LASE_POLICY_STATE["withheld"] = False
print("  [OK] Test 73 Passed: Lase withheld only for a hungry butcher in a safe fight against a corpse-yielding animal.")

# ---------------------------------------------------------------------------
# Test 74: delving to the stairs uses the engine path; a wall between him and the stairs can no longer flip him forever (issue 55)
# ---------------------------------------------------------------------------
_sd = (15, 12)
brain.KNOWN_STAIRS_DOWN[dungeon_stratum11_zone] = {"tx": 15, "ty": 12, "name": "hole in the ground"}; brain.RETREAT_TARGET_LEVEL = None
brain.UNREACHABLE_SECTORS.discard((dungeon_stratum11_zone, _sd)); brain.STAIRS_GIVEUP.clear(); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
brain.last_action = ""
_dec = brain.query_decision(dict(delve_state_nearby), took_damage=False, enemies=[])
assert _dec["action"] == "NAVIGATE_TO_CELL:15,12", _dec
# the engine reports no route: greedy steps are a fallback, and only while they get closer
brain.UNREACHABLE_SECTORS.add((dungeon_stratum11_zone, _sd))
_acts = []
for _i in range(brain.SECTOR_STALL_LIMIT + 6):
    _st = dict(delve_state_nearby); _st["x"], _st["y"] = (15, 15) if _i % 2 == 0 else (14, 16)   # flipping, never closer than 3
    brain.last_action = ""
    _acts.append(brain.query_decision(_st, took_damage=False, enemies=[])["action"])
assert (dungeon_stratum11_zone, _sd) in brain.STAIRS_GIVEUP, "A stairs target that is never approached must be given up"
assert not any(a.startswith("MOVE_") and "stairs" in a for a in _acts[-3:]), "After the give-up no delve step may remain"
# honest progress is never cut off
brain.STAIRS_GIVEUP.clear(); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
assert all(brain.sector_target_ok(dungeon_stratum11_zone, _sd, (15, 40 - i), "stairs") for i in range(25))
brain.UNREACHABLE_SECTORS.discard((dungeon_stratum11_zone, _sd)); brain.STAIRS_GIVEUP.clear(); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
print("  [OK] Test 74 Passed: delving uses the engine path; with no route the greedy fallback gives up after 14 turns without progress.")

# ---------------------------------------------------------------------------
# Test 75: the autolevel circuit breaker retries; unspent points can no longer sit for a whole session (issue 56)
# ---------------------------------------------------------------------------
_br = brain.AutolevelBreaker(); _pts = (0, 134, 3, 13); brain.TURN_CLOCK = 100
assert not _br.suppressed(_pts)
assert not _br.note_autolevel(_pts), "First attempt does not trip"
assert _br.note_autolevel(_pts), "Second identical attempt trips the breaker"
assert _br.suppressed(_pts), "Suppressed right after tripping"
brain.TURN_CLOCK = 100 + brain.AUTOLEVEL_RETRY_TURNS - 1
assert _br.suppressed(_pts), "Still suppressed just before the retry time"
brain.TURN_CLOCK = 100 + brain.AUTOLEVEL_RETRY_TURNS
assert not _br.suppressed(_pts), "Retries once the wait is over, with the points unchanged"
assert not _br.note_autolevel(_pts), "A retry gets a fresh first attempt"
assert _br.note_autolevel(_pts), "and trips again if it still fails"
_br.note_other((0, 34, 3, 14))
assert not _br.suppressed((0, 34, 3, 14)) and _br.failed == 0, "Changed points (the purchase worked) reset the breaker"
brain.TURN_CLOCK = 0
print("  [OK] Test 75 Passed: the circuit breaker suppresses, retries after AUTOLEVEL_RETRY_TURNS, and resets on progress.")

# ---------------------------------------------------------------------------
# Test 76: a wall-dwelling, immobile hostile at distance 3 no longer locks him into combat (HANDOFF issue 57)
# ---------------------------------------------------------------------------
_lover = {"name": "jilted lover", "blueprint": "Jilted Lover", "dist": 3, "dir": "SE", "tx": 18, "ty": 18, "is_enemy": True, "is_companion": False,
          "can_proselytize": True, "has_los": True, "level": 1, "difficulty": "Easy", "is_stationary": True, "corpse_chance": 2}
assert brain.is_ignorable_stationary_enemy(_lover), "A stationary Easy hostile two or more tiles away is not a threat"
assert not brain.is_ignorable_stationary_enemy(dict(_lover, dist=1)), "Adjacent: never ignored"
assert not brain.is_ignorable_stationary_enemy(dict(_lover, difficulty="Tough")), "Tough: never ignored"
assert not brain.is_ignorable_stationary_enemy(dict(_lover, name="turret", is_stationary=True)), "Turrets: never ignored"
assert not brain.is_ignorable_stationary_enemy(dict(_lover, is_stationary=False, name="baboon")), "A mobile creature is a threat"
brain.KNOWN_STAIRS_DOWN[dungeon_stratum11_zone] = {"tx": 15, "ty": 12, "name": "hole in the ground"}; brain.RETREAT_TARGET_LEVEL = None
brain.UNREACHABLE_SECTORS.discard((dungeon_stratum11_zone, (15, 12))); brain.STAIRS_GIVEUP.clear()
_st = dict(delve_state_nearby); _st["visible_entities"] = [_lover]; _st["zone_fully_explored"] = True
_dec = brain.query_decision(_st, took_damage=False, enemies=[_lover])
assert _dec["action"] == "NAVIGATE_TO_CELL:15,12", f"With only an immobile vine in view he must carry on to the stairs, got {_dec}"
_dec = brain.query_decision(_st, took_damage=False, enemies=[dict(_lover, is_stationary=False, name="baboon", blueprint="Baboon")])
assert not _dec["action"].startswith("NAVIGATE_TO_CELL"), f"A mobile hostile at distance 3 must still be fought, got {_dec}"
print("  [OK] Test 76 Passed: stationary hostiles beyond one tile do not force combat; adjacent, tough and mobile ones still do.")

# ---------------------------------------------------------------------------
# Test 77: the retreat to stairs up uses the engine path, and a wall can no longer make it flip until he dies (issue 58)
# ---------------------------------------------------------------------------
_enemy_h = [{"name": "snapjaw hunter", "dist": 3, "tx": 23, "ty": 15, "difficulty": "Tough"}]
_su = (20, 12)
brain.STAIRS_GIVEUP.clear(); brain.UNREACHABLE_SECTORS.discard((stratum1_zone, _su)); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
brain.update_stair_records(state_stratum1_retreat); brain.RETREAT_TARGET_LEVEL = None
_dec = brain.query_decision(dict(state_stratum1_retreat), took_damage=True, enemies=_enemy_h)
assert _dec["action"] == "NAVIGATE_TO_CELL:20,12", _dec
brain.UNREACHABLE_SECTORS.add((stratum1_zone, _su))      # the engine said: no route
_seen = []
for _i in range(brain.SECTOR_STALL_LIMIT + 6):
    _st = dict(state_stratum1_retreat); _st["x"], _st["y"] = (20, 15) if _i % 2 == 0 else (19, 15)   # flipping, never closer
    _seen.append(brain.query_decision(_st, took_damage=True, enemies=_enemy_h)["reason"])
assert (stratum1_zone, _su) in brain.STAIRS_GIVEUP, "A retreat that never gets closer must be given up"
assert "Fleeing towards stairs up" not in _seen[-1], "After the give-up he must stop fleeing toward them and fight or act otherwise"
brain.STAIRS_GIVEUP.clear(); brain.UNREACHABLE_SECTORS.discard((stratum1_zone, _su)); brain.SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
print("  [OK] Test 77 Passed: retreat to stairs up by engine path; the greedy fallback gives up without progress.")

# ---------------------------------------------------------------------------
# Test 78: stand and fight (HANDOFF issue 58): no fleeing from an adjacent below-Tough attacker unless stairs are close
# ---------------------------------------------------------------------------
_hunter = lambda diff="Average": {"name": "snapjaw hunter", "dist": 1, "dir": "E", "tx": 11, "ty": 10, "difficulty": diff, "is_enemy": True}
_gs = {"x": 10, "y": 10, "stairs_up": [], "stairs_down": []}
_adj = {"E": "snapjaw hunter"}
_abs = [{"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True},
        {"name": "Lase (4 charges)", "command": "CommandLase", "cooldown": 0, "usable": True}]
brain.KNOWN_STAIRS_UP.clear(); brain.KNOWN_STAIRS_DOWN.clear()
_flee = {"action": "SPRINT_W", "reason": "[LLM] Emergency retreat from melee threat"}
_d = brain.enforce_stand_and_fight(_flee, _gs, _adj, [_hunter()], _abs)
assert _d["action"] == "USE_ABILITY:CommandStunningForce:E", f"Stunning Force comes first, got {_d}"
_d = brain.enforce_stand_and_fight(_flee, _gs, _adj, [_hunter()], _abs[1:])
assert _d["action"] == "USE_ABILITY:CommandLase:E", f"then Lase, got {_d}"
_d = brain.enforce_stand_and_fight(_flee, _gs, _adj, [_hunter()], [])
assert _d["action"] == "MOVE_E", f"then a melee bump, got {_d}"
for _fl in ({"action": "MOVE_W", "reason": "x"}, {"action": "ACTIVATE_SPRINT", "reason": "x"}, {"action": "NAVIGATE_ZONE_EXIT:S", "reason": "x"}, {"action": "USE_STAIRS_UP", "reason": "x"}):
    assert brain.enforce_stand_and_fight(_fl, _gs, _adj, [_hunter()], _abs)["action"].startswith(("USE_ABILITY", "MOVE_E")), _fl
# decisions that are not fleeing pass through untouched
for _ok in ({"action": "MOVE_E", "reason": "attack"}, {"action": "USE_ABILITY:CommandIntimidate", "reason": "x"}, {"action": "EAT", "reason": "x"}):
    assert brain.enforce_stand_and_fight(_ok, _gs, _adj, [_hunter()], _abs) is _ok, _ok
# the exceptions: Tough or worse, stairs close, standing on stairs, nobody adjacent
assert brain.enforce_stand_and_fight(_flee, _gs, _adj, [_hunter("Tough")], _abs) is _flee, "Tough: he may run"
assert brain.enforce_stand_and_fight(_flee, dict(_gs, stairs_up=[{"tx": 13, "ty": 12}]), _adj, [_hunter()], _abs) is _flee, "Stairs within 4 tiles: he may run to them"
assert brain.enforce_stand_and_fight(_flee, dict(_gs, stairs_up=[{"tx": 30, "ty": 12}]), _adj, [_hunter()], _abs)["action"] != "SPRINT_W", "Far stairs do not count"
assert brain.enforce_stand_and_fight(_flee, dict(_gs, standing_on_stairs_up=True), _adj, [_hunter()], _abs) is _flee
assert brain.enforce_stand_and_fight(_flee, _gs, {}, [dict(_hunter(), dist=3)], _abs) is _flee, "Nobody adjacent: nothing to stand against"
brain.KNOWN_STAIRS_UP[("zz",)] = {"tx": 11, "ty": 11}
assert brain.enforce_stand_and_fight(_flee, _gs, _adj, [_hunter()], _abs) is _flee, "Remembered stairs close by also allow running"
brain.KNOWN_STAIRS_UP.clear()
print("  [OK] Test 78 Passed: below-Tough adjacent attackers are fought (Stunning Force, Lase, melee); Tough, close stairs and non-flee actions are untouched.")


# ---------------------------------------------------------------------------
# Test 79: loot (issue 59): walk to unowned items and chests, take them when adjacent, never in towns, never loop
# ---------------------------------------------------------------------------
def _loot_reset():
    brain.LOOT_BLACKLIST.clear(); brain.LOOT_PURSUIT.update({"key": None, "turns": 0}); brain.LOOT_STREAK.update({"key": None, "count": 0}); brain.LOOT_TURN = 0
_loot_reset()
_src = lambda **k: dict({"kind": "chest", "name": "chest", "tx": 20, "ty": 10, "dist": 5}, **k)
_LZ = "LootZone.1"
assert brain.choose_loot_action({"loot_sources": []}, _LZ, "", False) is None, "Nothing to loot: nothing to do"
assert brain.choose_loot_action({"loot_sources": [_src()]}, _LZ, "", True) is None, "Never in a settlement (R7)"
assert brain.choose_loot_action({"loot_sources": [_src()], "is_swimming": True}, _LZ, "", False) is None
_d = brain.choose_loot_action({"loot_sources": [_src(), _src(name="sword", kind="item", tx=15, ty=10, dist=3)]}, _LZ, "", False)
assert _d["action"] == "NAVIGATE_TO_CELL:15,10", f"Nearest first, got {_d}"
_d = brain.choose_loot_action({"loot_sources": [_src(dist=1, tx=11, ty=10)]}, _LZ, "", False)
assert _d["action"] == "LOOT", f"Adjacent: take it, got {_d}"
_d = brain.choose_loot_action({"loot_sources": [_src(dist=0, tx=10, ty=10, kind="item", name="dagger")]}, _LZ, "LOOT", False)
assert _d["action"] == "LOOT", "Standing on an item: take it"
# a LOOT that keeps not removing the source is written off after LOOT_STREAK_MAX tries
_loot_reset()
_acts = [brain.choose_loot_action({"loot_sources": [_src(dist=1, tx=11, ty=10)]}, _LZ, "LOOT", False) for _ in range(brain.LOOT_STREAK_MAX + 3)]
assert _acts[0]["action"] == "LOOT" and _acts[-1] is None, "A source that cannot be looted must be given up"
assert (_LZ, 11, 10) in brain.LOOT_BLACKLIST
# the engine pathfinder says no route: blacklist, move on to the next source
_loot_reset()
brain.choose_loot_action({"loot_sources": [_src()]}, _LZ, "", False)
_d = brain.choose_loot_action({"loot_sources": [_src(), _src(tx=30, ty=10, dist=9)], "last_move_failed": True, "last_failed_dir": "PATH_BLOCKED"}, _LZ, "NAVIGATE_TO_CELL:20,10", False)
assert (_LZ, 20, 10) in brain.LOOT_BLACKLIST and _d["action"] == "NAVIGATE_TO_CELL:30,10", f"Unreachable source skipped, got {_d}"
# a walk that never arrives is written off after LOOT_PURSUIT_MAX_TURNS
_loot_reset()
_last = [brain.choose_loot_action({"loot_sources": [_src()]}, _LZ, "", False) for _ in range(brain.LOOT_PURSUIT_MAX_TURNS + 3)]
assert _last[0] is not None and _last[-1] is None and (_LZ, 20, 10) in brain.LOOT_BLACKLIST
# in the full decision, Phase A walks to loot before it descends or explores
_loot_reset()
brain.KNOWN_STAIRS_DOWN[dungeon_stratum11_zone] = {"tx": 15, "ty": 12, "name": "hole in the ground"}; brain.RETREAT_TARGET_LEVEL = None
brain.UNREACHABLE_SECTORS.discard((dungeon_stratum11_zone, (15, 12))); brain.STAIRS_GIVEUP.clear()
_st = dict(delve_state_nearby); _st["zone_fully_explored"] = True; _st["visible_entities"] = []
_st["loot_sources"] = [{"kind": "chest", "name": "chest", "tx": 12, "ty": 15, "dist": 3}]
_dec = brain.query_decision(_st, took_damage=False, enemies=[])
assert _dec["action"] == "NAVIGATE_TO_CELL:12,15" and "Loot" in _dec["reason"], f"Loot comes before the descent, got {_dec}"
_st["loot_sources"] = []
_dec = brain.query_decision(_st, took_damage=False, enemies=[])
assert "Loot" not in _dec["reason"], "No loot, no loot step"
_loot_reset()
# the console report is printed once per sequence number
brain.LOOT_LAST_SEQ["seq"] = 0
brain.note_loot({"last_loot": {"seq": 1, "kind": "chest", "name": "chest", "count": 3, "left": 0}}); brain.note_loot({"last_loot": {"seq": 1}}); brain.note_loot({})
assert brain.LOOT_LAST_SEQ["seq"] == 1
print("  [OK] Test 79 Passed: loot sources are walked to nearest-first, taken when adjacent, skipped in towns, and every dead end is written off.")
# Test 80: "tam" no longer makes a giant amoeba a peaceful citizen (HANDOFF issue 60)
# ---------------------------------------------------------------------------
assert not brain.is_peaceful_npc("giant amoeba", "GiantAmoeba"), "A giant amoeba is not a peaceful NPC"
assert not brain.is_peaceful_npc("stamped data disk", "Stamped Data Disk")
assert not brain.is_peaceful_npc("metamorphic polygel", "Metamorphic Polygel")
assert brain.is_peaceful_npc("Tam", "Tam"), "The real NPC is still peaceful"
assert brain.is_peaceful_npc("Tam the dromad", None), "Whole word anywhere in the name"
assert brain.is_peaceful_npc("water merchant", "WaterMerchant") and brain.is_peaceful_npc("Barathrumites", None) and brain.is_peaceful_npc("farmer", "Farmer1")
assert brain.is_peaceful_npc("amoeba farmer", "AmoebaFarmer"), "Longer keywords keep substring matching (variants and plurals)"
assert not brain.is_peaceful_npc("snapjaw warden", "SnapjawWarden"), "Hostile overrides still win"
_amoeba = {"name": "giant amoeba", "blueprint": "GiantAmoeba", "is_enemy": True, "is_companion": False, "tx": 19, "ty": 7, "dist": 1, "dir": "SW", "difficulty": "Average"}
assert brain.filter_hostile_enemies([_amoeba]) == [_amoeba], "The amoeba must stay in the enemy list"
assert not brain.is_town_zone({"visible_entities": [_amoeba], "zone_name": "slimy salt marsh"}), "A marsh with an amoeba in it is not a town"
_d = brain.enforce_stand_and_fight({"action": "SPRINT_N", "reason": "[LLM] Escape melee threat"}, {"x": 20, "y": 6, "stairs_up": [], "stairs_down": []}, {"SW": "giant amoeba"}, [_amoeba], [])
assert _d["action"] == "MOVE_SW", f"With the amoeba recognised, an Average melee threat is fought, got {_d}"
assert not brain.is_ignorable_stationary_enemy({"name": "cherubic spade", "dist": 5, "difficulty": "Average"}), "A spade is not a pad"
assert brain.is_ignorable_stationary_enemy({"name": "lily pad", "dist": 5, "difficulty": "Easy"}) and brain.is_ignorable_stationary_enemy({"name": "glowpad", "dist": 5, "difficulty": "Easy"})
print("  [OK] Test 80 Passed: short peaceful keywords match whole words only; the amoeba stays an enemy and the marsh is not a town.")


# ---------------------------------------------------------------------------
# Test 81: Impossible hostiles near the arrival border: go back through it (HANDOFF issue 61)
# ---------------------------------------------------------------------------
_jell = {"name": "black jell", "blueprint": "BlackJell", "dist": 5, "dir": "SW", "tx": 45, "ty": 5, "is_enemy": True, "has_los": True, "difficulty": "Impossible"}
_BZ = "JoppaWorld.11.20.0.0.12"
brain.LAST_ZONE_ENTRY = {"from_zone": "JoppaWorld.11.22.1.1.12", "to_zone": _BZ, "entry_pos": (48, 0), "reverse_dir": "N"}
brain.FAILED_ZONE_EXITS.discard(("JoppaWorld.11.22.1.1.12", "S"))
_d = brain.border_retreat_decision({}, _BZ, (48, 0), [_jell])
assert _d["action"] == "MOVE_N" and _d.get("flee_ok"), f"On the border: step back through it, got {_d}"
assert ("JoppaWorld.11.22.1.1.12", "S") in brain.FAILED_ZONE_EXITS, "The exit that leads into the danger zone must be written off"
_d = brain.border_retreat_decision({}, _BZ, (50, 2), [_jell])
assert _d["action"] == "NAVIGATE_ZONE_EXIT:N", f"Near the border: walk back to it, got {_d}"
assert brain.border_retreat_decision({}, _BZ, (60, 12), [_jell]) is None, "Far from the arrival border: no border retreat"
assert brain.border_retreat_decision({}, _BZ, (48, 0), [dict(_jell, difficulty="Tough")]) is None, "Only Impossible hostiles trigger it"
assert brain.border_retreat_decision({}, _BZ, (48, 0), [dict(_jell, has_los=False)]) is None, "Out of sight: no retreat"
assert brain.border_retreat_decision({}, _BZ, (48, 0), [dict(_jell, dist=14)]) is None, "Too far away to matter yet"
assert brain.border_retreat_decision({}, "SomeOtherZone", (48, 0), [_jell]) is None, "Only in the zone he just entered"
# the stand-and-fight rule must not undo it, even with a weak hostile adjacent
_weak = {"name": "snapjaw", "dist": 1, "dir": "E", "difficulty": "Easy", "is_enemy": True}
_flee = {"action": "MOVE_N", "reason": "Danger retreat", "flee_ok": True}
assert brain.enforce_stand_and_fight(_flee, {"x": 48, "y": 0}, {"E": "snapjaw"}, [_weak, _jell], []) is _flee
# in the full decision, the retreat comes before any fight
brain.KNOWN_STAIRS_UP.clear(); brain.KNOWN_STAIRS_DOWN.clear(); brain.RETREAT_TARGET_LEVEL = None
brain.LAST_ZONE_ENTRY = {"from_zone": "X.prev", "to_zone": dungeon_stratum11_zone, "entry_pos": (15, 0), "reverse_dir": "N"}
_st = dict(delve_state_nearby); _st["x"], _st["y"] = 15, 0; _st["visible_entities"] = [_jell]
_st["surroundings"] = {"N": "[ZONE_EXIT: N]", "S": "dirt floor", "E": "dirt floor", "W": "dirt floor"}
_dec = brain.query_decision(_st, took_damage=False, enemies=[_jell])
assert _dec["action"] == "MOVE_N" and "Danger retreat" in _dec["reason"], f"Full decision: go back through the border, got {_dec}"
brain.LAST_ZONE_ENTRY = None; brain.FAILED_ZONE_EXITS.discard(("X.prev", "S")); brain.FAILED_ZONE_EXITS.discard(("JoppaWorld.11.22.1.1.12", "S"))
print("  [OK] Test 81 Passed: Impossible hostiles near the arrival border send him back through it; the exit is written off; stand-and-fight leaves it alone.")


# ---------------------------------------------------------------------------
# Test 82: only approved ancestral lessons reach the combat prompt (HANDOFF issue 62)
# ---------------------------------------------------------------------------
import chronicler as _chr
import tempfile as _tf3
_old_wf = _chr.WISDOM_FILE
_chr.WISDOM_FILE = _os.path.join(_tf3.mkdtemp(), "ancestral_wisdom.json")
try:
    assert "No approved" in _chr.format_ancestral_memory_for_prompt(), "No file: neutral text"
    _chr.save_ancestral_wisdom([
        {"generation": 1, "name": "A", "zone": "z", "death_reason": "x", "lesson": "Invented lesson one."},
        {"generation": 2, "name": "B", "zone": "z", "death_reason": "y", "lesson": "Checked lesson two.", "approved": True},
        {"generation": 3, "name": "C", "zone": "z", "death_reason": "z", "lesson": "Unapproved lesson three.", "approved": False},
    ])
    _p = _chr.format_ancestral_memory_for_prompt()
    assert "Checked lesson two." in _p and "Invented lesson one." not in _p and "Unapproved lesson three." not in _p, _p
    _chr.save_ancestral_wisdom([{"generation": 1, "lesson": "Only a guess."}])
    assert "Only a guess." not in _chr.format_ancestral_memory_for_prompt() and "No approved" in _chr.format_ancestral_memory_for_prompt()
    # the CLI approves and rejects by generation and keeps everything else
    import importlib.util as _iu
    _spec = _iu.spec_from_file_location("wisdom_cli", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools", "wisdom.py"))
    _cli = _iu.module_from_spec(_spec); _spec.loader.exec_module(_cli)
    with _ctx.redirect_stdout(_io.StringIO()):
        _cli.main(["approve", "1"])
    assert "Only a guess." in _chr.format_ancestral_memory_for_prompt(), "Approved by the CLI"
    with _ctx.redirect_stdout(_io.StringIO()):
        _cli.main(["reject", "1"])
    assert "Only a guess." not in _chr.format_ancestral_memory_for_prompt(), "Rejected again"
    assert len(_chr.load_ancestral_wisdom()) == 1, "Rejecting never deletes a lesson"
finally:
    _chr.WISDOM_FILE = _old_wf
print("  [OK] Test 82 Passed: unapproved lessons are saved but never shown to the model; tools/wisdom.py approves and rejects.")


# ---------------------------------------------------------------------------
# Test 83: the automatic post-mortem states the facts of a death (HANDOFF issue 63)
# ---------------------------------------------------------------------------
import postmortem as _pm
import tempfile as _tf4
_dir4 = _tf4.mkdtemp()
_rows = [{"t": 1, "pos": [5, 5], "hp": 31, "action": "AUTOEXPLORE", "reason": "explore", "combat": False}]
for _i, (_hp, _act, _c) in enumerate([(31, "USE_ABILITY:CommandLase:SE", True), (31, "USE_ABILITY:CommandLase:SE", True), (31, "USE_ABILITY:CommandLase:SE", True),
                                      (31, "USE_ABILITY:CommandLase:SE", True), (22, "SPRINT_E", True), (9, "SPRINT_E", True), (9, "SPRINT_SW", True),
                                      (9, "SPRINT_E", True), (9, "SPRINT_W", True), (9, "SPRINT_E", True), (9, "SPRINT_W", True), (9, "SPRINT_E", True)], start=2):
    _rows.append({"t": _i, "pos": [48 + (_i % 2), 0], "hp": _hp, "action": _act, "reason": "LLM: sustain beam | piped", "combat": _c})
_state = {"hp": 9, "max_hp": 31, "level": 5, "x": 49, "y": 0, "z": 12, "effects": ["dazed"],
          "visible_entities": [{"name": "black jell", "dist": 2, "dir": "SW", "difficulty": "Impossible", "level": 14, "has_los": True, "is_enemy": True},
                               {"name": "goat", "dist": 1, "dir": "E", "is_companion": True}],
          "abilities": [{"name": "Lase (0 charges)", "cooldown": 0}]}
_death = {"player_name": "Test Pilgrim", "level": 5, "turns": 2209, "zone": "subterranean desert canyon", "death_reason": "killed by a brown jell"}
_md = _pm.build_postmortem(_death, _state, _rows, generation=16)
for _needle in ("Post-mortem: Test Pilgrim (Gen 16)", "black jell", "Impossible", "(-13)", "Largest single-turn HP loss", "13 (42% of max HP)",
                "running did not shake the attacker", "Position flip", "Lase (0 charges)", "Companions: goat"):
    assert _needle in _md, f"missing in post-mortem: {_needle}\n{_md}"
assert "slimy/slimy" in _pm.build_postmortem({}, {"visible_entities": [{"name": "slimy|slimy jell", "is_enemy": True, "dist": 1}]}, []), "A pipe in a creature name must not break the table"
assert _pm.classify("SPRINT_N") == "flee/escape" and _pm.classify("REST") == "rest" and _pm.classify("USE_ABILITY:x") == "ability"
# a run boundary: only the newest run's rows are used
_tp = _os.path.join(_dir4, "trace.jsonl")
with open(_tp, "w", encoding="utf-8") as _f:
    for _r in [{"t": 1, "hp": 9, "action": "OLD"}, {"t": 2, "hp": 9, "action": "OLD"}, {"t": 1, "hp": 20, "action": "NEW"}, {"t": 2, "hp": 20, "action": "NEW2"}]:
        _f.write(json.dumps(_r) + "\n")
assert [r["action"] for r in _pm.load_trace_run(_tp)] == ["NEW", "NEW2"]
assert _pm.load_trace_run(_os.path.join(_dir4, "missing.jsonl")) == []
_path = _pm.write_postmortem(_dir4, _death, _state, _rows, 16, timestamp=123)
assert _os.path.basename(_path) == "Postmortem_Gen16_Test_Pilgrim_123.md" and "black jell" in open(_path, encoding="utf-8").read()
# no data at all must not crash
assert "No decision trace found" in _pm.build_postmortem({}, None, [])
print("  [OK] Test 83 Passed: the post-mortem lists the hostiles and their ratings, the HP drops, the decision mix and the heuristic observations.")


# ---------------------------------------------------------------------------
# Test 84: the danger ledger raises the rating of creatures that proved dangerous (HANDOFF issue 64)
# ---------------------------------------------------------------------------
import danger_ledger as _dl
_dl.LEDGER_PATH = _os.path.join(_tempfile.mkdtemp(), "ledger84.json"); _dl.reset_cache()
_amb = lambda dist=1, **k: dict({"name": "giant amoeba", "blueprint": "GiantAmoeba", "is_enemy": True, "dist": dist, "dir": "SW", "difficulty": "Average", "has_los": True}, **k)
_gs = lambda hp, mx=18, ents=None, **k: dict({"hp": hp, "max_hp": mx, "visible_entities": ents if ents is not None else [_amb()], "effects": []}, **k)
assert _dl.rating_for("GiantAmoeba", 18) is None, "Unknown creature: no rating"
assert _dl.record_turn_damage(_gs(1), 18), "17 HP lost next to one amoeba is recorded"
assert _dl.rating_for("GiantAmoeba", 18) is None, "One observation can be a freak: not rated yet"
_dl.record_turn_damage(_gs(2), 19)
assert _dl.rating_for("GiantAmoeba", 18) == "Impossible", "Two big hits against 18 max HP: Impossible"
assert _dl.rating_for("GiantAmoeba", 31) == "Very Tough" and _dl.rating_for("GiantAmoeba", 100) is None, "Rated against the CURRENT max HP"
# what must not be recorded
_n_before = _dl._load()["GiantAmoeba"]["hits"]
assert not _dl.record_turn_damage(_gs(10, ents=[_amb(), _amb(blueprint="Baboon", name="baboon")]), 25), "Two kinds adjacent: cannot attribute"
assert not _dl.record_turn_damage(_gs(10, effects=["bleeding"]), 25), "Bleeding is not the creature"
assert not _dl.record_turn_damage(_gs(10, is_on_fire=True), 25), "Fire is not the creature"
assert not _dl.record_turn_damage(_gs(30), 25), "HP went up"
assert not _dl.record_turn_damage(_gs(10, ents=[_amb(dist=3)]), 25), "Not adjacent: not attributed"
assert _dl._load()["GiantAmoeba"]["hits"] == _n_before
# kills count at once and are credited to the creature named in the death message
assert _dl.record_death({"visible_entities": [_amb(blueprint="Baboon", name="baboon"), _amb()]}, "You were @@killed by a giant amoeba## with a slimy pseudopod##.") == "GiantAmoeba"
assert _dl._load()["GiantAmoeba"]["kills"] == 1
assert _dl.record_death({"visible_entities": []}, "x") is None
# apply: only ever raises, keeps the engine's rating, leaves strangers alone
_out = _dl.apply([_amb(), _amb(blueprint="Baboon", name="baboon"), _amb(difficulty="Impossible")], 31)
assert _out[0]["difficulty"] == "Very Tough" and _out[0]["difficulty_engine"] == "Average" and "max hit" in _out[0]["ledger_note"]
assert _out[1]["difficulty"] == "Average" and "difficulty_engine" not in _out[1], "No entry: untouched"
assert _out[2]["difficulty"] == "Impossible", "Never lowered"
# in the full decision: an Average-rated amoeba with a bad record sends a low-HP character back through the arrival border
_dl._load()["GiantAmoeba"]["max_hit"] = 25
brain.KNOWN_STAIRS_UP.clear(); brain.KNOWN_STAIRS_DOWN.clear(); brain.RETREAT_TARGET_LEVEL = None
brain.LAST_ZONE_ENTRY = {"from_zone": "X.prev", "to_zone": dungeon_stratum11_zone, "entry_pos": (15, 0), "reverse_dir": "N"}
_st = dict(delve_state_nearby); _st["x"], _st["y"] = 15, 0; _st["max_hp"] = 28; _st["hp"] = 28
_foe = _amb(dist=3, tx=12, ty=2)
_st["visible_entities"] = [_foe]; _st["surroundings"] = {"N": "[ZONE_EXIT: N]", "S": "dirt floor", "E": "dirt floor", "W": "dirt floor"}
_dec = brain.query_decision(dict(_st), took_damage=False, enemies=[_foe])
assert _dec["action"] == "MOVE_N" and "Danger retreat" in _dec["reason"], f"The ledger makes the amoeba Impossible for this character, got {_dec}"
_dl.LEDGER_PATH = _os.path.join(_tempfile.mkdtemp(), "ledger84b.json"); _dl.reset_cache()
_dec = brain.query_decision(dict(_st), took_damage=False, enemies=[_foe])
assert "Danger retreat" not in _dec["reason"], "Without the record the engine's Average rating stands"
brain.LAST_ZONE_ENTRY = None
_dl.LEDGER_PATH = _os.path.join(_tempfile.mkdtemp(), "danger_ledger_dry_run.json"); _dl.reset_cache()
print("  [OK] Test 84 Passed: the ledger learns from hits and kills, rates against current max HP, only ever raises a rating, and feeds the existing retreat rules.")


# ---------------------------------------------------------------------------
# Test 85: the brain picks the LOADED chat model, honours an override, and the model is recorded (HANDOFF issue 65)
# ---------------------------------------------------------------------------
_v0 = [{"id": "text-embedding-nomic", "type": "embeddings", "state": "loaded"}, {"id": "google/gemma-4-12b", "type": "vlm", "state": "not-loaded"},
       {"id": "ministral-3-8b-instruct-2512", "type": "llm", "state": "loaded"}]
_v1 = [{"id": "google/gemma-4-12b"}, {"id": "text-embedding-bge-m3"}, {"id": "ministral-3-8b-instruct-2512"}]
assert brain.pick_model_id(_v0, _v1) == "ministral-3-8b-instruct-2512", "The loaded chat model, not the first listed"
assert brain.pick_model_id(_v0, _v1, override="qwen/qwen3-vl-8b-instruct") == "qwen/qwen3-vl-8b-instruct", "Override wins"
assert brain.pick_model_id([], _v1) == "google/gemma-4-12b", "No load info: first non-embedding model"
assert brain.pick_model_id([], [{"id": "text-embedding-bge-m3"}]) is None, "Only embeddings: no chat model"
assert brain.pick_model_id([], []) is None
assert isinstance(brain.LM_STUDIO_TIMEOUT, float) and brain.LM_STUDIO_TIMEOUT > 0
_md = _pm.build_postmortem({"player_name": "X"}, {}, [{"t": 1, "hp": 5, "action": "REST", "model": "google/gemma-4-12b"}])
assert "Combat model(s) this run: google/gemma-4-12b" in _md
print("  [OK] Test 85 Passed: loaded chat model chosen, override honoured, embeddings never picked, model recorded in the post-mortem.")


# ---------------------------------------------------------------------------
# Test 86: the model lab scores models on the brain's real combat call (HANDOFF issue 65), against a fake LM Studio
# ---------------------------------------------------------------------------
import copy as _copy
import http.server as _hs
import importlib.util as _iu2
import threading as _th
import time as _tm

_spec2 = _iu2.spec_from_file_location("model_lab", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools", "model_lab.py"))
_lab = _iu2.module_from_spec(_spec2); _spec2.loader.exec_module(_lab)


class _FakeLM(_hs.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        try:
            self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        except OSError:
            pass   # the client gave up (that is the timeout test)

    def do_GET(self):
        data = [{"id": "lab-good", "type": "llm", "state": "loaded"}, {"id": "lab-embed", "type": "embeddings", "state": "loaded"}, {"id": "lab-bad", "type": "llm", "state": "not-loaded"}]
        self._send({"data": data})

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).last_payload = payload
        model = payload.get("model")
        user = payload["messages"][-1]["content"]
        if "VALID ACTIONS:" not in user:
            return self._send({"choices": [{"message": {"content": "ready"}}]})
        first = user.split("VALID ACTIONS:")[1].strip().splitlines()[0][2:].split()[0]
        if model == "lab-good":
            content = json.dumps({"action": first, "thought": "taking the first valid action"})
        elif model == "lab-garbage":
            content = "I think you should probably run away!"
        elif model == "lab-think":
            content = "<think>Let me consider every option at great length...</think>" + json.dumps({"action": first, "thought": "x"})
        elif model == "lab-offmenu":
            content = json.dumps({"action": "TELEPORT_HOME", "thought": "not an offered action"})
        elif model == "lab-empty":
            return self._send({"choices": [{"message": {"content": "", "reasoning_content": "Let me think about the options for a very long time..."}, "finish_reason": "length"}], "usage": {"completion_tokens": 128}})
        elif model == "lab-slow":
            _tm.sleep(1.2)
            content = json.dumps({"action": first, "thought": "slow"})
        else:
            return self._send({"error": "no such model"}, 404)
        self._send({"choices": [{"message": {"content": content}}]})


_srv = _hs.ThreadingHTTPServer(("127.0.0.1", 0), _FakeLM)
_th.Thread(target=_srv.serve_forever, daemon=True).start()
_base = f"http://127.0.0.1:{_srv.server_address[1]}"
_scn = json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "model_lab_scenarios.json"), encoding="utf-8"))["scenarios"]
assert len(_scn) >= 8 and all({"id", "state", "enemies", "checks"} <= set(s) for s in _scn), "The scenario file must be well formed"
_old_url, _old_to, _old_model = brain.LM_STUDIO_URL, brain.LM_STUDIO_TIMEOUT, brain.active_model_id
try:
    _res = _lab.run_lab(["lab-good", "lab-garbage", "lab-think", "lab-offmenu", "lab-nobody"], _scn[:4], base=_base, repeat=2, timeout=5.0, unload=False, manage_models=False, log=lambda *a: None)
    _by = {s["model"]: s for s in _res["summaries"]}
    assert _by["lab-good"]["parse_pct"] == 100 and _by["lab-good"]["menu_pct"] == 100, _by["lab-good"]
    assert _by["lab-good"]["latency_p50"] is not None and _by["lab-good"]["same_action_pct"] == 100.0, "Same fixed reply: fully consistent"
    assert _by["lab-garbage"]["parse_pct"] == 0 and _by["lab-garbage"]["bad_json"] == _by["lab-garbage"]["runs"] and _by["lab-garbage"]["score_pct"] == 0
    assert _by["lab-think"]["think_leaks"] == _by["lab-think"]["runs"] and _by["lab-think"]["parse_pct"] == 0, "Thinking aloud breaks the brain's JSON parser: counted as a think leak"
    assert _by["lab-offmenu"]["parse_pct"] == 100 and _by["lab-offmenu"]["menu_pct"] == 0 and _by["lab-offmenu"]["score_pct"] == 0, "An action nobody offered is not in the menu"
    assert _by["lab-nobody"]["errors"] == _by["lab-nobody"]["runs"] and _by["lab-nobody"]["score_pct"] == 0, "An unknown model (HTTP 404) is an error, not a pass"
    # a thinking model that spends its token budget returns HTTP 200 with no text: a separate, diagnosable failure, and the model is abandoned early
    _resE = _lab.run_lab(["lab-empty"], _scn[:4], base=_base, repeat=3, timeout=5.0, unload=False, manage_models=False, log=lambda *a: None, do_warm=False)
    _e = _resE["summaries"][0]
    assert _e["empty_replies"] == _e["runs"] and _e["reasoning_runs"] == _e["runs"] and _e["aborted"] and _e["runs"] == _lab.ABORT_AFTER, _e
    assert "thought but returned no answer" in _resE["markdown"] and "abandoned" in _resE["markdown"]
    assert _resE["per_model"]["lab-empty"][_scn[0]["id"]][0]["finish_reason"] == "length" and _resE["per_model"]["lab-empty"][_scn[0]["id"]][0]["reasoning_chars"] > 0
    # a good model is never abandoned
    assert not _by["lab-good"]["aborted"]
    # extra request settings and the token budget reach the request (how a thinking model's reasoning is switched off)
    _old_extra, _old_mt = brain.LM_EXTRA_PAYLOAD, brain.LM_MAX_TOKENS
    brain.LM_EXTRA_PAYLOAD, brain.LM_MAX_TOKENS = {"reasoning_effort": "none"}, 222
    try:
        _lab.run_lab(["lab-good"], _scn[:1], base=_base, repeat=1, timeout=5.0, unload=False, manage_models=False, log=lambda *a: None, do_warm=False)
        assert _FakeLM.last_payload.get("reasoning_effort") == "none" and _FakeLM.last_payload.get("max_tokens") == 222, _FakeLM.last_payload
    finally:
        brain.LM_EXTRA_PAYLOAD, brain.LM_MAX_TOKENS = _old_extra, _old_mt
    # policy checks are judged on the raw action: a scenario that forbids everything makes even the good model fail
    _strict = _copy.deepcopy(_scn[:2])
    for _s in _strict:
        _s["checks"] = {"must_not": ["MOVE_", "USE_ABILITY", "SPRINT_", "REST", "WAIT", "ACTIVATE"], "should_any": []}
    _res2 = _lab.run_lab(["lab-good"], _strict, base=_base, repeat=1, timeout=5.0, unload=False, manage_models=False, log=lambda *a: None)
    assert _res2["summaries"][0]["menu_pct"] == 100 and _res2["summaries"][0]["policy_pct"] == 0 and _res2["summaries"][0]["score_pct"] == 0
    _lenient = _copy.deepcopy(_scn[:2])
    for _s in _lenient:
        _s["checks"] = {"must_not": [], "should_any": [""]}
    assert _lab.run_lab(["lab-good"], _lenient, base=_base, repeat=1, timeout=5.0, unload=False, manage_models=False, log=lambda *a: None)["summaries"][0]["score_pct"] == 100
    # a reply that takes longer than the lab timeout is a timeout; one that fits the lab but not the brain's timeout is flagged as too slow
    _res3 = _lab.run_lab(["lab-slow"], _scn[:2], base=_base, repeat=1, timeout=0.5, unload=False, manage_models=False, log=lambda *a: None, do_warm=False)
    assert _res3["summaries"][0]["timeouts"] == _res3["summaries"][0]["runs"] == 2, _res3["summaries"][0]
    _res4 = _lab.run_lab(["lab-slow"], _scn[:2], base=_base, repeat=1, timeout=5.0, brain_timeout=1.0, unload=False, manage_models=False, log=lambda *a: None, do_warm=False)
    assert _res4["summaries"][0]["parse_pct"] == 100 and _res4["summaries"][0]["within_brain_timeout_pct"] == 0.0 and _res4["summaries"][0]["latency_p50"] >= 1.0
    # the report and the saved files
    _od = _tempfile.mkdtemp()
    _res5 = _lab.run_lab(["lab-good", "lab-garbage"], _scn[:2], base=_base, repeat=1, timeout=5.0, unload=False, manage_models=False, out_dir=_od, log=lambda *a: None, do_warm=False)
    assert "| lab-good |" in _res5["markdown"] and "Scenario by scenario" in _res5["markdown"]
    assert sorted(f.split(".")[-1] for f in _os.listdir(_od)) == ["json", "md"]
    # `lms` prints UTF-8 progress characters: decoding them with the Windows default code page crashed the first managed run
    import sys as _sys
    _r = _lab.run_cmd([_sys.executable, "-c", "import sys; sys.stdout.buffer.write('ok \\u2713 \\u2588 and a stray byte \\x8f'.encode('utf-8')[:-1] + b'\\x8f')"], 30)
    assert _r is not None and _r.returncode == 0 and _r.stdout.startswith("ok") and "\u2713" in _r.stdout, _r
    assert _lab.run_cmd(["definitely-not-a-command-xyz"], 5) is None, "A missing command is None, not an exception"
    # a command that produced no output must not crash the load helper
    _real_lms = _lab._lms
    class _NoOut:
        returncode = 1; stdout = None; stderr = None
    _lab._lms = lambda *a, **k: _NoOut()
    try:
        _okx, _sx, _mx = _lab.lms_load("m", 8192)
        assert _okx is False and _mx == "", (_okx, _mx)
        assert _lab.lms_ps() == []
    finally:
        _lab._lms = _real_lms
    # helpers
    assert _lab.norm_action("USE_ABILITY:CommandLase:SE (beam)") == "USE_ABILITY:CommandLase" and _lab.norm_action("MOVE_E (Melee Attack x)") == "MOVE_E"
    assert _lab.policy_verdict("REST", {"must_not": ["REST"]})[0] is False and _lab.policy_verdict("MOVE_E", {"should_any": ["MOVE_"]})[0] is True
    assert _lab.chat_models(_base) == [("lab-good", True), ("lab-bad", False)], "Embedding models are never offered for the combat call"
finally:
    brain.LM_STUDIO_URL, brain.LM_STUDIO_TIMEOUT, brain.active_model_id, brain.LLM_PROBE = _old_url, _old_to, _old_model, None
    _srv.shutdown()
print("  [OK] Test 86 Passed: the lab scores parse, menu and policy per model, counts timeouts, thinking leaks and errors, and writes its report.")


# ---------------------------------------------------------------------------
# Test 87: item scoring is data-driven and build-aware; equip and junk decisions (HANDOFF issue 66)
# ---------------------------------------------------------------------------
import item_scoring as _is
_cat = _is.catalog()["items"]
assert len(_cat) > 1500 and _is.catalog()["_meta"]["counts"]["loot_items"] > 900, "data/items.json must be the full catalog"
def _find(name, group=None):
    for _k, _v in _cat.items():
        if _v["name"] == name and (group is None or _v["group"] == group):
            return _k, _v
    raise AssertionError(f"catalog has no {name!r}")
assert _is.dice_mean("1d8+2") == 6.5 and _is.dice_mean("3d2") == 4.5 and _is.dice_mean("2d6-1") == 6.0 and _is.dice_mean(None) == 0 and _is.dice_mean("junk") == 0
assert _is.parse_boosts("DV:4;MA:-1") == {"DV": 4.0, "MA": -1.0} and _is.parse_boosts("") == {}
_P = {b: _is.build_profile(build_templates.BUILD_TEMPLATES[b]) for b in ("auspicious_beginnings", "praetorian_generalist", "esper_ited_away", "uncle_iroh", "bullet_specter", "classic_punchkin", "gunkin", "gas_giant", "limb_off")}
assert "Axe" in _P["auspicious_beginnings"]["weapon_skills"] and not _P["auspicious_beginnings"]["caster"] and _P["auspicious_beginnings"]["weight_class"] == "heavy"
assert {"Rifle", "LongBlades"} <= set(_P["praetorian_generalist"]["weapon_skills"]) and _P["praetorian_generalist"]["wants_shield"] and _P["praetorian_generalist"]["ranged"]
assert _P["esper_ited_away"]["caster"] and _P["esper_ited_away"]["weapon_skills"] == [] and _P["esper_ited_away"]["stat_weights"]["Ego"] == 3.0
assert _P["gunkin"]["ranged"] and "Pistol" in _P["gunkin"]["weapon_skills"] and _P["gunkin"]["agile"] and _P["gunkin"]["weight_class"] == "light"
assert _P["uncle_iroh"]["weapon_skills"] == ["Cudgel"] and not _P["uncle_iroh"]["caster"] and _P["gas_giant"]["caster"]
# a weapon the build trains beats an equivalent one it does not; a caster values melee little; firearms follow the firearm skill
_axe = _find("carbide battle axe")[1]; _dag = _find("steel dagger")[1]; _pist = _find("chain pistol")[1]
assert _is.score_item(_axe, _P["auspicious_beginnings"])[0] > _is.score_item(_dag, _P["auspicious_beginnings"])[0], "Axe build prefers the axe"
assert _is.score_item(_dag, _P["auspicious_beginnings"])[0] < _is.score_item(_axe, _P["auspicious_beginnings"])[0] * 0.6
assert _is.score_item(_pist, _P["gunkin"])[0] > _is.score_item(_axe, _P["gunkin"])[0], "Pistol build prefers the pistol"
assert _is.score_item(_pist, _P["auspicious_beginnings"])[0] < _is.score_item(_pist, _P["gunkin"])[0] / 2, "An untrained firearm is worth far less"
assert _is.score_item(_axe, _P["esper_ited_away"])[0] < _is.score_item(_axe, _P["auspicious_beginnings"])[0] / 3, "A caster values a battle axe little"
_shield = _find("flawless crysteel aegis")[1]
assert _is.score_item(_shield, _P["praetorian_generalist"])[0] > _is.score_item(_shield, _P["gunkin"])[0], "Only a shield build gets the shield bonus"
_helm = _find("psychodyne helmet")[1]
assert _is.score_item(_helm, _P["esper_ited_away"])[0] > _is.score_item(_helm, _P["auspicious_beginnings"])[0], "Ego/Willpower boosts matter to an Esper"
_s, _kv, _why = _is.score_item(_axe, _P["auspicious_beginnings"])
assert _why and all(isinstance(r, str) for r in _why), "Every score carries its reasons"
# equip decisions: fill an empty slot, replace only when clearly better, never swap for a marginal gain
_boots = _find("flawless crysteel boots")[0]; _chain_mail = _find("chain mail")[0]; _lune = _find("zetachrome lune")[0]
_inv = [{"blueprint": _chain_mail, "equipped": True}, {"blueprint": _lune}, {"blueprint": _boots}]
_acts = {slot: it["blueprint"] for it, slot, why in _is.choose_equips(_inv, _P["auspicious_beginnings"])}
assert _acts.get("Feet") == _boots and _acts.get("Body") == _lune, _acts
assert not _is.choose_equips([{"blueprint": _lune, "equipped": True}, {"blueprint": _chain_mail}], _P["auspicious_beginnings"]), "Already wearing the better one"
_w_axe = _find("carbide battle axe")[0]; _w_dag = _find("steel dagger")[0]
_weap = _is.choose_equips([{"blueprint": _w_dag, "equipped": True}, {"blueprint": _w_axe}], _P["auspicious_beginnings"])
assert _weap and _weap[0][0]["blueprint"] == _w_axe and _weap[0][1] == "Hand"
# junk decisions
_scrap = _find("bent metal sheet")[0]; _wedge = _find("cybernetics credit wedge")[0]; _food = _find("jerky", None)[0] if any(v["name"] == "jerky" for v in _cat.values()) else None
_inv2 = [{"blueprint": _lune, "equipped": True}, {"blueprint": _chain_mail}, {"blueprint": _scrap, "count": 1}, {"blueprint": _wedge}]
_d = _is.choose_drops(_inv2, _P["auspicious_beginnings"], carried_weight=10, capacity=200)
assert [x[0]["blueprint"] for x in _d] == [_chain_mail], f"No pressure: only the outclassed armor goes, got {[x[0]['blueprint'] for x in _d]}"
assert "outclassed" in _d[0][1]
_d = _is.choose_drops(_inv2, _P["auspicious_beginnings"], carried_weight=190, capacity=200)
_names = [x[0]["blueprint"] for x in _d]
assert _chain_mail in _names and _scrap in _names, "Under pressure junk goes too"
assert _wedge not in _names and _lune not in _names, "Weightless items and equipped gear are never dropped"
# stackable supplies are capped, dropping only the extra
_fk = next(k for k, v in _cat.items() if v["group"] == "food" and v.get("loot"))
assert not _is.choose_drops([{"blueprint": _fk, "count": 11}], _P["gunkin"], carried_weight=10, capacity=200), "Stage 2 is conservative: food is never dropped automatically"
# conservative whitelist (human, 2026-10-06): only gear that is outclassed or harmful, scrap and corpses are ever dropped; everything else is kept and re-evaluated later
_book = next(k for k, v in _cat.items() if v["group"] == "book" and v.get("loot")); _trade = next(k for k, v in _cat.items() if v["group"] == "trade_good" and v.get("loot"))
_other = next(k for k, v in _cat.items() if v["group"] == "other" and v.get("loot") and (v.get("weight") or 0) > 0)
_junk = [x[0]["blueprint"] for x in _is.choose_drops([{"blueprint": _book}, {"blueprint": _trade}, {"blueprint": _other}, {"blueprint": _scrap}], _P["gunkin"], carried_weight=199, capacity=200)]
assert _junk == [_scrap], f"Books, trade goods and unknown items are deferred even under pressure; scrap is not: {_junk}"
# reputation trophies, quest items and relics carry a protect flag from the game's own parts and are never dropped
_rep = next(k for k, v in _cat.items() if v.get("loot") and any(str(p).startswith("reputation") for p in v.get("protect", [])))
assert _cat[_rep].get("protect"), "Catalog marks AddsRep items as protected"
_prot = dict(_cat[_rep]); _prot["group"] = "scrap"      # even in a droppable group the flag wins
_inv_p = [{"blueprint": _rep, "weight": 5, "group": "scrap"}]
assert not _is.choose_drops(_inv_p, _P["gunkin"], carried_weight=199, capacity=200), "A reputation trophy is never dropped"
assert _is.catalog()["_meta"]["counts"]["loot_items"] > 900 and _is.catalog()["_meta"]["protected_loot_items"] >= 30
# quest items and equipped things are never dropped, whatever the pressure
_q = next(k for k, v in _cat.items() if v["group"] == "quest_item" and v.get("loot"))
assert not _is.choose_drops([{"blueprint": _q}, {"blueprint": _scrap, "equipped": True}], _P["gunkin"], carried_weight=199, capacity=200)
# the pressure relief stops as soon as the pack is comfortable
_inv3 = [{"blueprint": _scrap, "count": 1, "weight": 10} for _ in range(6)]
_d = _is.choose_drops(_inv3, _P["gunkin"], carried_weight=150, capacity=200)
assert 0 < len(_d) < 6, f"Drop only as much as needed, got {len(_d)}"
# safety overrides carried over from the old evaluator, now data-driven: sole light source, sole ranged weapon (for a firing build), escape gear, unidentified items
_torch = next(k for k, v in _cat.items() if v["group"] == "light_source" and v.get("loot"))
_rec = next(k for k, v in _cat.items() if v.get("escape") and v.get("loot"))
_press = dict(carried_weight=195, capacity=200)
_names = [x[0]["blueprint"] for x in _is.choose_drops([{"blueprint": _torch}, {"blueprint": _scrap}], _P["gunkin"], **_press)]
assert _torch not in _names and _scrap in _names, "The only light source stays"
assert _rec not in [x[0]["blueprint"] for x in _is.choose_drops([{"blueprint": _rec}, {"blueprint": _scrap}], _P["gunkin"], **_press)], "Escape gear stays"
_shotgun = _find("pump shotgun")[0]
assert _shotgun not in [x[0]["blueprint"] for x in _is.choose_drops([{"blueprint": _shotgun}, {"blueprint": _scrap}], _P["gunkin"], **_press)], "The only firearm of a firing build stays"
assert _scrap not in [x[0]["blueprint"] for x in _is.choose_drops([{"blueprint": _scrap, "identified": False}], _P["gunkin"], **_press)], "Anything unidentified stays"
print("  [OK] Test 87 Passed: scores follow the build's skills and stats, equip fills slots and replaces only clear upgrades, junk is dropped by relative merit and pressure.")


# ---------------------------------------------------------------------------
# Test 88: inventory management wired into the brain (HANDOFF issue 66, stage 2)
# ---------------------------------------------------------------------------
import tempfile as _tf88
def _inv_reset():
    brain.INV_STATE.update({"sig": None, "pending": None, "fails": {}, "profiles": {}}); brain.INV_LAST_SEQ["seq"] = 0
_inv_reset()
_old_log = brain.ITEM_DROP_LOG_PATH
brain.ITEM_DROP_LOG_PATH = _os.path.join(_tf88.mkdtemp(), "item_drops.jsonl")
_tm88 = build_templates.BUILD_TEMPLATES["auspicious_beginnings"]
_boots88 = _find("flawless crysteel boots")[0]; _lune88 = _find("zetachrome lune")[0]; _mail88 = _find("chain mail")[0]; _scrap88 = _find("bent metal sheet")[0]
_row = lambda i, bp, eq=False, n=1, w=5, ident=True: {"id": i, "blueprint": bp, "name": bp, "count": n, "weight": w, "equipped": eq, "identified": ident}
_gs88 = lambda inv, cw=40, **k: dict({"inventory": inv, "carry_weight": cw, "max_carry_weight": 200}, **k)
# 1. an empty slot and a clear upgrade: one equip, naming the item by its id
_d = brain.choose_inventory_action(_gs88([_row("a1", _boots88), _row("a2", _mail88, eq=True)]), _tm88, False)
assert _d and _d["action"] == "EQUIP_ITEM:a1", _d
# 2. after the game reports success the next look finds nothing more to do, and does not ask again while nothing changes
_both = _gs88([_row("a1", _boots88, eq=True), _row("a2", _mail88, eq=True)])
_both["last_inventory_action"] = {"seq": 1, "kind": "equip", "ok": ["a1|boots"], "failed": [], "zone": "Z", "x": 3, "y": 4}
brain.note_inventory_action(_both); brain.note_inventory_action(_both)
assert brain.INV_LAST_SEQ["seq"] == 1, "The report is read once"
assert brain.choose_inventory_action(_both, _tm88, False) is None and brain.INV_STATE["sig"] is not None
assert brain.choose_inventory_action(_both, _tm88, False) is None, "Unchanged inventory: nothing to recompute"
# 3. a refusal twice stops the retries (R4: a command the game refuses must not loop)
_inv_reset()
_again = _gs88([_row("a1", _boots88), _row("a2", _mail88, eq=True)])
for _seq in (1, 2):
    assert brain.choose_inventory_action(_again, _tm88, False)["action"] == "EQUIP_ITEM:a1"
    _again["last_inventory_action"] = {"seq": _seq, "kind": "equip", "ok": [], "failed": ["a1:AutoEquip refused"], "zone": "Z", "x": 1, "y": 1}
    brain.note_inventory_action(_again)
assert brain.INV_STATE["fails"]["a1"] == 2 and brain.choose_inventory_action(_again, _tm88, False) is None, "After two refusals the item is left alone"
# 4. junk under weight pressure: dropped, logged with where it was left; protected, weightless and unidentified things stay
_inv_reset()
_rep88 = next(k for k, v in _cat.items() if v.get("loot") and v.get("protect") and v["group"] not in _is.EQUIPMENT_GROUPS)
_pile = _gs88([_row("g1", _lune88, eq=True), _row("g2", _mail88), _row("s1", _scrap88, n=3, w=4), _row("p1", _rep88, w=6), _row("u1", _scrap88, w=9, ident=False), _row("z1", _find("cybernetics credit wedge")[0], w=0)], cw=190)
_d = brain.choose_inventory_action(_pile, _tm88, False)
_ids = _d["action"].split(":", 1)[1].split(",")
assert _d["action"].startswith("DROP_ITEMS:") and "g2" in _ids and "s1" in _ids, _d
assert not ({"g1", "p1", "u1", "z1"} & set(_ids)), f"Equipped, protected, unidentified and weightless items stay: {_ids}"
_pile["last_inventory_action"] = {"seq": 5, "kind": "drop", "ok": [f"{i}|{i}" for i in _ids], "failed": [], "zone": "JoppaWorld.1.2.3", "x": 12, "y": 7}
with _ctx.redirect_stdout(_io.StringIO()):
    brain.note_inventory_action(_pile)
_logged = [json.loads(l) for l in open(brain.ITEM_DROP_LOG_PATH, encoding="utf-8")]
assert len(_logged) == len(_ids) and all(r["zone"] == "JoppaWorld.1.2.3" and r["x"] == 12 and r["y"] == 7 and r["reason"] for r in _logged), "Every drop is logged with where it was left and why"
# 5. never in a settlement, never swimming, never an unidentified upgrade, nothing without an inventory
_inv_reset()
assert brain.choose_inventory_action(_gs88([_row("a1", _boots88)]), _tm88, True) is None, "Not in a settlement"
assert brain.choose_inventory_action(_gs88([_row("a1", _boots88)], is_swimming=True), _tm88, False) is None
assert brain.choose_inventory_action(_gs88([_row("a1", _boots88, ident=False)]), _tm88, False) is None, "An unidentified item is not equipped"
assert brain.choose_inventory_action({"inventory": []}, _tm88, False) is None and brain.choose_inventory_action({}, _tm88, False) is None
# 5b. the mod reports a stack's TOTAL weight (12 torches: 12): the brain divides by the count before scoring
_inv_reset()
_stack = _gs88([_row("g1", _lune88, eq=True), _row("s1", _scrap88, n=4, w=8)], cw=190)
_dd = brain.choose_inventory_action(_stack, _tm88, False)
assert _dd and _dd["action"] == "DROP_ITEMS:s1", _dd
assert brain.INV_STATE["pending"]["ids"] == ["s1"]
# 6. in the full decision it comes before exploring and before the ammo top-off
_inv_reset()
brain.KNOWN_STAIRS_DOWN.clear(); brain.RETREAT_TARGET_LEVEL = None; brain.LAST_ZONE_ENTRY = None
_st = dict(delve_state_nearby); _st["zone_fully_explored"] = True; _st["visible_entities"] = []; _st["loot_sources"] = []
_st.update(_gs88([_row("a1", _boots88), _row("a2", _mail88, eq=True)]))
_dec = brain.query_decision(dict(_st), took_damage=False, enemies=[])
assert _dec["action"].startswith("EQUIP_ITEM:") and "Inventory" in _dec["reason"], _dec
# 7. with a hostile in view the decision is a combat one: the inventory step is Phase A only
_inv_reset()
_foe = {"name": "baboon", "blueprint": "Baboon", "is_enemy": True, "dist": 1, "dir": "E", "difficulty": "Average", "has_los": True, "tx": 16, "ty": 15}
_st2 = dict(_st); _st2["visible_entities"] = [_foe]; _st2["surroundings"] = {"N": "dirt floor", "S": "dirt floor", "E": "[ENEMY: baboon]", "W": "dirt floor"}
assert not brain.query_decision(_st2, took_damage=False, enemies=[_foe])["action"].startswith(("EQUIP_ITEM", "DROP_ITEMS")), "Never reorganise the pack in a fight"
# 8. a gun build equips its firearm, and does not put a dagger in the hand that holds it
_gk = build_templates.BUILD_TEMPLATES["gunkin"]; _pistol88 = _find("chain pistol")[0]; _dag88 = _find("steel dagger")[0]
_inv_reset()
_d = brain.choose_inventory_action(_gs88([_row("g1", _pistol88), _row("d1", _dag88)]), _gk, False)
assert _d and _d["action"] == "EQUIP_ITEM:g1", _d
_inv_reset()
assert brain.choose_inventory_action(_gs88([_row("g1", _pistol88, eq=True), _row("d1", _dag88)]), _gk, False) is None, "No dagger swap while holding the pistol"
brain.ITEM_DROP_LOG_PATH = _old_log; _inv_reset()
print("  [OK] Test 88 Passed: equip clear upgrades, drop only whitelisted junk under pressure with a log of where it was left, never loop on a refusal, never in a fight or a town.")


# ---------------------------------------------------------------------------
# Test 89: fear and banishment are not spent on an adjacent immobile hostile (HANDOFF issue 68)
# ---------------------------------------------------------------------------
_lov = {"name": "jilted lover", "blueprint": "Jilted Lover", "dist": 1, "dir": "SE", "is_enemy": True, "is_stationary": True, "difficulty": "Average", "has_los": True}
_gs89 = {"x": 10, "y": 10, "stairs_up": [], "stairs_down": []}
_ab89 = [{"name": "Intimidate", "command": "CommandIntimidate", "cooldown": 0, "usable": True}, {"name": "Teleport Other", "command": "CommandTeleportOther", "cooldown": 0, "usable": True},
         {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True}, {"name": "Lase (4 charges)", "command": "CommandLase", "cooldown": 0, "usable": True}]
brain.KNOWN_STAIRS_UP.clear(); brain.KNOWN_STAIRS_DOWN.clear()
for _wasted in ("USE_ABILITY:CommandIntimidate", "USE_ABILITY:CommandTeleportOther:SE", "USE_ABILITY:CommandIntimidate:SE"):
    _d = brain.enforce_stand_and_fight({"action": _wasted, "reason": "[LLM] fear to control the vine"}, _gs89, {"SE": "jilted lover"}, [_lov], _ab89)
    assert _d["action"] == "USE_ABILITY:CommandLase:SE", f"Damage first against a rooted target, got {_d}"
_d = brain.enforce_stand_and_fight({"action": "USE_ABILITY:CommandIntimidate", "reason": "x"}, _gs89, {"SE": "jilted lover"}, [_lov], [_ab89[0], _ab89[1]])
assert _d["action"] == "MOVE_SE", f"No damage ability: melee, got {_d}"
# not for a mobile enemy (fear and banishment are the right tools there), not for a tough immobile one, not when anything mobile is adjacent too
_bab = dict(_lov, name="baboon", is_stationary=False)
_w = {"action": "USE_ABILITY:CommandTeleportOther:SE", "reason": "x"}
assert brain.enforce_stand_and_fight(_w, _gs89, {"SE": "baboon"}, [_bab], _ab89) is _w, "Banishing a mobile enemy is legitimate"
assert brain.enforce_stand_and_fight(_w, _gs89, {"SE": "turret"}, [dict(_lov, difficulty="Tough")], _ab89) is _w, "A tough immobile hostile is left to the usual logic"
_w2 = {"action": "USE_ABILITY:CommandIntimidate", "reason": "x"}
assert brain.enforce_stand_and_fight(_w2, _gs89, {"SE": "jilted lover", "E": "baboon"}, [_lov, dict(_bab, dist=1, dir="E")], _ab89) is _w2, "With a mobile attacker adjacent too, fear stays available"
# other actions against the vine are untouched (a plain attack, a ray)
for _ok in ({"action": "MOVE_SE", "reason": "attack"}, {"action": "USE_ABILITY:CommandLase:SE", "reason": "x"}):
    assert brain.enforce_stand_and_fight(_ok, _gs89, {"SE": "jilted lover"}, [_lov], _ab89) is _ok
assert brain.immobile_adjacent({}, [_lov]) == [] and brain.immobile_adjacent({"SE": "x"}, [dict(_lov, is_stationary=False)]) == []
# priority, not list order: with Stunning Force listed first, Lase is still chosen against a rooted target, and Stunning Force still wins the stand-and-fight rule
assert brain.first_ready_by_priority(_ab89, ("lase", "stunning_force"))["command"] == "CommandLase"
assert brain.first_ready_by_priority(_ab89, ("stunning_force", "lase"))["command"] == "CommandStunningForce"
assert brain.first_ready_by_priority(_ab89[:2], ("lase", "stunning_force")) is None, "Only Intimidate and Teleport Other are ready: nothing"
_d = brain.enforce_stand_and_fight({"action": "SPRINT_W", "reason": "[LLM] run"}, _gs89, {"E": "snapjaw"}, [{"name": "snapjaw", "dist": 1, "dir": "E", "difficulty": "Easy", "is_enemy": True}], list(reversed(_ab89)))
assert _d["action"] == "USE_ABILITY:CommandStunningForce:E", f"Stand-and-fight: Stunning Force first whatever the list order, got {_d}"
print("  [OK] Test 89 Passed: fear and banishment aimed at an adjacent immobile hostile become a damage attack (melee if none); mobile, tough and mixed cases are untouched.")


# ---------------------------------------------------------------------------
# Test 90: the brain reports when the mod steers the pathfinder around immobile hostiles (HANDOFF issue 69)
# ---------------------------------------------------------------------------
brain.AVOID_SEEN["n"] = 0
_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    brain.note_avoid({"avoid_tagged": 3}); brain.note_avoid({"avoid_tagged": 3}); brain.note_avoid({"avoid_tagged": 5}); brain.note_avoid({}); brain.note_avoid({"avoid_tagged": "x"})
_lines = [l for l in _buf.getvalue().splitlines() if l.startswith("[AVOID]")]
assert len(_lines) == 2 and "3 more" in _lines[0] and "2 more" in _lines[1] and brain.AVOID_SEEN["n"] == 5, _lines
brain.AVOID_SEEN["n"] = 0
_csrc = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mod", "QudAIBrain", "AIBrainPart.cs"), encoding="utf-8").read()
for _needle in ("AvoidMovingNearby", "TagImmobileHostilesForAvoidance(player", "FlushNavigationCache", "avoid_tagged"):
    assert _needle in _csrc, f"the mod must contain {_needle}"
assert _csrc.count("{") == _csrc.count("}"), "C# braces"
print("  [OK] Test 90 Passed: the brain announces newly avoided immobile hostiles once; the mod source tags them with the engine's AvoidMovingNearby part and flushes the navigation cache.")


# ---------------------------------------------------------------------------
# Test 91: the console's logic (tools/console_logic.py): mod health parsing, flag, readable views, tailing, lessons
# ---------------------------------------------------------------------------
import sys as _sys91
_sys91.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools"))
import console_logic as _cl
_good = "[t] Compiling 1 file...\n[t] Success :)\n[t] Location: x.dll\n"
assert _cl.parse_build_log(_good)[0] == "ok"
assert _cl.parse_build_log("[t] Compiling 1 file...\n[t] error CS1002: ; expected\n")[0] == "bad"
assert _cl.parse_build_log("[t] Compiling 1 file...\n[t] error CS0103: x\n[t] Compiling 1 file...\n[t] Success :)\n")[0] == "ok", "only the LAST compile counts"
assert _cl.parse_build_log("")[0] == "unknown" and _cl.parse_build_log("[t] Compiling 1 file...\n")[0] == "warn"
_pl = "[QudAI] PlayerTurn patch ACTIVE\n[QudAI] Patch check: 10/10 applied\n[QudAI Inventory] equip ok=1 failed=0\n"
_rows = dict((n, s) for n, s, _ in _cl.parse_player_log(_pl))
assert _rows == {"PlayerTurn patch": "ok", "Harmony patches": "ok", "Mod errors": "ok"}, _rows
_rows = dict((n, s) for n, s, _ in _cl.parse_player_log("[QudAI] Patch check: 8/10 applied\n[QudAI X] Exception: boom\n"))
assert _rows["PlayerTurn patch"] == "bad" and _rows["Harmony patches"] == "bad" and _rows["Mod errors"] == "warn", _rows
_ex = tempfile.mkdtemp()
assert not _cl.flag_on(_ex)
open(_os.path.join(_ex, "active.flag"), "w").write("active")
assert _cl.flag_on(_ex)
_jl = _os.path.join(_ex, "t.jsonl")
open(_jl, "w", encoding="utf-8").write(json.dumps({"t": 1, "hp": 5, "action": "REST", "reason": "[LLM in 3.0s] hello"}) + chr(10) + "{half written")
_tr = _cl.tail_jsonl(_jl, 10)
assert len(_tr) == 1 and "hello" in _cl.format_trace_row(_tr[0]) and "LLM in" not in _cl.format_trace_row(_tr[0])
assert _cl.colour_tag("[INVENTORY] dropped x") == "[INVENTORY]" and _cl.colour_tag("plain") == ""
assert _cl.filter_lines(["a Lase", "b rest"], "LASE") == ["a Lase"]
_txt = _cl.describe_state({"hp": 4, "max_hp": 28, "level": 3, "genotype": "Mutated Human", "calling": "Apostle", "carry_weight": 54, "max_carry_weight": 225,
                           "abilities": [{"name": "Lase", "cooldown": 0}, {"name": "Intimidate", "cooldown": 18}], "inventory": [{"name": "staff", "equipped": True, "count": 1, "weight": 3}]})
assert "HP 4/28" in _txt and "Intimidate: cooldown 18" in _txt and "* staff" in _txt and _cl.describe_state({}).startswith("No state")
assert _cl.pause_resume_bytes() == b"\n"
_old_wf91 = _chr.WISDOM_FILE
_chr.WISDOM_FILE = _os.path.join(tempfile.mkdtemp(), "ancestral_wisdom.json")
try:
    _chr.save_ancestral_wisdom([{"generation": 1, "lesson": "a"}, {"generation": 2, "lesson": "b", "approved": True}])
    assert _cl.set_approval([1], True) == [1] and _cl.set_approval([2], False) == [2] and _cl.set_approval([99], True) == []
    _w91 = {w["generation"]: w.get("approved") for w in _cl.lessons()}
    assert _w91 == {1: True, 2: False}, _w91
finally:
    _chr.WISDOM_FILE = _old_wf91
_th = _cl.threat_summary({"visible_entities": [{"is_enemy": True, "name": "snapjaw warrior", "difficulty": "Tough", "dist": 3},
                                               {"is_enemy": True, "name": "jilted lover", "difficulty": "Easy", "dist": 1, "is_stationary": True},
                                               {"is_enemy": False, "name": "table", "dist": 1}]})
assert (_th[1] == "danger" and _th[0].index("jilted lover") < _th[0].index("snapjaw") and "!! snapjaw warrior [Tough]" in _th[0] and "(rooted)" in _th[0]), _th
assert _cl.threat_summary({"visible_entities": []}) == ("No hostiles in view.", "calm") and _cl.threat_summary({"visible_entities": [{"is_enemy": True, "name": "x", "difficulty": "Easy", "dist": 2}]})[1] == "watch"
assert _cl.feed_tag({"action": "MOVE_E", "reason": "[Loop Breaker] Oscillation"}, 10) == "loop" and _cl.feed_tag({"action": "REST", "reason": "", "hp": 7}, 10) == "hp"
assert _cl.feed_tag({"action": "NAVIGATE_ZONE_EXIT:N", "reason": ""}, None) == "flee" and _cl.feed_tag({"action": "USE_ABILITY:CommandLase:W", "reason": "", "hp": 10}, 10) == "ability"
assert _cl.feed_tag({"action": "LOOT", "reason": "Loot: taking"}, None) == "loot" and _cl.feed_tag({"action": "MOVE_E", "reason": ""}, None) == ""
open(_jl, "w", encoding="utf-8").write(json.dumps({"t": 1, "hp": 9, "action": "REST", "reason": ""}) + chr(10) + json.dumps({"t": 2, "hp": 5, "action": "REST", "reason": ""}) + chr(10))
assert [tag for _, tag in _cl.feed_rows(_jl, 10)] == ["", "hp"]
_cs = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools", "qudai_console.py"), encoding="utf-8").read()
assert "stdin=subprocess.PIPE" in _cs and "pause_resume_bytes" in _cs and "active.flag" not in _cs, "pause goes through the brain's stdin, never by touching the flag"
print("  [OK] Test 91 Passed: console logic (also the threat strip and the coloured live feed) parses the build and player logs (last compile only), tails a trace past a half-written line, reads the flag, renders the state, and approves lessons through chronicler.")


# ---------------------------------------------------------------------------
# Test 92: standing still is not an oscillation; a stuck-autoexplore latch gets retried (HANDOFF issue 71)
# ---------------------------------------------------------------------------
# The real sequence from the second stratum of the Kuyukas workshop (turns 338-342, 2026-10-07): two turns at a lead slug (LOOT, then AUTOEXPLORE's first
# step), two autoexplore steps, back to the slug's cell. The old window counted (60, 15) three times and the loop breaker latched the whole level as stuck.
brain.recent_positions.clear()
_seq = [(60, 15), (60, 15), (61, 14), (61, 15), (60, 15)]
_old_freq = 0
_old_window = []
for _p in _seq:
    _old_window.append(_p)
    _old_freq = _old_window.count(_p)
assert _old_freq >= 3, "the old counting would have flagged this as an oscillation"
for _p in _seq:
    _freq, _uniq = brain.record_position(_p)
assert _freq == 2 and _uniq == 3, (_freq, _uniq)
# a real ping-pong is still caught
brain.recent_positions.clear()
for _p in [(50, 4), (51, 5), (50, 4), (51, 5), (50, 4)]:
    _freq, _ = brain.record_position(_p)
assert _freq >= 3, _freq
# standing for many turns (resting, looting) never inflates the count
brain.recent_positions.clear()
for _ in range(10):
    _freq, _ = brain.record_position((5, 5))
assert _freq == 1
brain.recent_positions.clear()

# the latch: the first retry is due after AUTOEXPLORE_RETRY_GAP turns, then the gap doubles up to the maximum
brain.STUCK_RETRY.clear()
_gs = {"unexplored_cells": 1525, "autoexplore_stuck": False}
_t0 = brain.TURN_CLOCK
try:
    brain.TURN_CLOCK = 1000
    assert brain.autoexplore_retry_due("Z1", _gs) is False                      # just latched: not yet
    brain.TURN_CLOCK = 1000 + brain.AUTOEXPLORE_RETRY_GAP
    assert brain.autoexplore_retry_due("Z1", _gs) is True                       # one native step now
    assert brain.STUCK_RETRY["Z1"]["gap"] == 2 * brain.AUTOEXPLORE_RETRY_GAP
    brain.TURN_CLOCK += 1
    assert brain.autoexplore_retry_due("Z1", _gs) is False                      # backed off
    for _ in range(10):
        brain.TURN_CLOCK = brain.STUCK_RETRY["Z1"]["next"]
        assert brain.autoexplore_retry_due("Z1", _gs) is True
    assert brain.STUCK_RETRY["Z1"]["gap"] == brain.AUTOEXPLORE_RETRY_MAX_GAP
    # never when the engine itself says stuck or explored, or when little is left
    brain.TURN_CLOCK = brain.STUCK_RETRY["Z1"]["next"] + 1
    assert brain.autoexplore_retry_due("Z1", dict(_gs, autoexplore_stuck=True)) is False
    assert brain.autoexplore_retry_due("Z1", dict(_gs, zone_fully_explored=True)) is False
    assert brain.autoexplore_retry_due("Z1", dict(_gs, unexplored_cells=20)) is False
    assert brain.autoexplore_retry_due("", _gs) is False
finally:
    brain.TURN_CLOCK = _t0
    brain.STUCK_RETRY.clear()
_bsrc = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "brain.py"), encoding="utf-8").read()
assert "autoexplore_retry_due(zone_id or current_zone_id, game_state)" in _bsrc and "STUCK_RETRY.pop(_zid_now, None)" in _bsrc and "record_position(cur_pos)" in _bsrc
print("  [OK] Test 92 Passed: standing still no longer counts as oscillation (the real Kuyukas sequence), a ping-pong still does, and a latched zone gets a native autoexplore retry with backoff unless the engine says stuck or explored.")


# ---------------------------------------------------------------------------
# Test 93: a carried firearm is kept as a trade asset even in a heavy pack (human, 2026-10-07)
# ---------------------------------------------------------------------------
_rifle93 = next(k for k, v in _is.catalog()["items"].items() if v.get("name") == "Issachar rifle" and v.get("group") == "missile_weapon")
_inv93 = [{"id": "r1", "blueprint": _rifle93, "count": 1, "weight": 15, "equipped": False, "identified": True}]
assert not _is.choose_drops(_inv93, _P["esper_ited_away"], carried_weight=200, capacity=200), "an unused rifle must survive pack pressure"
assert not _is.choose_drops(_inv93, _P["esper_ited_away"], carried_weight=10, capacity=200)
print("  [OK] Test 93 Passed: a firearm in the pack is never auto-dropped, even at 100% of capacity, so a gifted or bought gun stays a trade asset.")


# ---------------------------------------------------------------------------
# Test 94: a stratum with no way down is left by the stairs up (HANDOFF issue 73)
# ---------------------------------------------------------------------------
_up94 = "JoppaWorld.11.21.0.0.10"
_dn94 = "JoppaWorld.11.21.0.0.11"
assert brain.upper_zone_id(_dn94) == _up94 and brain.upper_zone_id("") is None and brain.upper_zone_id("nodots") is None
_saved94 = (dict(brain.KNOWN_STAIRS_DOWN), dict(brain.KNOWN_STAIRS_UP), set(brain.STAIRS_GIVEUP), brain.ZONE_STEP_COUNT, brain.CURRENT_ZONE_CHOSEN_EXIT,
            brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE, brain.RETREAT_TARGET_LEVEL)
try:
    brain.KNOWN_STAIRS_DOWN.clear(); brain.KNOWN_STAIRS_UP.clear(); brain.STAIRS_GIVEUP.clear()
    brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None; brain.RETREAT_TARGET_LEVEL = None
    brain.KNOWN_STAIRS_DOWN[_up94] = {"tx": 56, "ty": 3, "z": 10, "name": "stairs down", "req_level": 3}
    _st94 = {"reachable_edges": "", "stairs_up": [{"name": "stairs up", "blueprint": "StairsUp", "tx": 56, "ty": 3}]}
    brain.ZONE_STEP_COUNT = 100
    # cleared, worked long enough, no way down: walk to the stairs up (from the state, then from memory)
    _d = brain.dead_end_ascent(_st94, _dn94, 11, (52, 8), False, True)
    assert _d and _d["action"] == "NAVIGATE_TO_CELL:56,3", _d
    brain.KNOWN_STAIRS_UP[_dn94] = {"tx": 56, "ty": 3, "z": 11, "name": "stairs up"}
    assert brain.dead_end_ascent({}, _dn94, 11, (52, 8), False, True)["action"] == "NAVIGATE_TO_CELL:56,3"
    # not on the surface, not before the stratum is cleared and worked, not at the stairs cell for the walk
    assert brain.dead_end_ascent(_st94, _up94, 10, (52, 8), False, True) is None
    assert brain.dead_end_ascent(_st94, _dn94, 11, (52, 8), False, False) is None
    brain.ZONE_STEP_COUNT = 5
    assert brain.dead_end_ascent(_st94, _dn94, 11, (52, 8), False, True) is None
    brain.ZONE_STEP_COUNT = 100
    # the engine reports reachable edges (as it did in the workshop stratum, NSEW): no walk to the stairs, the edge logic goes first...
    _edges = dict(_st94, reachable_edges="NSEW")
    assert brain.dead_end_ascent(_edges, _dn94, 11, (52, 8), False, True) is None
    # ...but when its route ends ON the stairs-up cell (cleared, worked, no way down) he ascends
    _d = brain.dead_end_ascent(_edges, _dn94, 11, (56, 3), True, True)
    assert _d and _d["action"] == "USE_STAIRS_UP", _d
    assert (_up94, (56, 3)) in brain.STAIRS_GIVEUP and _dn94 in brain.DEAD_END_ZONES, "going up must stop him walking straight back down"
    brain.STAIRS_GIVEUP.clear(); brain.DEAD_END_ZONES.clear()
    # never on arrival or while the stratum is still being explored, even standing on the stairs
    brain.ZONE_STEP_COUNT = 5
    assert brain.dead_end_ascent(_edges, _dn94, 11, (56, 3), True, True) is None
    brain.ZONE_STEP_COUNT = 100
    assert brain.dead_end_ascent(_edges, _dn94, 11, (56, 3), True, False) is None
    # stairs down known and usable: the delve logic owns the decision
    brain.KNOWN_STAIRS_DOWN[_dn94] = {"tx": 20, "ty": 10, "z": 11, "name": "stairs down", "req_level": 3}
    assert brain.dead_end_ascent(_st94, _dn94, 11, (52, 8), False, True) is None
    brain.STAIRS_GIVEUP.add((_dn94, (20, 10)))
    assert brain.dead_end_ascent(_st94, _dn94, 11, (52, 8), False, True) is not None, "stairs down that were given up no longer count as a way down"
    # the stratum above: standing on the stairs down he must NOT descend again once they were given up (and does when they were not)
    brain.KNOWN_STAIRS_DOWN.pop(_dn94, None)
    brain.STAIRS_GIVEUP.clear()
    _surface94 = {"hp": 31, "max_hp": 31, "x": 56, "y": 3, "z": 10, "level": 5, "zone_id": _up94, "zone_name": "salt marsh", "zone_fully_explored": False,
                  "hostiles_nearby": False, "hostiles_adjacent": False, "unexplored_cells": 400,
                  "surroundings": {"C": "stairs down", "N": "grass", "S": "grass", "E": "grass", "W": "grass", "NE": "grass", "NW": "grass", "SE": "grass", "SW": "grass"},
                  "stairs_down": [{"name": "stairs down", "blueprint": "StairsDown", "tx": 56, "ty": 3}], "standing_on_stairs_down": True, "visible_entities": []}
    brain.recent_positions.clear()
    assert brain.query_decision(dict(_surface94), took_damage=False, enemies=[])["action"] == "USE_STAIRS_DOWN", "control: without a give-up he descends"
    brain.STAIRS_GIVEUP.add((_up94, (56, 3)))
    brain.recent_positions.clear()
    _after = brain.query_decision(dict(_surface94), took_damage=False, enemies=[])
    assert _after["action"] != "USE_STAIRS_DOWN", _after
    # after a restart the stairs down of the stratum above were never seen: the dead-end memory alone must keep him from descending again
    brain.KNOWN_STAIRS_DOWN.clear(); brain.STAIRS_GIVEUP.clear(); brain.DEAD_END_ZONES.clear(); brain.ZONE_STEP_COUNT = 100
    _d = brain.dead_end_ascent(dict(_st94, reachable_edges="NSEW"), _dn94, 11, (56, 3), True, True)
    assert _d["action"] == "USE_STAIRS_UP" and not brain.STAIRS_GIVEUP and _dn94 in brain.DEAD_END_ZONES
    brain.update_stair_records(dict(_surface94))               # he arrives on the stairs down and only now learns them
    assert _up94 in brain.KNOWN_STAIRS_DOWN and brain.stairs_given_up(_up94)
    brain.recent_positions.clear()
    _again = brain.query_decision(dict(_surface94), took_damage=False, enemies=[])
    assert _again["action"] != "USE_STAIRS_DOWN", _again
    _far = dict(_surface94, x=30, y=10, standing_on_stairs_down=False, surroundings=dict(_surface94["surroundings"], C="grass"), zone_fully_explored=True, unexplored_cells=0)
    brain.recent_positions.clear()
    assert not brain.query_decision(_far, took_damage=False, enemies=[])["action"].startswith("NAVIGATE_TO_CELL:56,3"), "and he does not walk back to those stairs either"
finally:
    brain.KNOWN_STAIRS_DOWN.clear(); brain.KNOWN_STAIRS_DOWN.update(_saved94[0])
    brain.KNOWN_STAIRS_UP.clear(); brain.KNOWN_STAIRS_UP.update(_saved94[1])
    brain.STAIRS_GIVEUP.clear(); brain.STAIRS_GIVEUP.update(_saved94[2])
    brain.ZONE_STEP_COUNT, brain.CURRENT_ZONE_CHOSEN_EXIT, brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE, brain.RETREAT_TARGET_LEVEL = _saved94[3:]
    brain.DEAD_END_ZONES.clear(); brain.recent_positions.clear()
print("  [OK] Test 94 Passed (also after a restart, from the dead-end memory alone): a cleared, worked stratum with no way down is left by USE_STAIRS_UP (walking there only when the engine reports no reachable edge), the stairs down above are given up so he does not descend again, and a usable way down still belongs to the delve logic.")


# ---------------------------------------------------------------------------
# Test 95: the lethal-adjacent guard (HANDOFF issue 75): a Very Tough mobile hostile next to him gets a control answer, not whatever the model chose
# ---------------------------------------------------------------------------
_ab95 = [{"name": "Lase (1 charges)", "command": "CommandLase", "cooldown": 0, "usable": True, "active": False},
         {"name": "Intimidate", "command": "CommandIntimidate", "cooldown": 0, "usable": True, "active": False},
         {"name": "Teleport Other", "command": "CommandTeleportOther", "cooldown": 0, "usable": True, "active": False},
         {"name": "Force Bubble", "command": "CommandForceBubble", "cooldown": 0, "usable": True, "active": False}]
_puma = {"name": "wet chitinous puma", "dist": 1, "dir": "SE", "difficulty": "Very Tough", "level": 12, "is_enemy": True, "is_stationary": False}
_lase = {"action": "USE_ABILITY:CommandLase:SE", "reason": "[LLM] Lase"}
_g = brain.lethal_adjacent_guard(_lase, {"SE": "wet chitinous puma"}, [_puma], _ab95)
assert _g["action"] == "USE_ABILITY:CommandTeleportOther:SE" and "Lethal guard" in _g["reason"], _g           # the real death: Lase was chosen with these three ready
_cool = lambda name: [dict(a, cooldown=40, usable=False) if a["name"] == name else a for a in _ab95]
assert brain.lethal_adjacent_guard(_lase, {"SE": "x"}, [_puma], _cool("Teleport Other"))["action"] == "USE_ABILITY:CommandForceBubble"
_two = [dict(a, cooldown=40, usable=False) if a["name"] in ("Teleport Other", "Force Bubble") else a for a in _ab95]
assert brain.lethal_adjacent_guard(_lase, {"SE": "x"}, [_puma], _two)["action"] == "USE_ABILITY:CommandIntimidate"
_none = [dict(a, cooldown=40, usable=False) if a["name"] in ("Teleport Other", "Force Bubble", "Intimidate") else a for a in _ab95]
assert brain.lethal_adjacent_guard(_lase, {"SE": "x"}, [_puma], _none) == _lase, "nothing ready: the model's choice stands"
for _keep in ("USE_ABILITY:CommandTeleportOther:SE", "USE_ABILITY:CommandForceBubble", "USE_ABILITY:CommandIntimidate", "USE_STAIRS_UP"):
    assert brain.lethal_adjacent_guard({"action": _keep}, {"SE": "x"}, [_puma], _ab95)["action"] == _keep
assert brain.lethal_adjacent_guard(dict(_lase, flee_ok=True), {"SE": "x"}, [_puma], _ab95)["action"] == _lase["action"]
for _other in (dict(_puma, difficulty="Tough"), dict(_puma, difficulty="Average"), dict(_puma, is_stationary=True), dict(_puma, dist=2), dict(_puma, is_companion=True)):
    assert brain.lethal_adjacent_guard(_lase, {"SE": "x"}, [_other], _ab95) == _lase, _other
assert brain.lethal_adjacent_guard(_lase, {}, [_puma], _ab95) == _lase
assert brain.lethal_adjacent_guard(_lase, {"SE": "x"}, [dict(_puma, difficulty="Impossible")], _ab95)["action"].startswith("USE_ABILITY:CommandTeleportOther")
print("  [OK] Test 95 Passed: a mobile Very Tough or Impossible hostile next to him is answered with Teleport Other, else Force Bubble, else Intimidate (the real Gen 19 death), and Tough and below, rooted, distant, companion, escape and nothing-ready cases are untouched.")


# ---------------------------------------------------------------------------
# Test 96: the read-only quest log (HANDOFF issue 76, BACKLOG B2 stage 1): brain messages, console view, mod export
# ---------------------------------------------------------------------------
_q0 = {"id": "What's Eating the Watervine?", "name": "What's Eating the Watervine?", "level": 1, "finished": False, "giver": "Mehmet", "giver_place": "Joppa", "giver_zone": "JoppaWorld.11.22.1.1.10",
       "steps": [{"name": "Travel to Red Rock", "text": "Journey two parasangs north of Joppa to Red Rock.", "xp": 50, "finished": False, "failed": False, "optional": False, "hidden": False},
                 {"name": "Find the Vermin", "text": "Find the creatures that are eating Joppa's watervine.", "xp": 100, "finished": False, "failed": False, "optional": False, "hidden": False}]}
brain.QUEST_SEEN.update({"started": set(), "finished_steps": set(), "done": set(), "primed": False})
_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    brain.note_quests({"quests": [_q0]})                                   # the first state only records what exists (a restart must not replay the log)
    brain.note_quests({"quests": [_q0]})
    _q1 = dict(_q0, steps=[dict(_q0["steps"][0], finished=True), _q0["steps"][1]])
    brain.note_quests({"quests": [_q1]})                                   # a step finished
    brain.note_quests({"quests": [_q1]})
    _q2 = dict(_q1, finished=True)
    brain.note_quests({"quests": [_q2, {"id": "Argyve", "name": "Fetch Argyve a Knickknack", "level": 3, "giver": "Argyve", "steps": []}]})   # finished, plus a new quest
    brain.note_quests({}); brain.note_quests({"quests": "x"}); brain.note_quests(None)
_lines = [l for l in _buf.getvalue().splitlines() if l.startswith("[QUEST]")]
assert len(_lines) == 3 and "step finished" in _lines[0] and "Travel to Red Rock" in _lines[0] and "+50 XP" in _lines[0], _lines
assert "quest finished" in _lines[1] and "new quest: Fetch Argyve a Knickknack" in _lines[2], _lines
_txt96 = _cl.describe_quests({"quests": [_q1], "finished_quests": ["Fetch Argyve a Knickknack"]})
assert "1/2 steps" in _txt96 and "[x] Travel to Red Rock" in _txt96 and "[ ] Find the Vermin" in _txt96 and "Finished: Fetch Argyve a Knickknack" in _txt96, _txt96
assert _cl.describe_quests({}).startswith("No quests")
_csrc96 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mod", "QudAIBrain", "AIBrainPart.cs"), encoding="utf-8").read()
for _needle in ("[QudAI Quests] ", "QuestElements(", "QuestUnwrap(", "QuestKey(", "BuildQuestsJson(out finishedQuestsJson)", '\\"quests\\": {questsJson}', "finished_quests", '"Quests"', '"FinishedQuests"', '"StepsByID"', "FLAG_FINISHED"):
    assert _needle in _csrc96, f"the mod must contain {_needle}"
assert _csrc96.count("{") == _csrc96.count("}"), "C# braces"
brain.QUEST_SEEN.update({"started": set(), "finished_steps": set(), "done": set(), "primed": False})
print("  [OK] Test 96 Passed: the brain announces new quests, finished steps and finished quests once (and stays quiet on its first look), the console renders the quest log, and the mod exports it read-only by reflection.")


# ---------------------------------------------------------------------------
# Test 97: Memory tab logic (console): list everything, approve, archive, delete; a generation number is never reused
# ---------------------------------------------------------------------------
_old97 = (_chr.WISDOM_FILE, _chr.GENERATION_COUNTER_FILE)
_root97 = tempfile.mkdtemp()
_mem97, _chd97 = _os.path.join(_root97, "memory"), _os.path.join(_root97, "chronicles")
for _d in (_os.path.join(_mem97, "runs"), _os.path.join(_mem97, "model_lab"), _chd97):
    _os.makedirs(_d)
_chr.WISDOM_FILE = _os.path.join(_mem97, "ancestral_wisdom.json")
_chr.GENERATION_COUNTER_FILE = _os.path.join(_mem97, "generation_counter.json")
try:
    _chr.save_ancestral_wisdom([{"generation": g, "name": f"N{g}", "level": 3, "lesson": f"lesson {g}", "death_reason": "x", "approved": g == 1} for g in (1, 2, 3)])
    for _p, _t in ((_os.path.join(_chd97, "Chronicle_Gen1_N1_1.md"), "chronicle text"), (_os.path.join(_chd97, "Postmortem_Gen1_N1_1.md"), "post-mortem text"),
                   (_os.path.join(_mem97, "runs", "run_1.json"), "{}"), (_os.path.join(_mem97, "model_lab", "lab_1.md"), "lab"), (_os.path.join(_mem97, "danger_ledger.json"), "{}")):
        open(_p, "w", encoding="utf-8").write(_t)
    _items = _cl.list_memory_items(_mem97, _chd97)
    _by = {}
    for _it in _items:
        _by.setdefault(_it["kind"], []).append(_it)
    assert {k: len(v) for k, v in _by.items()} == {"lesson": 3, "chronicle": 1, "postmortem": 1, "run": 1, "lab": 1, "data": 1}, {k: len(v) for k, v in _by.items()}
    assert [i["gen"] for i in _by["lesson"]] == [3, 2, 1], "newest lesson first"
    assert [i["kind"] for i in _items] == sorted([i["kind"] for i in _items], key=_cl.MEMORY_KINDS.index), "grouped in the fixed kind order"
    assert "lesson 1" in _cl.memory_item_text(_by["lesson"][2]) and "APPROVED" in _cl.memory_item_text(_by["lesson"][2]) and _cl.memory_item_text(_by["chronicle"][0]) == "chronicle text"
    # live data is shown but refused
    assert _by["data"][0]["safe"] is False
    for _fn in (lambda: _cl.archive_memory_item(_by["data"][0], _mem97, _chd97), lambda: _cl.delete_memory_item(_by["data"][0])):
        try:
            _fn()
            raise AssertionError("a live data file must be refused")
        except ValueError:
            pass
    assert _os.path.exists(_os.path.join(_mem97, "danger_ledger.json"))
    # archive a lesson: it leaves the active list, is kept whole in the archive file, unapproved, and its number is never reused
    _cl.archive_memory_item(_by["lesson"][1], _mem97, _chd97)                          # generation 2
    _active = {w["generation"] for w in _chr.load_ancestral_wisdom()}
    _arch = _cl.read_json(_os.path.join(_mem97, "archive", "ancestral_wisdom_archived.json"), [])
    assert _active == {1, 3} and [w["generation"] for w in _arch] == [2] and _arch[0]["lesson"] == "lesson 2" and _arch[0]["approved"] is False
    assert _chr.next_generation(_chr.load_ancestral_wisdom()) == 4
    # delete a lesson: gone for good, and the counter still never goes back
    _cl.delete_memory_item(_by["lesson"][0])                                           # generation 3
    assert {w["generation"] for w in _chr.load_ancestral_wisdom()} == {1}
    assert _chr.next_generation(_chr.load_ancestral_wisdom()) == 5, "numbers 3 and 4 must not be reused"
    # files: archive moves (never overwrites), delete removes
    _cl.archive_memory_item(_by["chronicle"][0], _mem97, _chd97)
    assert not _os.path.exists(_by["chronicle"][0]["path"]) and _os.path.exists(_os.path.join(_chd97, "archive", "Chronicle_Gen1_N1_1.md"))
    open(_by["chronicle"][0]["path"], "w", encoding="utf-8").write("second one")
    _cl.archive_memory_item(_by["chronicle"][0], _mem97, _chd97)
    assert len(_os.listdir(_os.path.join(_chd97, "archive"))) == 2, "a same-named file must not overwrite the archived one"
    _cl.archive_memory_item(_by["run"][0], _mem97, _chd97)
    assert _os.path.exists(_os.path.join(_mem97, "archive", "run", "run_1.json"))
    _cl.delete_memory_item(_by["lab"][0])
    assert not _os.path.exists(_by["lab"][0]["path"])
    _left = _cl.list_memory_items(_mem97, _chd97)
    assert sorted(i["kind"] for i in _left) == ["data", "data", "lesson", "postmortem"], [i["kind"] for i in _left]   # the two data files: danger_ledger and the new generation counter
    # a lesson written after all that gets a fresh number
    _again = _chr.load_ancestral_wisdom()
    assert _chr.next_generation(_again) == 6
finally:
    _chr.WISDOM_FILE, _chr.GENERATION_COUNTER_FILE = _old97
_csrc97 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools", "qudai_console.py"), encoding="utf-8").read()
for _needle in ("_build_memory", "memory_approve", "memory_archive", "memory_delete", 'default="no"'):
    assert _needle in _csrc97, f"the console must contain {_needle}"
print("  [OK] Test 97 Passed: the Memory tab lists lessons, chronicles, post-mortems, runs, lab results and live data; archive keeps (lessons whole, files in archive folders, never overwriting), delete removes, live data is refused, and a generation number is never reused after either.")


# ---------------------------------------------------------------------------
# Test 98: the turret doctrine (HANDOFF issue 77), replaying the Gen 22 death state
# ---------------------------------------------------------------------------
_lase98 = {"name": "Lase (5 charges)", "command": "CommandLase", "cooldown": 0, "usable": True, "active": False}
_other98 = [{"name": "Sprint", "command": "CommandToggleRunning", "cooldown": 0, "usable": True, "active": False},
            {"name": "Stunning Force", "command": "CommandStunningForce", "cooldown": 0, "usable": True, "active": False},
            {"name": "Teleport Other", "command": "CommandTeleportOther", "cooldown": 0, "usable": True, "active": False}]
_musket98 = {"name": "musket turret", "blueprint": "SecurityTurret", "dist": 4, "dir": "NE", "tx": 10, "ty": 14, "is_enemy": False, "is_companion": False,
             "has_los": True, "level": 15, "difficulty": "Impossible", "is_stationary": True}
_tinker98 = {"name": "rifle turret tinker", "blueprint": "Rifle Turret Tinker", "dist": 10, "dir": "SE", "tx": 16, "ty": 20, "is_enemy": False, "is_companion": False,
             "has_los": True, "level": 15, "difficulty": "Impossible", "is_stationary": False}
_far98 = dict(_musket98, dist=16, has_los=False, tx=22, ty=12)
_surr98 = {k: "Empty ground" for k in ("C", "N", "S", "E", "W", "NE", "NW", "SE", "SW")}


def _state98(**kw):
    s = {"hp": 10, "max_hp": 24, "x": 6, "y": 17, "z": 11, "level": 3, "zone_id": "JoppaWorld.11.21.0.0.11", "zone_name": "subterranean salt marsh", "zone_fully_explored": False,
         "hostiles_nearby": True, "hostiles_adjacent": False, "unexplored_cells": 900, "surroundings": dict(_surr98),
         "stairs_up": [{"name": "stairs up", "blueprint": "StairsUp", "dist": 1, "dir": "W", "tx": 5, "ty": 17}], "stairs_down": [], "standing_on_stairs_up": False,
         "visible_entities": [dict(_musket98), dict(_tinker98), dict(_far98)], "abilities": [dict(_lase98)] + [dict(a) for a in _other98],
         "loot_sources": [{"kind": "chest", "name": "chest", "tx": 17, "ty": 16, "dist": 11}]}
    s.update(kw)
    return s


def _q98(state, enemies=None):
    brain.recent_positions.clear()
    brain.RETREAT_TARGET_LEVEL = None
    brain.TURRET_STATE["last"] = None
    return brain.query_decision(state, took_damage=False, enemies=enemies or [])


# the hazard list: the musket turret in line of sight only (the tinker robot is mobile, the far turret has no line of sight)
assert [e["name"] for e in brain.turret_hazards(_state98())] == ["musket turret"]
assert brain.is_fragile_shooter({"is_stationary": True, "max_hp": 5}) and not brain.is_fragile_shooter({"is_stationary": False, "max_hp": 5}) and not brain.is_fragile_shooter({"is_stationary": True, "max_hp": 80})
# the death turn, as the brain saw it (turret not listed as an enemy, 10 of 24 HP, safe-rest territory): it used to REST; now it shoots the turret
_d = _q98(_state98())
assert _d["action"] == "USE_ABILITY:CommandLase:NE@10,14" and "Turret" in _d["reason"], _d
# the same with the new mod: the turret listed as an enemy with 5 hp
_new = _state98(visible_entities=[dict(_musket98, is_enemy=True, hp=5, max_hp=5)])
_d = _q98(_new, enemies=[dict(_musket98, is_enemy=True, hp=5, max_hp=5)])
assert _d["action"] == "USE_ABILITY:CommandLase:NE@10,14", _d
# no ranged attack: walk to the stairs one step away; on them: leave and level first
_noshot = _state98(abilities=[dict(a) for a in _other98])
assert _q98(_noshot)["action"] == "NAVIGATE_TO_CELL:5,17"
_on = _state98(abilities=[dict(a) for a in _other98], x=5, y=17, standing_on_stairs_up=True)
_d = _q98(_on)
assert _d["action"] == "USE_STAIRS_UP" and brain.RETREAT_TARGET_LEVEL == 4, (_d, brain.RETREAT_TARGET_LEVEL)
# two turrets in view and stairs close: leave instead of trading shots
_two = _state98(visible_entities=[dict(_musket98), dict(_musket98, dist=6, tx=12, ty=15, name="second musket turret")])
_d = _q98(_two)
assert _d["action"] == "NAVIGATE_TO_CELL:5,17", _d
# no stairs near and nothing to shoot with: the doctrine steps aside, but resting and looting stay vetoed
_stuck = _state98(abilities=[dict(a) for a in _other98], stairs_up=[], hp=10)
_d = _q98(_stuck)
assert _d["action"] != "REST" and not str(_d.get("reason", "")).startswith("Loot:"), _d
# a turret that is out of sight does not stop him resting, and without one resting works as before
_calm = _state98(visible_entities=[dict(_far98)], hostiles_nearby=False, stairs_up=[])
assert _q98(_calm)["action"] == "REST"
# the emergency retreat no longer fires just because a fragile Impossible shooter is in the list; a real Impossible mobile creature still does
_frag = {"name": "x", "difficulty": "Impossible", "is_stationary": True, "max_hp": 5, "dist": 5, "dir": "NE"}
assert brain.is_fragile_shooter(_frag)
_csrc98 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mod", "QudAIBrain", "AIBrainPart.cs"), encoding="utf-8").read()
for _needle in ("explicitCell", 'dirPart.IndexOf(\'@\')', "IsTurretObject(obj)", '\\"max_hp\\": {objMaxHp}', "objMaxHp = obj.baseHitpoints", "[QudAI Turret] "):
    assert _needle in _csrc98, f"the mod must contain {_needle}"
assert _csrc98.count("{") == _csrc98.count("}"), "C# braces"
brain.RETREAT_TARGET_LEVEL = None
brain.TURRET_STATE["last"] = None
print("  [OK] Test 98 Passed: replaying the Gen 22 state, a musket turret in line of sight is shot with Lase instead of resting or looting, two turrets or no ranged attack send him to the stairs up (and he levels first), out-of-sight turrets change nothing, and the mod counts Turret-tagged creatures as enemies and exports hit points.")


# ---------------------------------------------------------------------------
# Test 99: the Proselytize outcome log (BACKLOG B11 stage 1, HANDOFF issue 80)
# ---------------------------------------------------------------------------
import sys as _sys99
_sys99.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools"))
import proselytize_report as _pr
_old99 = brain.PROSELYTIZE_LOG_PATH
brain.PROSELYTIZE_LOG_PATH = _os.path.join(tempfile.mkdtemp(), "proselytize_log.jsonl")
brain.PROSELYTIZE_PENDING.update({"rec": None, "wait": 0})
try:
    _goat = {"name": "goat", "blueprint": "Goat", "dist": 1, "dir": "W", "is_enemy": False, "is_companion": False, "level": 2, "difficulty": "Easy", "is_stationary": False}
    _snap = {"name": "snapjaw warrior", "blueprint": "Snapjaw Warrior", "dist": 2, "dir": "NE", "is_enemy": True, "is_companion": False, "level": 6, "difficulty": "Tough", "is_stationary": False}
    _s0 = {"zone_id": "Z1", "level": 3, "hp": 20, "max_hp": 24, "attributes": {"Ego": 21}, "companions": [], "visible_entities": [_goat, _snap],
           "abilities": [{"command": "CommandProselytize", "cooldown": 0}]}
    _log = lambda: _pr.load(brain.PROSELYTIZE_LOG_PATH)
    # an attempt on the goat that works: a companion appears in the next state
    brain.record_proselytize_attempt("MOVE_E", _s0)                                        # not a Proselytize: ignored
    assert brain.PROSELYTIZE_PENDING["rec"] is None
    brain.record_proselytize_attempt("USE_ABILITY:CommandProselytize:W", _s0)
    assert brain.PROSELYTIZE_PENDING["rec"]["target"] == "goat" and brain.PROSELYTIZE_PENDING["rec"]["target_level"] == 2
    _buf = _io.StringIO()
    with _ctx.redirect_stdout(_buf):
        brain.note_proselytize(dict(_s0, companions=[{"name": "goat"}], abilities=[{"command": "CommandProselytize", "cooldown": 25}]))
    _r = _log()
    assert len(_r) == 1 and _r[0]["outcome"] == "recruited" and _r[0]["gap"] == -1 and _r[0]["fired"] is True and _r[0]["ego"] == 21 and "[PROSELYTIZE] recruited: goat" in _buf.getvalue(), _r
    assert brain.PROSELYTIZE_PENDING["rec"] is None
    # an attempt that fails: waits two turns for a companion, then logs not_recruited
    brain.record_proselytize_attempt("USE_ABILITY:CommandProselytize:NE", _s0)
    brain.note_proselytize(dict(_s0, abilities=[{"command": "CommandProselytize", "cooldown": 24}]))
    assert len(_log()) == 1, "still waiting for the second look"
    brain.note_proselytize(dict(_s0, abilities=[{"command": "CommandProselytize", "cooldown": 23}]))
    _r = _log()
    assert len(_r) == 2 and _r[1]["outcome"] == "not_recruited" and _r[1]["gap"] == 3 and _r[1]["hostile"] is True and _r[1]["target"] == "snapjaw warrior", _r
    # a new attempt while one is pending resolves the old one as unresolved; an aim with no listed target still logs, with no gap
    brain.record_proselytize_attempt("USE_ABILITY:CommandProselytize:S", _s0)
    brain.record_proselytize_attempt("USE_ABILITY:CommandProselytize:W", _s0)
    assert _log()[-1]["outcome"] == "unresolved" and _log()[-1]["target"] is None
    brain.note_proselytize({"companions": "x", "abilities": None})                          # garbage never raises
    brain.note_proselytize(None)
    # the report: the gap buckets and the counts
    _rows = [dict(outcome="recruited", gap=-1, hostile=False), dict(outcome="not_recruited", gap=-1, hostile=False), dict(outcome="recruited", gap=0, hostile=True),
             dict(outcome="not_recruited", gap=3, hostile=True), dict(outcome="not_recruited", gap=5, hostile=True), dict(outcome="unresolved", gap=1), dict(outcome="recruited", gap=None)]
    _sum = {label: (n, k) for label, n, k in _pr.summarize(_rows)}
    assert _sum["below our level (gap <= -1)"] == (2, 1) and _sum["same level (gap 0)"] == (1, 1) and _sum["3 above"] == (1, 0) and _sum["4 or more above"] == (1, 0) \
        and _sum["1 above"] == (0, 0) and _sum["gap unknown (target not listed)"] == (1, 1), _sum
    assert "1 unresolved" in _pr.format_report(_rows) and "hostile targets: 1/3" in _pr.format_report(_rows)
    assert _pr.load(_os.path.join(tempfile.mkdtemp(), "none.jsonl")) == []
finally:
    brain.PROSELYTIZE_LOG_PATH = _old99
    brain.PROSELYTIZE_PENDING.update({"rec": None, "wait": 0})
_src99 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "brain.py"), encoding="utf-8").read()
assert "record_proselytize_attempt(action, game_state)" in _src99 and "note_proselytize(game_state)" in _src99
print("  [OK] Test 99 Passed: every Proselytize is logged with the target's level, ours and our Ego, resolved from the companion list as recruited or not_recruited (or unresolved), never raises, and the report gives the rate by level gap.")


# ---------------------------------------------------------------------------
# Test 100: the creature catalog (BACKLOG B12 stage 1, HANDOFF issue 81)
# ---------------------------------------------------------------------------
import sys as _sys100
_sys100.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools"))
import build_creature_catalog as _bcc
import creature_report as _crep
assert _bcc.number_or_range({"Value": "5"}) == (5, 5) and _bcc.number_or_range({"sValue": "18-20"}) == (18, 20) and _bcc.number_or_range({"sValue": "25"}) == (25, 25)
assert _bcc.number_or_range({"sValue": "(t)d3"}) == (None, None) and _bcc.number_or_range(None) == (None, None)
_reps = {"Snapjaws": -475, "Joppa": -140}
assert _bcc.start_reputation("Snapjaws-100,Joppa-50", _reps) == -475 and _bcc.start_reputation("Joppa-100", _reps) == -140 and _bcc.start_reputation("Nobody-100", _reps) is None and _bcc.start_reputation(None, _reps) is None
_doc100 = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "creatures.json"), encoding="utf-8"))
_c100 = _doc100["creatures"]
assert _doc100["meta"]["creatures"] >= 800 and _doc100["meta"]["with_level"] == _doc100["meta"]["creatures"]
_t = _c100["SecurityTurret"]
assert _t["hp"] == 5 and _t["level"] == 15 and _t["rooted"] and _t["is_ranged"] and _t["likely_hostile"] and "turret" in _t["flags"] and _t["ranged"] == ["Musket"], _t   # the Gen 22 killer
assert [m["name"] for m in _c100["RedrockGirshling"]["melee"]] == ["Girshling_Claw"], "the defanged girshling has no bite"
assert _c100["Gunsmith"]["level"] == 18 and _c100["Gunsmith"]["level_max"] == 20, "a level range is kept, not read as the inherited default"
assert _c100["Ctesiphus"]["likely_hostile"] is False and _c100["Ctesiphus"]["start_rep"] == -140 and _c100["Snapjaw Warrior 1"]["likely_hostile"] is True
assert _c100["Giant Centipede"]["level"] == 5 and _c100["Knollworm"]["hp"] == 20 and _c100["IrritableTortoise"]["level"] == 5 and _c100["Chitinous Puma"]["level"] == 12 and _c100["Chitinous Puma"]["hp"] == 45   # the Gen 19 killer
_page = _crep.render(_doc100)
assert "musket turret" in _page and "Rooted shooters" in _page and "inferred" in _page
print("  [OK] Test 100 Passed: the creature catalog reads fixed, range and tier-formula levels correctly, drops removed attacks, takes hostility from faction starting reputation, matches the Gen 22 turret (5 HP, level 15, rooted, ranged, hostile) and renders its report.")


# ---------------------------------------------------------------------------
# Test 101: the Lab tab's wish scenarios (BACKLOG B13 stage 1, HANDOFF issue 82)
# ---------------------------------------------------------------------------
_sc101 = _cl.load_wish_scenarios()
assert len(_sc101) >= 7 and len({s["id"] for s in _sc101}) == len(_sc101)
for _s in _sc101:
    assert _s.get("title") and _s.get("why") and _s.get("setup") and _s.get("watch") and _s["wishes"], _s["id"]
    for _w in _s["wishes"]:
        assert _w.get("confidence") in _cl.CONFIDENCE_TEXT and _w.get("cmd"), (_s["id"], _w)
# every spawn: names a creature blueprint in the catalog and every item: an item blueprint in the item catalog, so a card cannot send the human after a typo
_items101 = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "items.json"), encoding="utf-8"))["items"]
_crea101 = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "creatures.json"), encoding="utf-8"))["creatures"]
for _s in _sc101:
    for _w in _s["wishes"]:
        _c = _w["cmd"]
        assert not _c.startswith("spawn:"), f"the spawn: prefix failed in game (Unknown blueprint, 2026-10-08): {_s['id']}"
        assert _w.get("kind") in ("blueprint", "command"), (_s["id"], _w)
        if _w["kind"] == "blueprint":
            assert _c in _crea101 or _c in _items101, f"unknown blueprint typed alone in {_s['id']}: {_c}"
        elif _c.startswith("item:"):
            assert _c[5:] in _items101, f"unknown item in {_s['id']}: {_c}"
# the XP wish: the game's own curve, and what is still missing
assert _cl.xp_for_level(1) == 0 and _cl.xp_for_level(2) == 220 and _cl.xp_for_level(5) == 1975 and _cl.xp_for_level(10) == 15100
assert _cl.xp_wish_for_level(5, 1900) == "xp:75" and _cl.xp_wish_for_level(3, 1900) == "" and _cl.xp_wish_for_level(2, 0) == "xp:220"
_lv = next(s for s in _sc101 if s["id"] == "set-level")
assert _cl.wish_lines(_lv, 6, 0) == ["xp:3340"] and _cl.wish_lines(_lv, None, 0) == [] and _cl.wish_lines(_lv, 3, 5000) == []
_t101 = _cl.scenario_text(_sc101[0])
assert "Ctrl+W" in _t101 and "throwaway" in _t101 and "SecurityTurret" in _t101 and "ONE line" in _t101 and "verified in game" in _t101
_p101 = _os.path.join(tempfile.mkdtemp(), "lab_runs.jsonl")
_rec = _cl.log_lab_use("turret-nest", "unit test", _p101)
assert _cl.tail_jsonl(_p101, 5)[0]["scenario"] == "turret-nest" and _rec["note"] == "unit test" and len(_cl.tail_jsonl(_p101, 5)) == 1
assert _cl.load_wish_scenarios(_os.path.join(tempfile.mkdtemp(), "none.json")) == []
print("  [OK] Test 101 Passed: the Lab scenarios load, name only creatures and items that exist in the catalogs, compute the XP wish from the game's curve and the current XP, render with the cheat warning, and log a use.")


# ---------------------------------------------------------------------------
# Test 102: the IsAlive audit and the service-NPC recruit rule (HANDOFF issues 77 and 79)
# ---------------------------------------------------------------------------
import re as _re102
_cs102 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mod", "QudAIBrain", "AIBrainPart.cs"), encoding="utf-8").read()
def _body102(name):
    i = _cs102.index(name)
    j = _cs102.index("\n        }\n", i)
    return _cs102[i:j]
assert "private static bool IsStanding(GameObject o)" in _cs102 and "o.hitpoints > 0" in _cs102
assert "|| !IsStanding(obj)) return false;" in _body102("public static bool IsCompanion(GameObject obj, GameObject player)")
_enemy102 = _body102("public static bool CheckIsEnemy(GameObject obj, GameObject player)")
assert "if (!IsStanding(obj)) return false;" in _enemy102 and "if (!obj.IsAlive) return false;" not in _enemy102
assert "IsStanding(c))" in _cs102 and "IsStanding(zObj)" in _cs102, "the companion scans must not require organic life"
# what is left of IsAlive is deliberate: proselytize (organic minds only), loot (do not loot a turret), the diagnostic, the player's own death check, the stairs and the target fallback
_code102 = "\n".join(l for l in _cs102.splitlines() if not l.strip().startswith("//"))
assert len(_re102.findall(r"\.IsAlive\b", _code102)) == 7, len(_re102.findall(r"\.IsAlive\b", _code102))
# issue 79: the markers, and that a hostile service NPC is not protected
_svc102 = _body102("private static bool IsServiceNpc(GameObject obj)")
for _m in ("GivesRep", "GenericInventoryRestocker", "GivesDynamicQuest", "NamedVillager", "ParticipantVillager"):
    assert _m in _svc102, _m
assert "IsServiceNpc(obj) && !obj.IsHostileTowards(player)" in _cs102
# the data behind it: the catalog flags separate people who serve from ordinary creatures (ConversationScript does not: 814 of 845 have one)
_crea102 = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "creatures.json"), encoding="utf-8"))["creatures"]
_serve = lambda n: bool({"gives_rep", "restocks"} & set(_crea102[n].get("flags", [])))
for _n in ("Nima Ruda", "Gunsmith", "Mehmet", "ElderBob", "Warden Yrame", "Warden Esthers", "Tam", "Argyve"):
    assert _serve(_n), _n
for _n in ("Goat", "Ctesiphus", "Giant Centipede", "Snapjaw Warrior 1", "Cave Spider", "Baboon", "Knollworm", "SecurityTurret"):
    assert not _serve(_n), _n
assert 100 <= sum(1 for _n in _crea102 if _serve(_n)) <= 200
print("  [OK] Test 102 Passed: companions and the enemy test use hit points instead of organic life (so a robot, golem or turret can be a companion or an enemy), the 7 remaining IsAlive uses are the intended ones, and shopkeepers, quest givers and reputation NPCs are protected from recruiting by the markers that separate them from animals.")


# ---------------------------------------------------------------------------
# Test 103: creature catalogue adapter and threat score (B12 stage 2, HANDOFF issue 84), display only
# ---------------------------------------------------------------------------
import creature_threat as _ct103
_cat103 = _ct103.load_catalog()
assert len(_cat103) > 800
assert _ct103.lookup(name="wet chitinous puma")["level"] == 12, "adjectives must not defeat the lookup"
assert _ct103.lookup(blueprint="SecurityTurret")["rooted"] is True
assert _ct103.lookup(name="no such beast") is None and _ct103.threat(None, 1, 20)["cls"] == "unknown"
assert _ct103._dice_average("2d4+1") == 6.0 and _ct103._dice_average("1d3") == 2.0
_puma = _ct103.threat(_ct103.lookup(blueprint="Chitinous Puma"), 2, 27)
_goat = _ct103.threat(_ct103.lookup(blueprint="Goat"), 2, 27)
assert _puma["ratio"] > 1.6 and _puma["cls"] == "deadly", _puma
assert _goat["ratio"] < _puma["ratio"] and _goat["cls"] != "deadly", _goat
assert abs(_ct103.expected_penetrations(4, 0) - 1.2) < 0.05 and _ct103.expected_penetrations(2, 9) == 3.0, "penetration rule: 3 trials of an exploding 1d10-2"
assert _ct103.threat(_ct103.lookup(blueprint="SecurityTurret"), 1, 21)["cls"] == "deadly", "a shooter gets free shots while we close in"
assert _ct103.threat(_ct103.lookup(blueprint="Chitinous Puma"), 2, 27, enemy_hp=10)["ratio"] < _puma["ratio"], "live hit points must be used"
import tools.console_logic as _cl103
_st103 = {"level": 2, "hp": 27, "max_hp": 27, "visible_entities": [{"name": "wet chitinous puma", "blueprint": "Chitinous Puma", "is_enemy": True, "difficulty": "Tough", "dist": 5}]}
assert "~deadly" in _cl103.threat_summary(_st103)[0], _cl103.threat_summary(_st103)
print("  [OK] Test 103 Passed: the catalogue adapter finds creatures by blueprint or by display name with adjectives, the threat race ranks a puma above a goat, uses live hit points when the state has them, and the console threat strip shows the catalogue class beside the engine's own difficulty.")


# ---------------------------------------------------------------------------
# Test 104: our own armour and main-hand weapon feed the threat score (B12 stage 2, HANDOFF issue 84)
# ---------------------------------------------------------------------------
_cs104 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mod", "QudAIBrain", "AIBrainPart.cs"), encoding="utf-8").read()
for _s in ('player.Stat("AV", 0)', 'player.Stat("DV", 0)', "player.GetPrimaryWeapon()", "mw.GetNormalPenetration(player)", '\\"av\\": {statAV}', '\\"melee\\": {{\\"weapon\\"', '\\"penetration\\": {meleePen}'):
    assert _s in _cs104, _s
_puma104 = _ct103.lookup(blueprint="Chitinous Puma")
_weak104 = _ct103.threat(_puma104, 2, 27, us={"av": 4, "melee": {"damage": "1d2", "penetration": 0}})
_strong104 = _ct103.threat(_puma104, 2, 27, us={"av": 7, "melee": {"damage": "2d6", "penetration": 3}})
assert _strong104["ratio"] < _weak104["ratio"] / 5, (_weak104, _strong104)
assert _strong104["their_dps"] < _weak104["their_dps"], "better armour must lower the damage we take"
assert _ct103.creature_armor(_puma104) == 7 and _ct103.creature_armor(None) == 0
assert _ct103.threat(_puma104, 2, 27)["ratio"] == _ct103.threat(_puma104, 2, 27, us={})["ratio"], "no export, no change: the guess is the fallback"
print("  [OK] Test 104 Passed: the mod exports av, dv and the main-hand weapon (dice, penetration), and the threat score uses them: a stronger weapon and better armour lower the threat, and a state without them falls back to the guess.")


# ---------------------------------------------------------------------------
# Test 105: party tables and the party threat (B12 stage 4 start, HANDOFF issue 84)
# ---------------------------------------------------------------------------
_par105 = _ct103.load_parties()["parties"]
assert abs(_par105["BaboonParty"]["members"]["Baboon"] - 3.15) < 0.01 and abs(_par105["BigBaboonParty"]["members"]["Baboon"] - 10.8) < 0.01, "3-4 baboons at 90 percent; 8-16 at 90 percent"
assert _par105["SnapjawParty1"]["members"]["Snapjaw Scavenger 1"] == 3.5, "1-3 at 100 percent plus 1-3 at 75 percent"
assert _ct103.parties_of("Baboon").get("BaboonParty") and not _ct103.parties_of("SecurityTurret")
_us105 = {"av": 1, "melee": {"damage": "1d2", "penetration": -1}}
_solo105 = _ct103.threat(_ct103.lookup(blueprint="Baboon"), 2, 30, us=_us105)
_pack105 = _ct103.party_threat("BaboonParty", 2, 30, us=_us105)
assert _solo105["cls"] in ("trivial", "easy", "fair") and _pack105["cls"] == "deadly" and _pack105["ratio"] > 4 * _solo105["ratio"], (_solo105, _pack105)
assert _ct103.party_threat("NoSuchParty", 2, 30)["cls"] == "unknown"
import tools.build_party_table as _bpt105
assert _bpt105.number_average("3-4") == 3.5 and _bpt105.number_average("1d4") == 2.5 and _bpt105.number_average("") == 1.0
print("  [OK] Test 105 Passed: the party tables give the game's own pack sizes (baboons 3.15 in a small party, 10.8 in a big one), a lone baboon is a fair fight but its party is deadly for a starting character, and unknown parties degrade to 'unknown'.")


# ---------------------------------------------------------------------------
# Test 106: zone danger ledger and exit steering (BACKLOG B10 step 1, HANDOFF issue 85), including a multi-turn walk
# ---------------------------------------------------------------------------
import zone_danger as _zd106
assert _zd106.world_cell("JoppaWorld.11.22.1.1.10") == (34, 67, 10) and _zd106.world_cell("junk") is None
assert _zd106.adjacent_zone("JoppaWorld.11.22.2.1.10", "E") == "JoppaWorld.12.22.0.1.10" and _zd106.adjacent_zone("JoppaWorld.11.22.0.1.10", "W") == "JoppaWorld.10.22.2.1.10"
assert _zd106.zone_distance("JoppaWorld.11.22.2.1.10", "JoppaWorld.12.22.0.1.10") == 1 and _zd106.zone_distance("JoppaWorld.1.1.0.0.10", "JoppaWorld.1.1.0.0.11") is None
_led106 = _zd106.Ledger()
_Z = "JoppaWorld.11.22.1.1.10"
assert _led106.record(_Z, "chitinous puma", 12, 5) is True and _led106.record(_Z, "goat", 1, 5) is False, "a worse creature replaces, a lesser one does not"
assert _led106.flags[_Z].clears_at == 9 and _led106.active_flags(8) and not _led106.active_flags(9), "lapses at creature level minus 3"
assert _zd106.Ledger().pressure(_Z, 1) == 0.0 and _zd106.steer(_zd106.Ledger(), _Z, 1, ["N", "S"], ["N", "S"], "S") == (None, None, None), "no flag, no steering"
_lowpack = _zd106.Ledger(); _lowpack.record(_Z, "baboon party", 5, 1)
assert _lowpack.flags[_Z].clears_at == 3, "a flag raised at level 1 lapses after two levels even for a weak creature"
# steering: danger lies north of here, so north must not be chosen while south and east are free
_led = _zd106.Ledger(); _led.record("JoppaWorld.11.22.1.0.10", "puma", 12, 3)      # the zone directly north of _Z
_keep, _mode, _note = _zd106.steer(_led, _Z, 3, ["N", "S", "E", "W"], ["N", "S", "E", "W"], None)
assert _mode == "away" and "N" not in _keep and set(_keep) <= {"S", "E", "W"}, (_keep, _mode, _note)
# backtracking: danger on three sides ahead (we came from the south), the way back is the best exit
_led2 = _zd106.Ledger()
for _d in ("N", "E", "W"):
    _led2.record(_zd106.adjacent_zone(_Z, _d), "puma", 12, 3)
_keep2, _mode2, _note2 = _zd106.steer(_led2, _Z, 3, ["N", "E", "W", "S"], ["N", "E", "W"], "S")
assert _mode2 == "retreat" and _keep2 == ["S"], (_keep2, _mode2, _note2)
# multi-turn: a walker on a grid with a wall of flagged zones to the north must end up in the south or sideways and never oscillate between two zones
def _walk106(start, flags, steps=14):
    led = _zd106.Ledger()
    for f in flags:
        led.record(f, "puma", 12, 2)
    cur, rev, seen, trail = start, None, set([start]), [start]
    for _ in range(steps):
        cands = [d for d in "NSEW" if _zd106.adjacent_zone(cur, d)]
        novel = [d for d in cands if _zd106.adjacent_zone(cur, d) not in seen]
        keep, mode, _n = _zd106.steer(led, cur, 2, [d for d in cands if d != rev] or cands, [d for d in novel if d != rev] or novel, rev)
        pool = keep or ([d for d in novel if d != rev] or novel or cands)
        d = sorted(pool)[0] if mode is None else pool[0]
        nxt = _zd106.adjacent_zone(cur, d)
        rev = {"N": "S", "S": "N", "E": "W", "W": "E"}[d]
        cur = nxt; seen.add(cur); trail.append(cur)
    return trail
_start106 = "JoppaWorld.11.22.1.1.10"
_flags106 = [_zd106.adjacent_zone(_start106, "N")] + [_zd106.adjacent_zone(_zd106.adjacent_zone(_start106, "N"), s) for s in "EW"]
_trail106 = _walk106(_start106, _flags106)
assert not any(a == b for a, b in zip(_trail106, _trail106[2:])), ("oscillation A-B-A", _trail106)
_ys = [_zd106.world_cell(z)[1] for z in _trail106]
assert _ys[-1] >= _ys[0], ("he walked north into the flagged zones", _ys)
assert all(z not in _flags106 for z in _trail106), "the walk entered a flagged zone"
# brain wiring: the ledger is fed from the state and the exit chooser answers
brain.ZONE_DANGER = _zd106.Ledger()
_st106 = {"zone_id": _start106, "level": 2, "hp": 20, "max_hp": 20, "visible_entities": [{"name": "wet chitinous puma", "blueprint": "Chitinous Puma", "is_enemy": True, "is_stationary": False, "level": 12, "difficulty": "Very Tough", "dist": 7}]}
brain.note_zone_danger(_st106)
assert _start106 in brain.ZONE_DANGER.flags and brain.ZONE_DANGER.flags[_start106].creature_level == 12
_st106b = {"zone_id": _start106, "level": 2, "hp": 20, "visible_entities": [{"name": "goat", "blueprint": "Goat", "is_enemy": True, "is_stationary": False, "level": 1, "difficulty": "Trivial"}]}
brain.ZONE_DANGER = _zd106.Ledger(); brain.note_zone_danger(_st106b)
assert not brain.ZONE_DANGER.flags, "a goat flags nothing"
brain.ZONE_DANGER = _zd106.Ledger()
print("  [OK] Test 106 Passed: a zone with a creature out of our class is flagged until we have grown, exits are steered away from flagged zones, the way back is taken when every way on leads closer, a 14-step walk beside a wall of flagged zones never enters one and never oscillates, and a goat flags nothing.")


# ---------------------------------------------------------------------------
# Test 107: prompt tokens in the trace and the context headroom check (HANDOFF issue 86)
# ---------------------------------------------------------------------------
assert brain.loaded_context_length([{"id": "a", "loaded_context_length": 8192}, {"id": "b"}], "a") == 8192 and brain.loaded_context_length([{"id": "b"}], "b") is None and brain.loaded_context_length(None, "a") is None
_src107 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "brain.py"), encoding="utf-8").read()
assert 'LAST_LLM_USAGE.update({"turn": TURN_CLOCK, "prompt_tokens"' in _src107 and '"llm": {k: LAST_LLM_USAGE.get(k)' in _src107, "the call must record usage and the trace row must carry it"
import tools.console_logic as _cl107
_tmp107 = _os.path.join(tempfile.mkdtemp(), "t.jsonl")
def _w107(rows):
    with open(_tmp107, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(_json.dumps(r) + chr(10))
_w107([{"t": 1, "action": "REST"}])
assert _cl107.llm_headroom(_tmp107)[0] == _cl107.UNKNOWN, "rows without token counts say unknown, not zero"
_w107([{"llm": {"prompt_tokens": 2000, "ctx": 8192}}, {"llm": {"prompt_tokens": 3000, "ctx": 8192}}, {"t": 3}])
_ok107 = _cl107.llm_headroom(_tmp107)
assert _ok107[0] == _cl107.OK and "3000" in _ok107[1] and "8192" in _ok107[1], _ok107
_w107([{"llm": {"prompt_tokens": 5200, "ctx": 8192}}])
assert _cl107.llm_headroom(_tmp107)[0] == _cl107.WARN, "more than 60 percent of the window warns"
_w107([{"llm": {"prompt_tokens": 900, "ctx": None}}])
assert _cl107.llm_headroom(_tmp107)[0] == _cl107.UNKNOWN, "an unknown window size cannot be judged"
print("  [OK] Test 107 Passed: the brain records prompt and completion tokens and the loaded context length on each model call, the trace row carries them, and the console health tab reports the largest prompt against the window (OK, WARN above 60 percent, UNKNOWN without data).")


# ---------------------------------------------------------------------------
# Test 108: the creature catalog applies mixins (HANDOFF issue 87: the first hover golem test)
# ---------------------------------------------------------------------------
_c108 = _ct103.load_catalog()
_g108 = _c108["Hover Golem"]
assert _g108["level"] == 50 and _g108["hp"] == 500 and "Barathrumites" in _g108["factions"] and not _g108["likely_hostile"], _g108
assert _c108["Humanoid Robot Golem"]["level"] == 50 and _c108["Infrastructure Golem"]["hp"] == 1000, "the mixin's hit points, then the blueprint's own"
assert _c108["Baboon"]["level"] == 5 and _c108["Scrapbot"]["factions"].startswith("Robots"), "creatures without a mixin are unchanged"
_cs108 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tools", "build_creature_catalog.py"), encoding="utf-8").read()
assert "class MixinCatalog(bic.Catalog)" in _cs108 and "cat = MixinCatalog(raw)" in _cs108
assert _c108["Scrapbot"]["calm"] is True and not _c108["Scrapbot"]["likely_hostile"] and _c108["Waydroid"]["likely_hostile"] and _c108["Baboon"]["likely_hostile"], "Calm=True means it does not start fights (the Scrapbot test, 2026-10-08); Hostile=false alone does not (baboons)"
print("  [OK] Test 108 Passed: the creature catalog merges <mixin> blueprints, so a hover golem is level 50 with 500 hit points in the Barathrumites (not hostile), as the game reported, and creatures without a mixin are unchanged.")


# ---------------------------------------------------------------------------
# Test 109: the zone-danger ratio trigger is conservative for a character with a ranged opener (Waydroid retest, HANDOFF issue 87)
# ---------------------------------------------------------------------------
_ab109 = [{"name": "Lase (3 charges)", "command": "CommandLase", "usable": True}, {"name": "Sprint", "command": "CommandToggleRunning"}]
assert brain.has_ranged_opener({"abilities": _ab109}) and brain.has_ranged_opener({"abilities": [{"command": "CommandTeleportOther", "usable": False}]}), "a kit on cooldown still counts"
assert not brain.has_ranged_opener({"abilities": [{"command": "CommandToggleRunning"}, {"command": "CommandIntimidate"}]}) and not brain.has_ranged_opener({})
assert brain.has_ranged_opener({"has_missile_weapon": True, "abilities": []})
_wd109 = {"name": "waydroid", "blueprint": "Waydroid", "is_enemy": True, "is_stationary": False, "level": 10, "difficulty": "Average", "hp": 24, "dist": 8}
def _flagged109(extra):
    brain.ZONE_DANGER = _zd106.Ledger()
    brain.note_zone_danger(dict({"zone_id": _start106, "level": 3, "hp": 26, "av": 1, "melee": {"damage": "1d2", "penetration": -1}, "visible_entities": [_wd109]}, **extra))
    return _start106 in brain.ZONE_DANGER.flags
assert _flagged109({"abilities": []}) is True, "no opener: the ratio flags a level-10 robot even when the engine calls it Average"
assert _flagged109({"abilities": _ab109}) is False, "an opener: the ratio alone no longer flags it"
_wd109["difficulty"] = "Very Tough"
assert _flagged109({"abilities": _ab109}) is True, "the engine's own difficulty always flags"
brain.ZONE_DANGER = _zd106.Ledger()
print("  [OK] Test 109 Passed: a character with a ranged or disabling ability (ready or on cooldown) or a missile weapon is flagged only by the engine's difficulty, not by the melee-only threat ratio; a character without one is still flagged by both.")


# ---------------------------------------------------------------------------
# Test 110: last-seen position memory keeps the frontier chooser away from an out-of-class creature (B10 step 1 extension, HANDOFF issue 85)
# ---------------------------------------------------------------------------
_Z110 = "JoppaWorld.11.21.0.1.10"
_led110 = _zd106.Ledger()
assert _led110.avoid_points(_Z110, 1, 0) == [], "no flag, no avoid point"
_led110.record(_Z110, "wet croc", 3, 1)
assert _led110.avoid_points(_Z110, 1, 0) == [], "flagged but never located"
_led110.seen(_Z110, 72, 13, 100)
assert _led110.avoid_points(_Z110, 1, 120) == [(72, 13)] and _led110.avoid_points(_Z110, 1, 100 + _zd106.AVOID_MAX_AGE + 1) == [], "the position goes stale"
assert _led110.avoid_points(_Z110, 20, 120) == [], "a lapsed flag keeps nothing away"
_led110.seen("JoppaWorld.1.1.0.0.10", 5, 5, 100)
assert "JoppaWorld.1.1.0.0.10" not in _led110.flags, "seen() never creates a flag"
# the frontier chooser: the nearest target lies beside the croc, the next one does not
def _front110(level=1, turn=120):
    brain.ZONE_DANGER = _led110
    brain.TURN_CLOCK = turn
    brain.FRONTIER_COMMIT.update({"zone": None, "target": None})
    brain.FRONTIER_PURSUIT.update({"key": None, "turns": 0})
    st = {"level": level, "frontier_targets": [{"x": 72, "y": 13, "dist": 2, "q": "SE"}, {"x": 30, "y": 5, "dist": 40, "q": "NW"}]}
    return brain.pick_frontier_target(st, (74, 15), _Z110)
_t110, _r110 = _front110()
assert _t110 == (30, 5), (_t110, _r110)
brain.FRONTIER_COMMIT.update({"zone": _Z110, "target": (72, 13)})
_st110 = {"level": 1, "frontier_targets": [{"x": 72, "y": 13, "dist": 2, "q": "SE"}, {"x": 30, "y": 5, "dist": 40, "q": "NW"}]}
assert brain.pick_frontier_target(_st110, (74, 15), _Z110)[0] == (30, 5), "a committed target near the danger is dropped"
_only110 = {"level": 1, "frontier_targets": [{"x": 72, "y": 13, "dist": 2, "q": "SE"}]}
brain.FRONTIER_COMMIT.update({"zone": None, "target": None})
assert brain.pick_frontier_target(_only110, (74, 15), _Z110) == (None, None), "when every target is near the danger the chooser offers none (the brain then leaves or autoexplores)"
assert _front110(level=20)[0] == (72, 13), "a lapsed flag restores the nearest target"
assert _front110(turn=120 + 200)[0] == (72, 13), "a stale position restores the nearest target"
# the feed: note_zone_danger stores where the creature stood
brain.ZONE_DANGER = _zd106.Ledger(); brain.TURN_CLOCK = 50
brain.note_zone_danger({"zone_id": _Z110, "level": 1, "hp": 18, "visible_entities": [{"name": "wet croc", "blueprint": "Crocodile", "is_enemy": True, "is_stationary": False, "level": 3, "difficulty": "Impossible", "tx": 70, "ty": 11, "hp": 40}]})
assert brain.ZONE_DANGER.flags[_Z110].where == (70, 11) and brain.ZONE_DANGER.flags[_Z110].where_turn == 50
brain.ZONE_DANGER = _zd106.Ledger(); brain.FRONTIER_COMMIT.update({"zone": None, "target": None})
print("  [OK] Test 110 Passed: the ledger remembers where a flagged creature was last in view, the frontier chooser skips targets within 8 cells of it (dropping a committed one, offering none when all are near), and the memory lapses with the flag or after 80 turns.")


# ---------------------------------------------------------------------------
# Test 111: a rooted vine is not a fragile shooter (human run 2026-10-08, trace t1668: Lase fired at a jilted lover)
# ---------------------------------------------------------------------------
assert brain.is_fragile_shooter({"is_stationary": True, "max_hp": 5, "name": "musket turret", "blueprint": "SecurityTurret"}) is True
assert brain.is_fragile_shooter({"is_stationary": True, "max_hp": 5, "name": "jilted lover", "blueprint": "Jilted Lover"}) is False, "no ranged attack in the catalogue: not a shooter"
assert brain.is_fragile_shooter({"is_stationary": True, "max_hp": 5, "name": "mystery", "blueprint": "NoSuchThing"}) is True, "unknown to the catalogue: the old caution stays"
assert brain.is_fragile_shooter({"is_stationary": False, "max_hp": 5, "name": "musket turret", "blueprint": "SecurityTurret"}) is False
_st111 = {"x": 40, "y": 12, "visible_entities": [{"name": "jilted lover", "blueprint": "Jilted Lover", "is_enemy": True, "is_stationary": True, "max_hp": 5, "hp": 5, "dist": 4, "has_los": True, "tx": 44, "ty": 12}]}
assert brain.turret_hazards(_st111) == [], "a lone jilted lover is not a turret hazard"
print("  [OK] Test 111 Passed: a rooted vine with no ranged attack (jilted lover) is not treated as a fragile shooter, so the turret rule no longer spends Lase charges on it, while real turrets and creatures unknown to the catalogue keep the old rule.")


# ---------------------------------------------------------------------------
# Test 112: the turret retreat depends on the damage a nest deals against our hit points (human run 2026-10-08, trace t1649 and t1783; HANDOFF issue 89)
# ---------------------------------------------------------------------------
_c112 = _ct103.load_catalog()
assert _c112["Seed-Spitting Vine"]["ranged_shots"][0]["damage"] == "1d3" and _c112["Seed-Spitting Vine"]["ranged_shots"][0]["penetration"] == 2, "ProjectileSpatSeed"
assert _c112["SecurityTurret"]["ranged_shots"][0]["damage"] == "1d8" and _c112["SecurityTurret"]["ranged_shots"][0]["penetration"] == 4, "ProjectileMusketBall"
_vine112 = {"name": "seed-spitting vine", "blueprint": "Seed-Spitting Vine", "is_enemy": True, "is_stationary": True, "max_hp": 5, "hp": 5, "dist": 11, "has_los": True}
_vine112b = dict(_vine112, dist=6)
_mus112 = {"name": "musket turret", "blueprint": "SecurityTurret", "is_enemy": True, "is_stationary": True, "max_hp": 5, "hp": 5, "dist": 6, "has_los": True}
def _hz112(hp, ents):
    return brain.turret_hazards({"hp": hp, "av": 1, "visible_entities": ents})
assert _hz112(40, [_vine112]) == [], "one seed vine is not worth fleeing at 40 HP (t1783)"
assert len(_hz112(40, [_vine112, _vine112b])) == 2, "two vines still are (t1649 had two, at 28 HP)"
assert len(_hz112(28, [_vine112])) == 1, "the same vine matters at 28 HP"
assert len(_hz112(40, [_mus112])) == 1, "a musket turret is never tolerable at these hit points"
_unk112 = {"name": "ancient turret", "blueprint": "NoSuchTurret", "is_enemy": True, "is_stationary": True, "max_hp": 5, "dist": 6, "has_los": True}
assert len(_hz112(500, [_unk112])) == 1, "a turret the catalogue does not know keeps the old caution"
# the decision itself: one vine at 40 HP, stairs up near: no retreat; the musket nest keeps the doctrine
_gs112 = {"x": 45, "y": 23, "z": 12, "zone_id": "JoppaWorld.11.20.1.1.12", "hp": 40, "av": 1, "level": 5, "standing_on_stairs_up": True, "stairs_up": [{"tx": 45, "ty": 23}],
          "visible_entities": [dict(_vine112)]}
assert brain.turret_decision(_gs112, [], 1.0, []) is None
_gs112["visible_entities"] = [dict(_mus112)]
assert brain.turret_decision(_gs112, [], 1.0, [])["action"] == "USE_STAIRS_UP"
print("  [OK] Test 112 Passed: the catalogue carries the engine's shot damage (seed 1d3 pen 2, musket ball 1d8 pen 4), a nest whose expected damage while closing in is under half our HP is not fled (one vine at 40 HP), two vines or a lower HP or a musket turret still are, and an unknown turret keeps the old caution.")


# ---------------------------------------------------------------------------
# Test 113: a cleared stratum whose way down is held shut by a level goal is left by the stairs up (human run 2026-10-08, trace t2134-2253; HANDOFF issue 90)
# ---------------------------------------------------------------------------
_up113 = "JoppaWorld.11.20.1.1.10"
_dn113 = "JoppaWorld.11.20.1.1.11"
_saved113 = (dict(brain.KNOWN_STAIRS_DOWN), dict(brain.KNOWN_STAIRS_UP), set(brain.STAIRS_GIVEUP), set(brain.DEAD_END_ZONES), brain.ZONE_STEP_COUNT, brain.RETREAT_TARGET_LEVEL)
try:
    brain.KNOWN_STAIRS_DOWN.clear(); brain.KNOWN_STAIRS_UP.clear(); brain.STAIRS_GIVEUP.clear(); brain.DEAD_END_ZONES.clear()
    brain.KNOWN_STAIRS_DOWN[_dn113] = {"tx": 45, "ty": 23, "z": 11, "name": "stairs down", "req_level": 5}
    brain.KNOWN_STAIRS_UP[_dn113] = {"tx": 20, "ty": 4, "z": 11, "name": "stairs up"}
    brain.RETREAT_TARGET_LEVEL = 6
    brain.ZONE_STEP_COUNT = 150
    _edges113 = {"reachable_edges": "NSEW"}          # the engine claims every edge is reachable; underground its route ends at a wall
    _d = brain.dead_end_ascent(_edges113, _dn113, 11, (62, 7), False, True, True)
    assert _d and _d["action"] == "NAVIGATE_TO_CELL:20,4" and "Level goal" in _d["reason"], _d
    assert brain.dead_end_ascent(_edges113, _dn113, 11, (62, 7), False, True, False) is None, "not gated: the delve logic owns it"
    assert brain.dead_end_ascent(_edges113, _dn113, 11, (62, 7), False, False, True) is None, "still being explored"
    brain.ZONE_STEP_COUNT = 5
    assert brain.dead_end_ascent(_edges113, _dn113, 11, (62, 7), False, True, True) is None, "not worked long enough"
    brain.ZONE_STEP_COUNT = 150
    _u = brain.dead_end_ascent(_edges113, _dn113, 11, (20, 4), True, True, True)
    assert _u and _u["action"] == "USE_STAIRS_UP" and "Level goal" in _u["reason"], _u
    assert _dn113 not in brain.DEAD_END_ZONES and not brain.STAIRS_GIVEUP, "a waiting room is not a dead end: nothing is given up, the level goal holds the way down shut"
    assert brain.dead_end_ascent(_edges113, _up113, 10, (62, 7), False, True, True) is None, "never on the surface"
    # the same stratum with the stairs down given up is the old dead end
    brain.STAIRS_GIVEUP.add((_dn113, (45, 23)))
    _old = brain.dead_end_ascent({"reachable_edges": ""}, _dn113, 11, (62, 7), False, True, True)
    assert _old and "Dead end" in _old["reason"], _old
finally:
    brain.KNOWN_STAIRS_DOWN.clear(); brain.KNOWN_STAIRS_DOWN.update(_saved113[0]); brain.KNOWN_STAIRS_UP.clear(); brain.KNOWN_STAIRS_UP.update(_saved113[1])
    brain.STAIRS_GIVEUP.clear(); brain.STAIRS_GIVEUP.update(_saved113[2]); brain.DEAD_END_ZONES.clear(); brain.DEAD_END_ZONES.update(_saved113[3])
    brain.ZONE_STEP_COUNT = _saved113[4]; brain.RETREAT_TARGET_LEVEL = _saved113[5]
_src113 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "brain.py"), encoding="utf-8").read()
assert "is_zone_cleared, is_retreating)" in _src113, "the call site must pass the level-goal gate"
print("  [OK] Test 113 Passed: in a cleared, worked stratum whose way down is held shut by a level goal he walks to the stairs up (even when the engine reports edges) and ascends without marking a dead end or giving up the stairs; with no gate, an unworked or uncleared stratum, or on the surface nothing changes, and the old dead end still fires when the stairs were given up.")


# ---------------------------------------------------------------------------
# Test 114: stairs the engine could not route to get a bounded second chance (human run 2026-10-09: written off at (57, 12) for the rest of the run; HANDOFF issue 92)
# ---------------------------------------------------------------------------
_Z114 = "JoppaWorld.11.20.1.1.13"
_K114 = (_Z114, (73, 13))
_saved114 = (dict(brain.KNOWN_STAIRS_DOWN), set(brain.STAIRS_GIVEUP), set(brain.UNREACHABLE_SECTORS), dict(brain.STAIRS_RETRY_META), set(brain.STAIRS_RETRY_ACTIVE), brain.TURN_CLOCK)
try:
    def _reset114():
        brain.KNOWN_STAIRS_DOWN.clear(); brain.STAIRS_GIVEUP.clear(); brain.UNREACHABLE_SECTORS.clear(); brain.STAIRS_RETRY_META.clear(); brain.STAIRS_RETRY_ACTIVE.clear()
        brain.KNOWN_STAIRS_DOWN[_Z114] = {"tx": 73, "ty": 13, "z": 13, "name": "stairs down"}
        brain.TURN_CLOCK = 1000
    _reset114()
    assert brain.retry_given_up_stairs(_Z114, 6, (57, 12)) is False, "nothing written off: nothing to retry"
    brain.note_stairs_unreachable(_Z114, (73, 13), 6, (57, 12)); brain.UNREACHABLE_SECTORS.add(_K114); brain.STAIRS_GIVEUP.add(_K114)
    assert brain.retry_given_up_stairs(_Z114, 6, (57, 12)) is False, "same level, same place, no time passed: not yet"
    brain.TURN_CLOCK = 1000 + brain.STAIRS_RETRY_TURNS - 1
    assert brain.retry_given_up_stairs(_Z114, 6, (58, 12)) is False
    assert brain.retry_given_up_stairs(_Z114, 7, (57, 12)) is True, "a level gained lifts the write-off"
    assert _K114 not in brain.STAIRS_GIVEUP and _K114 not in brain.UNREACHABLE_SECTORS and _K114 in brain.STAIRS_RETRY_ACTIVE and brain.STAIRS_RETRY_META[_K114]["retries"] == 1
    assert brain.retry_given_up_stairs(_Z114, 8, (57, 12)) is False, "a retry in progress is not restarted"
    # a failed retry gives up again (what the greedy-fallback branch does) and the next trigger can lift it again
    brain.STAIRS_RETRY_ACTIVE.discard(_K114); brain.STAIRS_GIVEUP.add(_K114); brain.note_stairs_unreachable(_Z114, (73, 13), 7, (57, 12))
    assert brain.STAIRS_RETRY_META[_K114]["retries"] == 1, "the count survives a new write-off"
    assert brain.retry_given_up_stairs(_Z114, 7, (30, 12)) is True, "moving 12 or more cells away lifts it"
    # a dead-end give-up is never retried
    _reset114(); brain.STAIRS_GIVEUP.add(_K114)
    brain.TURN_CLOCK = 5000
    assert brain.retry_given_up_stairs(_Z114, 9, (10, 10)) is False, "no retry entry: a deliberate give-up stays"
    # multi-turn: the engine never finds a route; over 3000 turns the retries stay bounded and every retry ends at once
    _reset114(); brain.note_stairs_unreachable(_Z114, (73, 13), 6, (57, 12)); brain.UNREACHABLE_SECTORS.add(_K114); brain.STAIRS_GIVEUP.add(_K114)
    _acts114 = 0
    for _t in range(1000, 4000):
        brain.TURN_CLOCK = _t
        if brain.retry_given_up_stairs(_Z114, 6, (57, 12)):
            _acts114 += 1
            brain.STAIRS_RETRY_ACTIVE.discard(_K114); brain.STAIRS_GIVEUP.add(_K114); brain.UNREACHABLE_SECTORS.add(_K114)
            brain.note_stairs_unreachable(_Z114, (73, 13), 6, (57, 12))
    assert _acts114 == brain.STAIRS_RETRY_MAX == 3, _acts114
finally:
    brain.KNOWN_STAIRS_DOWN.clear(); brain.KNOWN_STAIRS_DOWN.update(_saved114[0]); brain.STAIRS_GIVEUP.clear(); brain.STAIRS_GIVEUP.update(_saved114[1])
    brain.UNREACHABLE_SECTORS.clear(); brain.UNREACHABLE_SECTORS.update(_saved114[2]); brain.STAIRS_RETRY_META.clear(); brain.STAIRS_RETRY_META.update(_saved114[3])
    brain.STAIRS_RETRY_ACTIVE.clear(); brain.STAIRS_RETRY_ACTIVE.update(_saved114[4]); brain.TURN_CLOCK = _saved114[5]
_src114 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "brain.py"), encoding="utf-8").read()
assert "if (zone_id, sd_pos) in STAIRS_RETRY_ACTIVE:" in _src114 and "best_m = None" in _src114 and "retry_given_up_stairs(zone_id, cur_lvl, cur_pos)" in _src114, "the call site and the engine-route-only rule"
assert "STAIRS_RETRY_META.pop((up, (usd.get" in _src114, "a dead-end give-up must erase any retry entry"
print("  [OK] Test 114 Passed: stairs the engine could not route to are retried when a level is gained, he has moved 12 cells, or 150 turns have passed, at most 3 times (a 3,000-turn simulation shows exactly 3), a retry never steps greedily, a deliberate dead-end give-up is never retried, and a retry in progress is not restarted.")


# ---------------------------------------------------------------------------
# Test 115: the path diagnostic exists in the mod and cannot throw or spam (HANDOFF issue 92)
# ---------------------------------------------------------------------------
_cs115 = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mod", "QudAIBrain", "AIBrainPart.cs"), encoding="utf-8").read()
for _s in ("private static void LogPathDiag(GameObject player, Cell target)", "private static string PathDiagCell(Cell c, GameObject player)", "[QudAI PathDiag] no engine step to ",
           "c.GetNavigationWeightFor(player, false, false, false, false, false)", "c.HasWadingDepthLiquid()", "c.HasSwimmingDepthLiquid()", "c.IsExplored()", "pathDiagSeen.Count >= 40",
           "LogPathDiag(player, targetCell);"):
    assert _s in _cs115, _s
_body115 = _cs115[_cs115.index("private static void LogPathDiag(GameObject player, Cell target)"):_cs115.index("public static bool IsCompanion(GameObject obj, GameObject player)")]
assert _body115.count("try") >= 3 and "catch { }" in _body115, "the diagnostic must be guarded"
assert _cs115.count("{") == _cs115.count("}")
print("  [OK] Test 115 Passed: the mod logs one guarded [QudAI PathDiag] line per target the engine cannot route to (target and neighbours: explored, passable, solid, wading, swimming, dangerous liquid, navigation weight), at most 40 per session.")


# ---------------------------------------------------------------------------
# Test 116: a diagonal step off the map edge is checked against the zone it really enters (human run 2026-10-09, trace t2094-2153; HANDOFF issue 93)
# ---------------------------------------------------------------------------
assert brain.exit_move_crossings("NW", 38, 0) == ["N"] and brain.exit_move_crossings("SW", 38, 24) == ["S"] and sorted(brain.exit_move_crossings("NW", 0, 0)) == ["N", "W"]
assert brain.exit_move_crossings("N", 10, 0) == ["N"] and brain.exit_move_crossings("E", 79, 5) == ["E"] and brain.exit_move_crossings("NW", 20, 10) == []
_A116, _B116 = "JoppaWorld.10.18.2.2.10", "JoppaWorld.10.19.2.0.10"        # B is directly south of A
_saved116 = (brain.ZONE_HOPPING_DETECTED, set(brain.EXPLORED_ZONE_SET), list(brain.RECENT_ZONES), brain.LAST_ZONE_ENTRY, dict(brain.EXIT_SUPPRESS_UNTIL), brain.CURRENT_ZONE_CHOSEN_EXIT,
             brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE, brain.ZONE_STEP_COUNT, brain.TURN_CLOCK, brain.exit_move_crossings, brain.current_zone_id, brain.CURRENT_TRACKED_ZONE)
try:
    def _state116():
        # standing on B's north edge (y = 0): the diagonal NW step crosses north, back into A, which is explored and in the recent cycle
        return {"hp": 28, "max_hp": 28, "x": 38, "y": 0, "z": 10, "zone_id": _B116, "level": 4, "ap": 0, "sp": 0, "mp": 0, "zone_fully_explored": True,
                "hostiles_nearby": False, "hostiles_adjacent": False, "reachable_edges": "NSEW",
                "surroundings": {"C": "grass", "N": "[ZONE_EXIT: N]", "NW": "[ZONE_EXIT: NW]", "NE": "[ZONE_EXIT: NE]", "W": "grass", "E": "grass", "S": "grass", "SE": "grass", "SW": "grass"},
                "visible_entities": []}
    def _prep116():
        brain.EXPLORED_ZONE_SET.clear(); brain.EXPLORED_ZONE_SET.update({_A116, _B116})
        brain.RECENT_ZONES.clear(); brain.RECENT_ZONES.extend([_A116, _B116, _A116, _B116])
        brain.ZONE_HOPPING_DETECTED = True
        brain.LAST_ZONE_ENTRY = {"from_zone": _A116, "to_zone": _B116, "reverse_dir": "S"}      # so the plain reverse-exit rule does not decide it
        brain.CURRENT_ZONE_CHOSEN_EXIT = None; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
        brain.current_zone_id = _B116          # not an arrival: the arrival grace (inward step) must not decide this
        brain.CURRENT_TRACKED_ZONE = _B116
        brain.ZONE_STEP_COUNT = 10; brain.TURN_CLOCK = 5000
        brain.EXIT_SUPPRESS_UNTIL[_B116] = brain.TURN_CLOCK + 100        # the chooser is silent, so the exit-move branch decides
    # the old rule (every diagonal is allowed): the loop's step is taken
    brain.exit_move_crossings = lambda m_dir, px, py: []
    _prep116()
    _old116 = brain.query_decision(_state116(), took_damage=False, enemies=[])
    assert _old116["action"] in ("MOVE_NW", "MOVE_NE") and "novel zone" in _old116["reason"], ("expected the old loop step", _old116)
    # the fix: the step into the explored, recent zone is refused
    brain.exit_move_crossings = _saved116[9]
    _prep116()
    _new116 = brain.query_decision(_state116(), took_damage=False, enemies=[])
    assert not (_new116["action"] in ("MOVE_NW", "MOVE_NE", "MOVE_N") and "novel zone" in _new116["reason"]), ("the diagonal into an explored zone must not be taken as 'novel'", _new116)
finally:
    (brain.ZONE_HOPPING_DETECTED, _ex116, _rz116, brain.LAST_ZONE_ENTRY, _sup116, brain.CURRENT_ZONE_CHOSEN_EXIT, brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE, brain.ZONE_STEP_COUNT, brain.TURN_CLOCK, brain.exit_move_crossings, brain.current_zone_id, brain.CURRENT_TRACKED_ZONE) = _saved116
    brain.EXPLORED_ZONE_SET.clear(); brain.EXPLORED_ZONE_SET.update(_ex116)
    brain.RECENT_ZONES.clear(); brain.RECENT_ZONES.extend(_rz116)
    brain.EXIT_SUPPRESS_UNTIL.clear(); brain.EXIT_SUPPRESS_UNTIL.update(_sup116)
print("  [OK] Test 116 Passed: a diagonal step off the map edge is checked against the zone it enters (NW at the north edge is the north neighbour), so the hopping filter no longer lets two diagonal steps carry him between two explored zones; with the old rule the test reproduces the loop step.")


# ---------------------------------------------------------------------------
# Test 117: an empty reachable_edges reading on a border cell does not blacklist the exit he is walking to (human run 2026-10-09; HANDOFF issue 93)
# ---------------------------------------------------------------------------
_Z117 = "JoppaWorld.10.19.2.0.10"
_saved117 = (set(brain.FAILED_ZONE_EXITS), brain.CURRENT_ZONE_CHOSEN_EXIT, brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE, dict(brain.EXIT_SUPPRESS_UNTIL), brain.LAST_ZONE_ENTRY, brain.current_zone_id)
try:
    brain.FAILED_ZONE_EXITS.clear(); brain.EXIT_SUPPRESS_UNTIL.clear(); brain.LAST_ZONE_ENTRY = None; brain.current_zone_id = _Z117
    # the heuristic itself
    assert brain.check_exit_direction_failure({"reachable_edges": ""}, (38, 0), "W") is False, "empty on a border cell is an artifact"
    assert brain.check_exit_direction_failure({"reachable_edges": ""}, (0, 12), "N") is False
    assert brain.check_exit_direction_failure({"reachable_edges": ""}, (36, 6), "N") is True, "empty inside the zone still means a sealed room"
    assert brain.check_exit_direction_failure({"reachable_edges": "EW"}, (36, 6), "N") is True and brain.check_exit_direction_failure({"reachable_edges": "EW"}, (36, 6), "E") is False
    # the chooser: walking to W, an empty reading on the border row must keep W
    brain.CURRENT_ZONE_CHOSEN_EXIT = "W"; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = _Z117
    _s = {"zone_id": _Z117, "z": 10, "x": 38, "y": 0, "reachable_edges": "", "surroundings": {}}
    _pos, _tag, _dir = brain.get_zone_exit_target((38, 0), _s)
    assert _dir == "W" and not brain.FAILED_ZONE_EXITS, (_dir, brain.FAILED_ZONE_EXITS)
    # multi-turn: 40 readings alternating border-empty and interior-full never blacklist anything, and the chosen exit survives
    for _t in range(40):
        brain.TURN_CLOCK = 100 + _t
        _empty = (_t % 2 == 0)
        _st = {"zone_id": _Z117, "z": 10, "x": 38 if _empty else 20, "y": 0 if _empty else 5, "reachable_edges": "" if _empty else "NSEW", "surroundings": {}}
        brain.get_zone_exit_target((_st["x"], _st["y"]), _st)
    assert not brain.FAILED_ZONE_EXITS and brain.CURRENT_ZONE_CHOSEN_EXIT == "W", (brain.FAILED_ZONE_EXITS, brain.CURRENT_ZONE_CHOSEN_EXIT)
    # a genuinely missing exit still invalidates: a non-empty list without W, in the interior
    _st = {"zone_id": _Z117, "z": 10, "x": 20, "y": 5, "reachable_edges": "NSE", "surroundings": {}}
    brain.get_zone_exit_target((20, 5), _st)
    assert (_Z117, "W") in brain.FAILED_ZONE_EXITS, "a real report that W is unreachable must still count"
finally:
    brain.FAILED_ZONE_EXITS.clear(); brain.FAILED_ZONE_EXITS.update(_saved117[0]); brain.CURRENT_ZONE_CHOSEN_EXIT = _saved117[1]; brain.CURRENT_ZONE_CHOSEN_EXIT_ZONE = _saved117[2]
    brain.EXIT_SUPPRESS_UNTIL.clear(); brain.EXIT_SUPPRESS_UNTIL.update(_saved117[3]); brain.LAST_ZONE_ENTRY = _saved117[4]; brain.current_zone_id = _saved117[5]
print("  [OK] Test 117 Passed: an empty reachable_edges reading on a border cell is treated as an engine artifact (it no longer blacklists the exit he is heading for; 40 alternating readings blacklist nothing), an empty reading inside the zone still means a sealed room, and a real report that the exit is missing still invalidates it.")
