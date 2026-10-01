import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def inspect_events(type_name):
    for t in dn.net.mdtables.TypeDef:
        if t.TypeName and type_name == str(t.TypeName):
            print(f"\n=== Events for {type_name} ===")
            for m in getattr(t, "MethodList", []):
                if m.row and "handleevent" in str(m.row.Name).lower():
                    # check signature
                    rva = m.row.Rva
                    raw = dn.get_data(rva, 300)
                    # print string tokens
                    for i in range(len(raw) - 4):
                        if raw[i] == 0x72:
                            tok = raw[i+1] | (raw[i+2] << 8) | (raw[i+3] << 16) | (raw[i+4] << 24)
                            # print token
                            print(f"  token in HandleEvent: 0x{tok:x}")

inspect_events("Food")
inspect_events("Butcherable")
