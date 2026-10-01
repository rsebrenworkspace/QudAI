import json, os

def find_zone_unexplored_frontier(game_state, cur_pos, visit_counts):
    px, py = cur_pos
    entities = game_state.get("visible_entities", [])

    # 1. Check visible entities in unvisited sectors (e.g. across water/river)
    unvisited_entities = []
    for e in entities:
        tx = e.get("tx")
        ty = e.get("ty")
        if tx is not None and ty is not None:
            # We consider an entity unvisited if neither it nor its immediate neighbors have been visited
            if visit_counts.get((tx, ty), 0) == 0:
                unvisited_entities.append((tx, ty))

    if unvisited_entities:
        distant_unvisited = [p for p in unvisited_entities if max(abs(p[0] - px), abs(p[1] - py)) >= 4]
        if distant_unvisited:
            # Sort by Chebyshev distance first, then Euclidean distance
            distant_unvisited.sort(key=lambda p: (max(abs(p[0] - px), abs(p[1] - py)), (p[0] - px)**2 + (p[1] - py)**2))
            target = distant_unvisited[0]
            return target, f"Water Traversal: Navigating across river toward unvisited frontier at {target}"

    # 2. Macro-sector check across 80x25 grid
    north_visits = sum(visit_counts.get((x, y), 0) for x in range(80) for y in range(9))
    south_visits = sum(visit_counts.get((x, y), 0) for x in range(80) for y in range(16, 25))
    west_visits = sum(visit_counts.get((x, y), 0) for x in range(25) for y in range(25))
    east_visits = sum(visit_counts.get((x, y), 0) for x in range(55, 80) for y in range(25))

    if py >= 10 and north_visits == 0:
        return (px, 3), f"Water Traversal: Navigating North across water toward unexplored northern sector (y=3)"
    if py <= 14 and south_visits == 0:
        return (px, 21), f"Water Traversal: Navigating South across water toward unexplored southern sector (y=21)"
    if px >= 35 and west_visits == 0:
        return (10, py), f"Water Traversal: Navigating West across water toward unexplored western sector (x=10)"
    if px <= 45 and east_visits == 0:
        return (70, py), f"Water Traversal: Navigating East across water toward unexplored eastern sector (x=70)"

    return None, None

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

# Player at (68, 18), southern half visited
visits = {}
for x in range(80):
    for y in range(10, 25):
        visits[(x, y)] = 2

target, reason = find_zone_unexplored_frontier(state, (68, 18), visits)
print("Target:", target)
print("Reason:", reason)
