import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Find Stomach.FoodStatus
for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Stomach":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name in ("FoodStatus", "WaterStatus", "IsFamished", "UpdateHunger"):
                print(f"\nMethod {m.row.Name}:")
                rva = m.row.RVA
                offset = dn.get_offset_from_rva(rva)
                # Read 200 bytes of IL
                raw_il = dn.get_data(rva, 250)
                # Find any strings or tokens referenced
                # Also print text representations
                text = "".join(chr(b) if 32 <= b <= 126 else "." for b in raw_il)
                print(f"  IL raw: {text[:100]}")
