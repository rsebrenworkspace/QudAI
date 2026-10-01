with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

start = 8602000
end = 8602500
clean = "".join(chr(b) if 32 <= b <= 126 else "\n" for b in data[start:end])
print("\n".join(s for s in clean.splitlines() if len(s) > 2))
