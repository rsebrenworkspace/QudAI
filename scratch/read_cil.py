import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def read_method_cil(rva):
    offset = pe.get_offset_from_rva(rva)
    # Read method header
    first_byte = pe.get_data(rva, 1)[0]
    header_type = first_byte & 3
    if header_type == 2:  # Tiny header
        code_size = first_byte >> 2
        header_size = 1
    elif header_type == 3:  # Fat header
        header_bytes = pe.get_data(rva, 12)
        flags = (header_bytes[1] << 8) | header_bytes[0]
        header_size = (flags >> 12) * 4
        code_size = int.from_bytes(header_bytes[4:8], 'little')
    else:
        return f"Unknown header: {header_type}"
    
    code = pe.get_data(rva + header_size, code_size)
    return code_size, code

for name, rva in [("Cook", 0x433fcc), ("CookPresetMeal", 0x432d08), ("ClearHunger", 0x43431b)]:
    sz, raw = read_method_cil(rva)
    print(f"=== {name} (size: {sz}) ===")
    # Look for UserStrings or MemberRefs in raw bytes
    # Find ldstr tokens (0x72 xx xx xx 70)
    for i in range(len(raw) - 4):
        if raw[i] == 0x72 and raw[i+4] == 0x70:
            token = int.from_bytes(raw[i+1:i+5], 'little')
            try:
                # get user string
                us_offset = token & 0x00FFFFFF
                us = pe.net.user_strings.get_us(us_offset)
                print(f"  String token {hex(token)}: {us.value}")
            except Exception as e:
                pass
        # Find call / callvirt (0x28 or 0x6f)
        if raw[i] in (0x28, 0x6f):
            token = int.from_bytes(raw[i+1:i+5], 'little')
            table_id = token >> 24
            row_id = token & 0x00FFFFFF
            try:
                if table_id == 6: # MethodDef
                    target_name = pe.net.mdtables.MethodDef[row_id - 1].Name
                    print(f"  Call MethodDef: {target_name}")
                elif table_id == 10: # MemberRef
                    target_name = pe.net.mdtables.MemberRef[row_id - 1].Name
                    print(f"  Call MemberRef: {target_name}")
            except Exception:
                pass
