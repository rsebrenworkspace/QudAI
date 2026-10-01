import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Inspect Cell methods related to liquid and swimming
for row in pe.net.mdtables.TypeDef:
    t_name = str(row.TypeName)
    t_ns = str(row.TypeNamespace)
    if t_name == "Cell" and t_ns == "XRL.World":
        for m in row.MethodList:
            m_name = str(m.row.Name)
            if any(k in m_name for k in ["Liquid", "Swim", "Passable"]):
                sig = list(m.row.Signature.value)
                params = [str(p.row.Name) for p in getattr(m, 'ParamList', []) if hasattr(p, 'row')]
                print(f"Cell.{m_name}({', '.join(params)})")
    if "Swim" in t_name:
        print(f"Type with Swim: {t_ns}.{t_name}")
