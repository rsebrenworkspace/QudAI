import json, os

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

px = state.get('x')
py = state.get('y')
print(f"Current player: ({px}, {py})")

# Let's inspect visible_entities and find the centroid / clusters of entities
entities = state.get('visible_entities', [])
north_entities = [e for e in entities if e.get('ty') is not None and e.get('ty') <= 8]
south_entities = [e for e in entities if e.get('ty') is not None and e.get('ty') >= 10]

print(f"Entities in North (y <= 8): {len(north_entities)}")
print(f"Entities in South (y >= 10): {len(south_entities)}")

if north_entities:
    avg_nx = sum(e['tx'] for e in north_entities) / len(north_entities)
    avg_ny = sum(e['ty'] for e in north_entities) / len(north_entities)
    print(f"Northern entity cluster centroid: ({avg_nx:.1f}, {avg_ny:.1f})")
