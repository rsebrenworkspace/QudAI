import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

def inspect_method(rva):
    first_byte = pe.get_data(rva, 1)[0]
    header_type = first_byte & 3
    if header_type == 2:
        code_size = first_byte >> 2
        header_size = 1
    elif header_type == 3:
        header_bytes = pe.get_data(rva, 12)
        flags = (header_bytes[1] << 8) | header_bytes[0]
        header_size = (flags >> 12) * 4
        code_size = int.from_bytes(header_bytes[4:8], 'little')
    else:
        return []
    
    code = pe.get_data(rva + header_size, code_size)
    return code

raw_clear = inspect_method(0x43431b) # ClearHunger
print("ClearHunger bytes:", [hex(b) for b in raw_clear])

# Look at UserStrings in CookPresetMeal
raw_preset = inspect_method(0x432d08)
for i in range(len(raw_preset) - 4):
    if raw_preset[i] == 0x72 and raw_preset[i+4] == 0x70:
        token = int.from_bytes(raw_preset[i+1:i+5], 'little')
        try:
            us_offset = token & 0x00FFFFFF
            us = pe.net.user_strings.get_us(us_offset)
            print("  Preset string:", us.value)
        except Exception:
            pass
