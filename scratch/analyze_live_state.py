import os, json, sys
sys.path.insert(0, r'D:\QudAI')
import brain

p = os.path.expandvars(r'%APPDATA%\..\LocalLow\Freehold Games\CavesOfQud\QudAI\last_state.json')
with open(p, 'r', encoding='utf-8-sig') as f:
    state = json.load(f)

print('Player position:', state.get('x'), state.get('y'), state.get('z'))
print('Zone ID:', state.get('zone_id'))
print('Zone fully explored:', state.get('zone_fully_explored'))
print('Hunger:', state.get('hunger_level'), 'is_famished:', state.get('is_famished'))
print('HP:', state.get('hp'), '/', state.get('max_hp'))
print('Surroundings:')
for d in ['NW', 'N', 'NE', 'W', 'CENTER', 'E', 'SW', 'S', 'SE']:
    print(f'  {d}: {state.get("surroundings", {}).get(d)}')

valid_m = brain.get_valid_moves(state.get('surroundings', {}), (state.get('x'), state.get('y')), None, is_in_combat=False)
print('Valid moves from get_valid_moves:', valid_m)

decision = brain.query_decision(state, took_damage=False, enemies=[])
print('Decision:', decision)
