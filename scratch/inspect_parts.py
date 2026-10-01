with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

for target in [b"Campfire", b"MakeCamp", b"Butchery", b"Harvestry"]:
    pos = 0
    print(f"\n=== Searching for {target.decode()} ===")
    count = 0
    while count < 3:
        idx = data.find(target, pos)
        if idx == -1:
            break
        start = max(0, idx - 60)
        end = min(len(data), idx + 120)
        clean = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[start:end])
        print(f"Match at {idx}: {clean}")
        pos = idx + len(target)
        count += 1
