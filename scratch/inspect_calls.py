import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def find_method_calls(class_name, method_name):
    for t in dn.net.mdtables.TypeDef:
        if t.TypeName and class_name in str(t.TypeName):
            for m in getattr(t, "MethodList", []):
                if m.row and m.row.Name and method_name == str(m.row.Name):
                    print(f"\nCalls inside {t.TypeNamespace}.{t.TypeName}.{m.row.Name}:")
                    rva = m.row.Rva
                    raw = dn.get_data(rva, 600)
                    b0 = raw[0]
                    code = raw[1:1 + (b0 >> 2)] if (b0 & 3) == 2 else raw[12:12+(raw[4]|(raw[5]<<8))]
                    # scan for call (0x28) or callvirt (0x6f)
                    for i in range(len(code) - 4):
                        if code[i] in (0x28, 0x6f):
                            tok = code[i+1] | (code[i+2] << 8) | (code[i+3] << 16) | (code[i+4] << 24)
                            table_id = tok >> 24
                            row_id = tok & 0xFFFFFF
                            if table_id == 6: # MethodDef
                                target_m = dn.net.mdtables.MethodDef[row_id - 1]
                                print(f"  calls MethodDef: {target_m.Name}")
                            elif table_id == 10: # MemberRef
                                target_m = dn.net.mdtables.MemberRef[row_id - 1]
                                print(f"  calls MemberRef: {target_m.Name}")

find_method_calls("InventoryAndEquipmentStatusScreen", "HandleQuickEat")
find_method_calls("Butcherable", "AttemptButcher")
find_method_calls("Harvestable", "AttemptHarvest")
find_method_calls("Survival_Camp", "AttemptCamp")
