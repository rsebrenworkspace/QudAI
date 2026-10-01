import sys
sys.path.insert(0, r'D:\QudAI')
import brain

# Simulate character at the shoreline, e.g. at (40, 10)
# To the North is water: 'deep pool of rules|4000 drams of salty water'
# To the South is dry land: 'watervine' (visited 1 time)
# To the East is dry land: 'riverbank dirt' (visited 0 times or 1 time)
# To the West is dry land: 'watervine' (visited 1 time)

surroundings = {
    "N": "deep pool of rules|4000 drams of salty water",
    "S": "watervine",
    "E": "riverbank dirt",
    "W": "watervine",
    "NW": "pool of rules|500 drams of salty water",
    "NE": "deep pool of rules|4000 drams of salty water",
    "SW": "watervine",
    "SE": "watervine",
}

cur_pos = (40, 10)
brain.visit_counts.clear()
brain.visit_counts[(40, 11)] = 1 # S
brain.visit_counts[(39, 10)] = 1 # W
brain.visit_counts[(41, 10)] = 0 # E (unvisited shoreline tile!)
brain.visit_counts[(40, 9)] = 0  # N (unvisited water tile!)

valid_m = brain.get_valid_moves(surroundings, cur_pos, None, is_in_combat=False)
print("Valid moves:", valid_m)

ranked = sorted(valid_m, key=lambda m: (
    brain.visit_counts[(cur_pos[0] + brain.CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + brain.CARDINAL_OFFSETS[m[5:]][1])],
    1 if brain.is_swim_move(m, surroundings) else 0
))

print("Ranked moves:")
for m in ranked:
    nx = cur_pos[0] + brain.CARDINAL_OFFSETS[m[5:]][0]
    ny = cur_pos[1] + brain.CARDINAL_OFFSETS[m[5:]][1]
    vc = brain.visit_counts[(nx, ny)]
    sw = 1 if brain.is_swim_move(m, surroundings) else 0
    print(f"  {m} -> dest ({nx}, {ny}), visits={vc}, is_swim={sw}, sort_key={(vc, sw)}")
