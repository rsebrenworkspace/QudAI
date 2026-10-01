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

raw = inspect_method(0x431bc4)
# Dump hex and opcodes around 0x170 to 0x1b5
print("=== Opcodes from 0x165 to 0x1b5 ===")
for offset in range(0x165, min(len(raw), 0x1c0)):
    b = raw[offset]
    print(f"{hex(offset)}: {hex(b)}")
