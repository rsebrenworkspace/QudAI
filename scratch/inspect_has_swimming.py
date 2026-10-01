import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')

def find_method(typename, methodname):
    for r in pe.net.mdtables.TypeDef:
        if str(r.TypeName) == typename:
            for m in r.MethodList:
                if str(m.row.Name) == methodname:
                    return m
    return None

m = find_method('Cell', 'HasSwimmingDepthLiquid')
print('HasSwimmingDepthLiquid RVA:', hex(m.row.Rva))

# Read method body
rva = m.row.Rva
offset = pe.get_offset_from_rva(rva)
pe.parse_method_body(m)
# Let's inspect bytes or opcodes
print('Size/Offset:', offset)
