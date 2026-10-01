import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get("#US")
us_data = us.get_data() if us else b""

def get_str(tok):
    idx = tok & 0xFFFFFF
    if idx < len(us_data):
        b0 = us_data[idx]
        l = b0 if b0 < 0x80 else (((b0 & 0x3F) << 8) | us_data[idx+1])
        start = idx + (1 if b0 < 0x80 else 2)
        return us_data[start:start+l-1].decode("utf-16le", errors="ignore")
    return ""

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Food":
        for m in getattr(t, "MethodList", []):
            if m.row and "handleevent" in str(m.row.Name).lower():
                rva = m.row.Rva
                if not rva: continue
                raw = dn.get_data(rva, 600)
                b0 = raw[0]
                code = raw[1:1 + (b0 >> 2)] if (b0 & 3) == 2 else raw[12:12+(raw[4]|(raw[5]<<8))]
                print(f"\nFood.{m.row.Name} strings:")
                for i in range(len(code) - 4):
                    if code[i] == 0x72:
                        tok = code[i+1] | (code[i+2] << 8) | (code[i+3] << 16) | (code[i+4] << 24)
                        s = get_str(tok)
                        if s: print(f"  {repr(s)}")
