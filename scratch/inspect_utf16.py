with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

terms = ["Campfire", "MakeCamp", "Butcher", "Harvest", "WhipUp", "Cook", "Preserve", "Stomach", "Hungry", "Famished"]

for term in terms:
    needle = term.encode("utf-16le")
    pos = 0
    found = set()
    while len(found) < 15:
        idx = data.find(needle, pos)
        if idx == -1: break
        s_start = idx
        while s_start >= 2 and data[s_start-1] == 0 and 32 <= data[s_start-2] <= 126:
            s_start -= 2
        s_end = idx
        while s_end + 1 < len(data) and data[s_end+1] == 0 and 32 <= data[s_end] <= 126:
            s_end += 2
        try:
            raw = data[s_start:s_end+2].decode("utf-16le", errors="ignore")
            # keep only printable ascii
            s = "".join(c for c in raw if 32 <= ord(c) <= 126)
            if len(s) >= len(term):
                found.add(s)
        except Exception:
            pass
        pos = idx + len(needle)
    print(f"\n=== {term}: {len(found)} matches ===")
    for item in sorted(found):
        print(f"  {item}")
