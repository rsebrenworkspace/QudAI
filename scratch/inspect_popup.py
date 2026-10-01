import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for row in pe.net.mdtables.TypeDef:
    t_name = str(row.TypeName)
    if t_name == "Popup" and "UI" in str(row.TypeNamespace):
        print(f"Type: {row.TypeNamespace}.{t_name}")
        for m in getattr(row, 'MethodList', []):
            try:
                print(f"  Method: {m.row.Name}")
            except:
                pass
