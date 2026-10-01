import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get("#US")
us_data = us.get_data() if us else b""

def get_us_string(token):
    idx = token & 0xFFFFFF
    if idx < len(us_data):
        b0 = us_data[idx]
        if b0 < 0x80:
            length = b0
            str_data = us_data[idx+1:idx+1+length-1]
        else:
            length = ((b0 & 0x3F) << 8) | us_data[idx+1]
            str_data = us_data[idx+2:idx+2+length-1]
        return str_data.decode("utf-16le", errors="ignore")
    return None

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Stomach":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name in ("FoodStatus", "WaterStatus", "IsFamished", "UpdateHunger"):
                print(f"\nMethod {m.row.Name}:")
                rva = m.row.Rva
                if not rva: continue
                raw_il = dn.get_data(rva, 500)
                for i in range(len(raw_il) - 4):
                    if raw_il[i] == 0x72: # ldstr
                        tok = raw_il[i+1] | (raw_il[i+2] << 8) | (raw_il[i+3] << 16) | (raw_il[i+4] << 24)
                        if (tok >> 24) == 0x70:
                            s = get_us_string(tok)
                            if s:
                                print(f"  ldstr: {repr(s)}")
