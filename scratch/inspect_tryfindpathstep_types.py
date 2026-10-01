import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
for t in pe.net.mdtables.TypeDef:
    if str(t.TypeName) == 'AutoAct':
        for m in t.MethodList:
            if 'TryFindPathStep' in str(m.row.Name):
                print(f"Method: {m.row.Name}")
                # check parameter types
                # dnfile method signature
                print('Signature length:', len(m.row.Signature))
