import json, os

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

px = state.get('x')
py = state.get('y')

print(f"Player at ({px}, {py})")
nearby_entities = []
for e in state.get('visible_entities', []):
    ex = e.get('tx')
    ey = e.get('ty')
    if ex is not None and ey is not None and abs(ex - px) <= 6 and abs(ey - py) <= 6:
        nearby_entities.append(e)

print(f"Entities within 6 tiles ({len(nearby_entities)}):")
for e in nearby_entities:
    print(f"  ({e.get('tx')}, {e.get('ty')}): {e.get('name')} | hostile={e.get('is_hostile')} | diff={e.get('difficulty')}")
