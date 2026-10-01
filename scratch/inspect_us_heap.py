import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get(b"#US")
print("UserStringHeap members:", [m for m in dir(us) if not m.startswith("_")])
if hasattr(us, "get"):
    print("us.get(1):", us.get(1))
