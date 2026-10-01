with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

import re

idx = 0
while True:
    idx = data.find(b"Stomach", idx)
    if idx == -1:
        break
    start = max(0, idx - 100)
    end = min(len(data), idx + 200)
    clean = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[start:end])
    print(f"Stomach at {idx}: {clean}")
    idx += 7
    if idx > 12000000:
        break
