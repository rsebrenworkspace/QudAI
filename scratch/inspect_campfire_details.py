import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
for row in pe.net.mdtables.TypeDef:
    t_name = str(row.TypeName)
    t_ns = str(row.TypeNamespace)
    if t_name == "Campfire" and t_ns == "XRL.World.Parts":
        print(f"Found {t_ns}.{t_name}")
        for m in getattr(row, 'MethodList', []):
            try:
                m_name = m.row.Name
                print(f"Method: {m_name}")
            except Exception as e:
                pass
