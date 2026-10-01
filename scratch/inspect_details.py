import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Read UserStrings stream to find COMMAND_NAME or string constants
us = dn.net.metadata.streams.get("#US")

def print_type_methods(type_name):
    for row in dn.net.mdtables.TypeDef:
        if row.TypeName == type_name:
            print(f"\n=== Methods for {row.TypeName} ===")
            for m in getattr(row, "MethodList", []):
                if m.row:
                    print(f"  {m.row.Name}")

print_type_methods("Survival_Camp")
print_type_methods("CookingAndGathering_Butchery")
print_type_methods("Campfire")
print_type_methods("Stomach")
