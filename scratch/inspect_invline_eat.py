import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for t in dn.net.mdtables.TypeDef:
    if t.TypeName and "InventoryLine" == str(t.TypeName):
        for m in getattr(t, "MethodList", []):
            if m.row and "HandleQuickEat" in str(m.row.Name):
                rva = m.row.Rva
                raw = dn.get_data(rva, 300)
                print(f"InventoryLine.HandleQuickEat calls:")
                for i in range(len(raw) - 4):
                    if raw[i] in (0x28, 0x6f):
                        tok = raw[i+1] | (raw[i+2] << 8) | (raw[i+3] << 16) | (raw[i+4] << 24)
                        table_id = tok >> 24
                        row_id = tok & 0xFFFFFF
                        name = ""
                        if table_id == 6:
                            name = dn.net.mdtables.MethodDef[row_id - 1].Name
                        elif table_id == 10:
                            name = dn.net.mdtables.MemberRef[row_id - 1].Name
                        print(f"  {name}")
