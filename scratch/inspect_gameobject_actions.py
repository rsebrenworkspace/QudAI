import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "GameObject":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name:
                name_str = str(m.row.Name.value if hasattr(m.row.Name, "value") else m.row.Name)
                if any(k in name_str.lower() for k in ["inventoryaction", "action", "eat", "drink", "use", "cook", "butcher"]):
                    print(f"GameObject method: {name_str}")
