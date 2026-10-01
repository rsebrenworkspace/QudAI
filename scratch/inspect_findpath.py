import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
for t in pe.net.mdtables.TypeDef:
    if 'FindPath' in str(t.TypeName) or 'Pathfinding' in str(t.TypeNamespace):
        print(f"TypeDef: {t.TypeNamespace}.{t.TypeName}")
        for m in t.MethodList:
            params = []
            if m.row.ParamList:
                for p in m.row.ParamList:
                    params.append(str(p.row.Name))
            print(f"  {m.row.Name}({', '.join(params)})")
