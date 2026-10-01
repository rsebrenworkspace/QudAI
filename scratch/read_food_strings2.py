import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get(b"#US")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Food":
        for m in getattr(t, "MethodList", []):
            if not m.row: continue
            rva = m.row.Rva
            if not rva: continue
            raw = dn.get_data(rva, 600)
            print(f"--- Method {m.row.Name} ---")
            for i in range(len(raw) - 4):
                if raw[i] == 0x72:
                    tok = raw[i+1] | (raw[i+2] << 8) | (raw[i+3] << 16) | (raw[i+4] << 24)
                    s = us.get(tok & 0xFFFFFF)
                    if s:
                        print(f"  ldstr: {repr(s)}")
