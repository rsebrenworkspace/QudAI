import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

campfire_type = None
for row in pe.net.mdtables.TypeDef:
    if str(row.TypeName) == "Campfire" and str(row.TypeNamespace) == "XRL.World.Parts":
        campfire_type = row
        break

# Find .cctor
for m in campfire_type.MethodList:
    if str(m.row.Name) == ".cctor":
        # Disassemble .cctor
        first_byte = pe.get_data(m.row.Rva, 1)[0]
        header_type = first_byte & 3
        if header_type == 2:
            code_size = first_byte >> 2
            header_size = 1
        elif header_type == 3:
            header_bytes = pe.get_data(m.row.Rva, 12)
            flags = (header_bytes[1] << 8) | header_bytes[0]
            header_size = (flags >> 12) * 4
            code_size = int.from_bytes(header_bytes[4:8], 'little')
        code = pe.get_data(m.row.Rva + header_size, code_size)
        
        last_str = ""
        for i in range(len(code)):
            if code[i] == 0x72: # ldstr
                tok = int.from_bytes(code[i+1:i+5], 'little') & 0x00FFFFFF
                try:
                    last_str = str(pe.net.user_strings.get(tok))
                except:
                    pass
            elif code[i] == 0x80: # stsfld
                tok = int.from_bytes(code[i+1:i+5], 'little')
                rid = tok & 0x00FFFFFF
                f = pe.net.mdtables.Field[rid - 1]
                print(f"{f.Name} = '{last_str}'")
