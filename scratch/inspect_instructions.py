import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def inspect_class(class_name):
    for type_def in dn.net.mdtables.TypeDef:
        if type_def.TypeName == class_name:
            print(f"\n================ {type_def.TypeNamespace}.{type_def.TypeName} ================")
            for m in getattr(type_def, "MethodList", []):
                if not m.row: continue
                name = m.row.Name
                print(f"--- Method: {name} ---")
                # Look for strings in method instructions if possible
                try:
                    body = dn.net.metadata.get_method_body(m.row.RVA)
                    if body and hasattr(body, "instructions"):
                        for inst in body.instructions:
                            if inst.mnemonic in ("ldstr", "call", "callvirt"):
                                val = inst.operand
                                # If string
                                if inst.mnemonic == "ldstr" and isinstance(val, str):
                                    print(f"    ldstr \"{val}\"")
                                elif hasattr(val, "row") and hasattr(val.row, "Name"):
                                    print(f"    {inst.mnemonic} {val.row.Name}")
                except Exception as ex:
                    pass

inspect_class("Survival_Camp")
inspect_class("CookingAndGathering_Butchery")
inspect_class("Stomach")
