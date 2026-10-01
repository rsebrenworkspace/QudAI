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

for t in pe.net.mdtables.TypeDef:
    t_name = str(t.TypeName)
    if t_name in ("Butcherable", "Harvestable"):
        for m in t.MethodList:
            m_name = str(m.row.Name)
            if m_name in ("AttemptButcher", "AttemptHarvest"):
                raw = inspect_method(m.row.Rva)
                print(f"=== {t_name}.{m_name} (size: {len(raw)}) ===")
                for i in range(len(raw) - 4):
                    if raw[i] == 0x72 and raw[i+4] == 0x70:
                        tok = int.from_bytes(raw[i+1:i+5], 'little') & 0x00FFFFFF
                        try: print("  String:", pe.net.user_strings.get(tok))
                        except: pass
                    if raw[i] in (0x28, 0x6f):
                        tok = int.from_bytes(raw[i+1:i+5], 'little')
                        t_id = tok >> 24
                        r_id = tok & 0x00FFFFFF
                        try:
                            if t_id == 6: name = pe.net.mdtables.MethodDef[r_id-1].Name
                            elif t_id == 10: name = pe.net.mdtables.MemberRef[r_id-1].Name
                            else: name = f"tok_{hex(tok)}"
                            if any(k in name for k in ("Show", "Popup", "Dialog", "Ask", "Pick")):
                                print(f"  UI Call: {name}")
                        except: pass
