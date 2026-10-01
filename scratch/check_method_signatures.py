import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def check_params(class_name, method_name):
    for t in dn.net.mdtables.TypeDef:
        if t.TypeName == class_name:
            for m in getattr(t, "MethodList", []):
                if m.row and m.row.Name == method_name:
                    p_names = [p.row.Name for p in getattr(m.row, "ParamList", []) if p.row]
                    print(f"{class_name}.{method_name} params: {p_names}")

check_params("Survival_Camp", "AttemptCamp")
check_params("Campfire", "Cook")
check_params("Campfire", "PerformPreserve")
check_params("Butcherable", "AttemptButcher")
check_params("Harvestable", "AttemptHarvest")
