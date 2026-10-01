import json, os

def find_zone_unexplored_frontier(game_state, cur_pos, visit_counts):
    px, py = cur_pos
    entities = game_state.get("visible_entities", [])
    if not entities:
        return None, None

    # Check visible entities in unvisited sectors (e.g. across water/river)
    unvisited_entities = []
    for e in entities:
        tx = e.get("tx")
        ty = e.get("ty")
        if tx is not None and ty is not None:
            if visit_counts.get((tx, ty), 0) == 0:
                unvisited_entities.append((tx, ty))

    if unvisited_entities:
        # Distance at least 4 tiles away
        distant_unvisited = [p for p in unvisited_entities if max(abs(p[0] - px), abs(p[1] - py)) >= 4]
        if distant_unvisited:
            # Sort by Chebyshev distance first, then Euclidean distance
            distant_unvisited.sort(key=lambda p: (max(abs(p[0] - px), abs(p[1] - py)), (p[0] - px)**2 + (p[1] - py)**2))
            target = distant_unvisited[0]
            return target, f"Water Traversal: Navigating across water toward unvisited frontier at {target}"

    return None, None

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

visits = {}
for x in range(80):
    for y in range(10, 25):
        visits[(x, y)] = 2

target, reason = find_zone_unexplored_frontier(state, (68, 18), visits)
print("Live river target:", target)
print("Reason:", reason)

# Test 19 scenario (entities = [])
t19_state = {"visible_entities": []}
t19_target, _ = find_zone_unexplored_frontier(t19_state, (14, 10), {})
print("Test 19 target:", t19_target)
