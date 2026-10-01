import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Find Campfire type
campfire_type = None
for row in pe.net.mdtables.TypeDef:
    if str(row.TypeName) == "Campfire" and str(row.TypeNamespace) == "XRL.World.Parts":
        campfire_type = row
        break

if campfire_type:
    for m in campfire_type.MethodList:
        print(f"Method: {m.row.Name}")
        # Let's inspect parameters
        for p in getattr(m, 'ParamList', []):
            try:
                print(f"  Param: {p.row.Name}")
            except:
                pass
