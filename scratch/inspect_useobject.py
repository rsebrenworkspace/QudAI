import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "GameObject":
        for m in getattr(t, "MethodList", []):
            if m.row and str(m.row.Name) == "UseObject":
                print(f"UseObject signature:")
                # print parameters
                for p in getattr(m.row, "ParamList", []):
                    if p.row:
                        print(f"  Param: {p.row.Name}")
