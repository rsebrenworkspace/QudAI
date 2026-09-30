import requests
import json
import time

url = "http://localhost:1234/v1/chat/completions"

# Check loaded model or pick first one
models_res = requests.get("http://localhost:1234/v1/models").json()
model_id = models_res['data'][0]['id']
print(f"Using model: {model_id}")

system_prompt = """You are a tactical combat AI controlling a character in Caves of Qud.
Analyze the game state and pick ONE optimal action from the provided Available Actions list.
Respond ONLY with a valid JSON object in this exact schema:
{
  "action": "<EXACT_ACTION_STRING>",
  "thought": "<Brief tactical reasoning, max 20 words>"
}"""

user_prompt = """CURRENT STATUS:
- Location: Red Rock (Level 1)
- HP: 16/24 (Took 4 damage last turn!)
- Water: 32 drams
- Status Effects: None
- Rifle Ammo: 3/6

VISIBLE THREATS:
- snapjaw scavenger at (14, 18), dist: 2 (E), wielding bone club

AVAILABLE ABILITIES:
- Sprint: READY (Cooldown: 0)

SURROUNDINGS:
- N: Clear ground
- S: Clear ground
- W: Clear ground (Safe kite vector)
- E: snapjaw scavenger

VALID ACTIONS:
- MOVE_W (Backpedal/kite)
- MOVE_N (Maneuver)
- MOVE_S (Maneuver)
- FIRE_MISSILE@14,18 (Shoot enemy)
- ACTIVATE_SPRINT (Gain massive movement speed to disengage)
- RELOAD (Dry magazine top-off)"""

payload = {
    "model": model_id,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.1,
    "max_tokens": 128
}

t0 = time.time()
res = requests.post(url, json=payload, timeout=20)
dt = time.time() - t0

print(f"\nResponse received in {dt:.2f}s:")
content = res.json()['choices'][0]['message']['content']
print(content)
