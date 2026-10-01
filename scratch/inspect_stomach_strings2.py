import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get("#US")
us_data = us.get_data() if us else b""

for t in dn.net.mdtables.TypeDef:
    if t.TypeName == "Stomach":
        for m in getattr(t, "MethodList", []):
            if m.row and m.row.Name in ("FoodStatus", "WaterStatus", "IsFamished", "UpdateHunger"):
                rva = m.row.Rva
                offset = dn.get_offset_from_rva(rva)
                raw = dn.get_data(rva, 600)
                # Check header format
                b0 = raw[0]
                if (b0 & 3) == 2: # tiny
                    code = raw[1:1 + (b0 >> 2)]
                elif (b0 & 3) == 3: # fat
                    size = raw[4] | (raw[5] << 8) | (raw[6] << 16) | (raw[7] << 24)
                    code = raw[12:12+size]
                else:
                    code = raw
                print(f"=== {m.row.Name} (size: {len(code)}) ===")
                # scan for ldstr (0x72)
                for i in range(len(code) - 4):
                    if code[i] == 0x72:
                        tok = code[i+1] | (code[i+2] << 8) | (code[i+3] << 16) | (code[i+4] << 24)
                        idx = tok & 0xFFFFFF
                        if idx < len(us_data):
                            lb = us_data[idx]
                            s_raw = us_data[idx+1:idx+1+lb-1] if lb < 0x80 else us_data[idx+2:idx+2+(((lb&0x3F)<<8)|us_data[idx+1])-1]
                            s = s_raw.decode("utf-16le", errors="ignore")
                            print(f"  ldstr: {repr(s)}")
