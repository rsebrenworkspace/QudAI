import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Stomach":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name in ("FoodStatus", "IsFamished"):
                rva = m.row.Rva
                raw = dn.get_data(rva, 60)
                b0 = raw[0]
                code = raw[1:1 + (b0 >> 2)] if (b0 & 3) == 2 else raw[12:12+(raw[4]|(raw[5]<<8))]
                print(f"=== {m.row.Name} ===")
                print(" ".join(f"{b:02x}" for b in code))
