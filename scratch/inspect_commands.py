with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

needle = "Command".encode("utf-16le")
pos = 0
found = set()
while True:
    idx = data.find(needle, pos)
    if idx == -1: break
    s_end = idx
    while s_end + 1 < len(data) and data[s_end+1] == 0 and 32 <= data[s_end] <= 126:
        s_end += 2
    try:
        raw = data[idx:s_end+2].decode("utf-16le", errors="ignore")
        s = "".join(c for c in raw if 32 <= ord(c) <= 126)
        if any(k in s.lower() for k in ["camp", "cook", "butcher", "harvest", "eat", "drink", "rest", "food", "survival"]):
            found.add(s)
    except Exception:
        pass
    pos = idx + len(needle)

print(f"Found {len(found)} relevant Command strings:")
for item in sorted(found):
    print(f"  {item}")
