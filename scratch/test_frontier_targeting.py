import json, os, sys
sys.path.insert(0, r'D:\QudAI')
import brain

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

px = state.get('x')
py = state.get('y')
cur_pos = (px, py)
print(f"Current player: {cur_pos}")

entities = state.get("visible_entities", [])
unvisited = [e for e in entities if e.get("tx") is not None and e.get("ty") is not None and brain.visit_counts.get((e["tx"], e["ty"]), 0) == 0]
distant = [e for e in unvisited if max(abs(e["tx"] - px), abs(e["ty"] - py)) >= 3]
distant.sort(key=lambda e: (max(abs(e["tx"] - px), abs(e["ty"] - py)), (e["tx"] - px)**2 + (e["ty"] - py)**2))

target = (distant[0]["tx"], distant[0]["ty"])
print(f"Nearest distant unexplored target: {target} ({distant[0]['name']})")

valid_m = brain.get_valid_moves(state.get("surroundings", {}), cur_pos, None, is_in_combat=False)
print("Valid moves:", valid_m)

best_m = brain.get_best_move_towards(cur_pos, target, valid_m, state.get("surroundings", {}))
print(f"Best move toward target {target}: {best_m}")
