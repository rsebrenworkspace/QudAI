import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for row in pe.net.mdtables.MethodDef:
    m_name = str(row.Name)
    if "Split" in m_name:
        # find class
        parent_class = None
        # In TypeDef, find which type owns this method
        print(f"Method: {m_name}")
        # print params
        for p in getattr(row, 'ParamList', []):
            try:
                print(f"  Param: {p.row.Name}")
            except:
                pass
