import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')

for row in pe.net.mdtables.TypeDef:
    if row.TypeName == 'Statistic' and row.TypeNamespace == 'XRL.World':
        for method in row.MethodList:
            if str(method.row.Name) in ['set_BaseValue', 'set_Penalty', 'NotifyChange']:
                print(f"=== {method.row.Name} ===")
                rva = method.row.Rva
                data = pe.get_data(rva, 256)
                code_size = data[0] >> 2 if (data[0] & 3) == 2 else int.from_bytes(data[4:8], 'little')
                header_len = 1 if (data[0] & 3) == 2 else 12
                print(f"code_size: {code_size}")
