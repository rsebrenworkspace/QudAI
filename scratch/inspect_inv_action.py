import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def inspect_method(rva):
    first_byte = pe.get_data(rva, 1)[0]
    header_type = first_byte & 3
    if header_type == 2:
        code_size = first_byte >> 2
        header_size = 1
    elif header_type == 3:
        header_bytes = pe.get_data(rva, 12)
        flags = (header_bytes[1] << 8) | header_bytes[0]
        header_size = (flags >> 12) * 4
        code_size = int.from_bytes(header_bytes[4:8], 'little')
    else:
        return []
    
    code = pe.get_data(rva + header_size, code_size)
    return code

raw = inspect_method(0x431f24) # InventoryActionEvent handler
print("=== HandleEvent 0x431f24 calls and strings ===")
for i in range(len(raw) - 4):
    if raw[i] == 0x72 and raw[i+4] == 0x70:
        token = int.from_bytes(raw[i+1:i+5], 'little')
        us_offset = token & 0x00FFFFFF
        try:
            print("  String:", pe.net.user_strings.get(us_offset))
        except:
            pass
    if raw[i] in (0x28, 0x6f):
        token = int.from_bytes(raw[i+1:i+5], 'little')
        table_id = token >> 24
        row_id = token & 0x00FFFFFF
        try:
            if table_id == 6:
                print("  MethodDef:", pe.net.mdtables.MethodDef[row_id - 1].Name)
            elif table_id == 10:
                print("  MemberRef:", pe.net.mdtables.MemberRef[row_id - 1].Name)
        except:
            pass
