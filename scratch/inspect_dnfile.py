import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

target_types = ["Stomach", "Campfire", "Survival_Camp", "CookingAndGathering_Butchery", "CookingAndGathering_Harvestry", "CookingAndGathering_MealPreparation", "Food", "Corpse"]

for row in dn.net.mdtables.TypeDef:
    name = row.TypeName
    namespace = row.TypeNamespace
    if any(name == t for t in target_types):
        print(f"\n==========================================")
        print(f"TYPE: {namespace}.{name}")
        # Print fields
        print("  FIELDS:")
        for f in getattr(row, "FieldList", []):
            if f.row:
                print(f"    {f.row.Name}")
        # Print methods
        print("  METHODS:")
        for m in getattr(row, "MethodList", []):
            if m.row:
                print(f"    {m.row.Name}")
