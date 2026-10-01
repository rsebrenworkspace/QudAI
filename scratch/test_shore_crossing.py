import json, os, sys
sys.path.insert(0, r'D:\QudAI')
import brain

# Simulate player at the shoreline facing the river: (68, 10)
# To the South (y >= 10), everything has been explored / visited
brain.visit_counts.clear()
for x in range(80):
    for y in range(10, 25):
        brain.visit_counts[(x, y)] = 2

# To the North (y < 10), nothing has been visited
# Let's run find_zone_unexplored_frontier
surroundings_at_shore = {
    "N": "deep pool of rules|4000 drams of salty water",
    "S": "watervine",
    "E": "watervine",
    "W": "watervine",
    "NW": "deep pool of rules|4000 drams of salty water",
    "NE": "deep pool of rules|4000 drams of salty water",
    "SW": "watervine",
    "SE": "watervine",
}

cur_pos = (68, 10)

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

# Find unvisited entity across water
entities = state.get("visible_entities", [])
unvisited = [e for e in entities if e.get("tx") is not None and e.get("ty") is not None and brain.visit_counts.get((e["tx"], e["ty"]), 0) == 0]
distant = [e for e in unvisited if max(abs(e["tx"] - cur_pos[0]), abs(e["ty"] - cur_pos[1])) >= 3]
distant.sort(key=lambda e: (max(abs(e["tx"] - cur_pos[0]), abs(e["ty"] - cur_pos[1])), (e["tx"] - cur_pos[0])**2 + (e["ty"] - cur_pos[1])**2))

target = (distant[0]["tx"], distant[0]["ty"])
print(f"Player at shore: {cur_pos}")
print(f"Target across river: {target} ({distant[0]['name']})")

valid_m = brain.get_valid_moves(surroundings_at_shore, cur_pos, None, is_in_combat=False)
print("Valid moves at shore:", valid_m)

best_m = brain.get_best_move_towards(cur_pos, target, valid_m, surroundings_at_shore)
print(f"Best move toward target {target}: {best_m}")
