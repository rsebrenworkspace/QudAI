import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
for row in pe.net.mdtables.TypeDef:
    t_name = str(row.TypeName)
    t_ns = str(row.TypeNamespace)
    if "Campfire" in t_name or "Cooking" in t_name:
        print(f"Type: {t_ns}.{t_name}")
        # inspect methods
        for m in getattr(row, 'MethodList', []):
            try:
                print(f"  Method: {m.row.Name}")
            except Exception:
                pass
