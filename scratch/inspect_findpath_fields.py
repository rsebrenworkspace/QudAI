import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
for t in pe.net.mdtables.TypeDef:
    if str(t.TypeName) == 'FindPath':
        print('FindPath fields/properties:')
        for f in t.FieldList:
            print('  Field:', str(f.row.Name))
        for m in t.MethodList:
            if str(m.row.Name).startswith('get_'):
                print('  Property:', str(m.row.Name))
