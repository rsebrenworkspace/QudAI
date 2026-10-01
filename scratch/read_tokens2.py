import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get("#US")
print("us stream type:", type(us))
print("us stream dir:", [m for m in dir(us) if not m.startswith("_")])
for tok in [0x0f29a8, 0x0f29c0, 0x0f29da, 0x0f29f6]:
    try:
        val = us.get(tok)
        print(f"tok {hex(tok)}: {repr(val)}")
    except Exception as e:
        print(f"error on {hex(tok)}: {e}")
