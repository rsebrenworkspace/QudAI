with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

for term in [b"Famished", b"Hungry", b"Starving", b"Satiated"]:
    pos = 0
    print(f"\n=== Searching for {term.decode()} ===")
    count = 0
    while count < 3:
        idx = data.find(term, pos)
        if idx == -1:
            break
        start = max(0, idx - 40)
        end = min(len(data), idx + 80)
        clean = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[start:end])
        print(f"Match at {idx}: {clean}")
        pos = idx + len(term)
        count += 1
