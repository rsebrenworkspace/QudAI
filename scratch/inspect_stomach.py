import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Find Stomach
for row in pe.net.mdtables.TypeDef:
    if str(row.TypeName) == "Stomach" and str(row.TypeNamespace) == "XRL.World.Parts":
        print("Found Stomach:")
        for m in getattr(row, 'MethodList', []):
            try:
                print(f"  Method: {m.row.Name}")
            except:
                pass
