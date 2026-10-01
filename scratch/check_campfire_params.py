import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Campfire":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name in ("Cook", "PerformPreserve", "CookPresetMeal", "CookFromIngredients"):
                p_names = [p.row.Name.value if hasattr(p.row.Name, "value") else str(p.row.Name) for p in getattr(m.row, "ParamList", []) if p.row]
                print(f"Campfire.{m.row.Name} params: {p_names}")
