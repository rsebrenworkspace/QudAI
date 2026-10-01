import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

token = 0x04004a55
row_id = token & 0x00FFFFFF
field = pe.net.mdtables.Field[row_id - 1]
print(f"Field name: {field.Name}")

for tok in [0x04004a54, 0x04004a55, 0x04004a56, 0x04004a57]:
    rid = tok & 0x00FFFFFF
    f = pe.net.mdtables.Field[rid - 1]
    print(f"Field {hex(tok)}: {f.Name}")
