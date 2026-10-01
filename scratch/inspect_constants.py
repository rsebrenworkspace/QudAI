import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

# Check Constant table
if hasattr(dn.net.mdtables, "Constant"):
    for c in dn.net.mdtables.Constant:
        parent = c.Parent
        val = c.Value
        if isinstance(val, bytes):
            try:
                s = val.decode("utf-16le")
                if any(k in s.lower() for k in ["camp", "butcher", "cook", "stomach", "hungry", "famished"]):
                    print(f"Constant ({parent.table.name} #{parent.row_index}): {s}")
            except Exception:
                pass
