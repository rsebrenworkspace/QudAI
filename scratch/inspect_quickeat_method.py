import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    for m in getattr(t, "MethodList", []):
        if m.row and m.row.Name:
            name_str = str(m.row.Name.value if hasattr(m.row.Name, "value") else m.row.Name).lower()
            if any(k in name_str for k in ["quickeat", "quickdrink", "eatfood", "butcher", "harvest"]):
                print(f"Class: {t.TypeNamespace}.{t.TypeName} -> Method: {m.row.Name}")
