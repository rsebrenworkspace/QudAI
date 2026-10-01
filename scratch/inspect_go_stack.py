import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for row in pe.net.mdtables.TypeDef:
    if str(row.TypeName) == "GameObject" and str(row.TypeNamespace) == "XRL.World":
        for m in row.MethodList:
            m_name = str(m.row.Name)
            if any(k in m_name for k in ["Stack", "Count", "Split", "Consume", "Remove"]):
                params = [str(p.row.Name) for p in getattr(m, 'ParamList', []) if hasattr(p, 'row')]
                print(f"GameObject.{m_name}({', '.join(params)})")
