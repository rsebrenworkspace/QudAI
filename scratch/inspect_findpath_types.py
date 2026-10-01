import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
for t in pe.net.mdtables.TypeDef:
    if str(t.TypeName) == 'FindPath':
        for f in t.FieldList:
            if str(f.row.Name) in ['Directions', 'Steps', 'bFound', 'Found']:
                print('Field:', str(f.row.Name), 'sig bytes:', len(f.row.Signature))
