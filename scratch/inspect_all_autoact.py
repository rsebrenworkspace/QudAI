import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
for t in pe.net.mdtables.TypeDef:
    if str(t.TypeName) == 'AutoAct':
        for m in t.MethodList:
            params = []
            if m.row.ParamList:
                for p in m.row.ParamList:
                    params.append(str(p.row.Name))
            print(f"AutoAct.{m.row.Name}({', '.join(params)})")
