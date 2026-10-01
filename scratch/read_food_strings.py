import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get(b"#US")
us_data = us.data if us else b""

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Food":
        for m in getattr(t, "MethodList", []):
            if not m.row: continue
            rva = m.row.Rva
            if not rva: continue
            raw = dn.get_data(rva, 600)
            print(f"--- Method {m.row.Name} (RVA: {hex(rva)}) ---")
            for i in range(len(raw) - 4):
                if raw[i] == 0x72:
                    tok = raw[i+1] | (raw[i+2] << 8) | (raw[i+3] << 16) | (raw[i+4] << 24)
                    idx = tok & 0xFFFFFF
                    if idx < len(us_data):
                        s_end = idx
                        while s_end + 1 < len(us_data) and not (us_data[s_end] == 0 and us_data[s_end+1] == 0):
                            s_end += 2
                        try:
                            s = us_data[idx:s_end].decode("utf-16le", errors="ignore")
                            clean = "".join(c for c in s if 32 <= ord(c) <= 126)
                            if len(clean) >= 2:
                                print(f"    0x{tok:x}: {repr(clean)}")
                        except Exception:
                            pass
