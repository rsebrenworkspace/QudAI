import os
import requests
import json

folder = r"C:\QudAI"
state_path = os.path.join(folder, "state.json")

print(f"1. Checking directory: {os.path.exists(folder)}")
print(f"2. Checking state.json: {os.path.exists(state_path)}")

if not os.path.exists(folder):
    os.makedirs(folder)
    print("   Created C:\\QudAI directory.")

# Create the test file programmatically so extension mistakes are impossible
sample_data = {"hp": 18, "max_hp": 20, "surroundings": "Joppa, near a watervine patch"}
with open(state_path, "w") as f:
    json.dump(sample_data, f)
print("3. Wrote test state.json successfully.")

# Test connection to LM Studio
print("4. Testing connection to LM Studio on port 1234...")
try:
    res = requests.get("http://localhost:1234/v1/models", timeout=5)
    print("   LM Studio reachable! Available models:", [m['id'] for m in res.json().get('data', [])])
except Exception as e:
    print(f"   Could not reach LM Studio: {e}")