import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Food":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name:
                print(f"Food Method: {m.row.Name}")
                rva = m.row.Rva
                if not rva: continue
                raw = dn.get_data(rva, 400)
                b0 = raw[0]
                code = raw[1:1 + (b0 >> 2)] if (b0 & 3) == 2 else raw[12:12+(raw[4]|(raw[5]<<8))]
                # look for ldstr or TypeRef
                for i in range(len(code) - 4):
                    if code[i] == 0x72:
                        tok = code[i+1] | (code[i+2] << 8) | (code[i+3] << 16) | (code[i+4] << 24)
                        print(f"  ldstr tok: 0x{tok:x}")
                    elif code[i] in (0x28, 0x6f):
                        tok = code[i+1] | (code[i+2] << 8) | (code[i+3] << 16) | (code[i+4] << 24)
                        table_id = tok >> 24
                        row_id = tok & 0xFFFFFF
                        name = ""
                        if table_id == 6:
                            name = dn.net.mdtables.MethodDef[row_id - 1].Name
                        elif table_id == 10:
                            name = dn.net.mdtables.MemberRef[row_id - 1].Name
                        print(f"  calls: {name}")
