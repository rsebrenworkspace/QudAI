with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

import re

def find_context(needle, n=3):
    pos = 0
    while n > 0:
        idx = data.find(needle, pos)
        if idx == -1:
            break
        start = max(0, idx - 40)
        end = min(len(data), idx + 80)
        clean = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[start:end])
        print(f"[{needle.decode()}] {clean}")
        pos = idx + len(needle)
        n -= 1

find_context(b"Survival_Camp")
find_context(b"CookingAndGathering_Butchery")
find_context(b"XRL.World.Parts.Campfire")
find_context(b"XRL.World.Parts.Stomach")
