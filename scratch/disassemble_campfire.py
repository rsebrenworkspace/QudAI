import dnfile
import struct

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Helper to resolve signature
def parse_method_sig(blob):
    # blob is bytes
    call_conv = blob[0]
    param_count = blob[1]
    return f"call_conv: {hex(call_conv)}, param_count: {param_count}"

campfire_type = None
for row in pe.net.mdtables.TypeDef:
    if str(row.TypeName) == "Campfire" and str(row.TypeNamespace) == "XRL.World.Parts":
        campfire_type = row
        break

if campfire_type:
    # Inspect all methods of Campfire
    for m in campfire_type.MethodList:
        m_name = str(m.row.Name)
        if any(k in m_name for k in ["Cook", "Preserve", "ClearHunger"]):
            sig = parse_method_sig(m.row.Signature.value)
            print(f"Method: {m_name}, RVA: {hex(m.row.Rva)}, {sig}")
