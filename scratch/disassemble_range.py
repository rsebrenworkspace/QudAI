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

# We want to see instructions between 0x160 and 0x220
# Simple CIL decoder for common opcodes
opcodes = {
    0x00: ("nop", 0), 0x02: ("ldarg.0", 0), 0x03: ("ldarg.1", 0), 0x04: ("ldarg.2", 0),
    0x06: ("ldloc.0", 0), 0x07: ("ldloc.1", 0), 0x08: ("ldloc.2", 0), 0x09: ("ldloc.3", 0),
    0x0a: ("stloc.0", 0), 0x0b: ("stloc.1", 0), 0x0c: ("stloc.2", 0), 0x0d: ("stloc.3", 0),
    0x11: ("ldloc.s", 1), 0x13: ("stloc.s", 1), 0x14: ("ldnull", 0),
    0x15: ("ldc.i4.m1", 0), 0x16: ("ldc.i4.0", 0), 0x17: ("ldc.i4.1", 0), 0x18: ("ldc.i4.2", 0),
    0x19: ("ldc.i4.3", 0), 0x1a: ("ldc.i4.4", 0), 0x1b: ("ldc.i4.5", 0), 0x1c: ("ldc.i4.6", 0),
    0x1f: ("ldc.i4.s", 1), 0x20: ("ldc.i4", 4),
    0x25: ("dup", 0), 0x26: ("pop", 0), 0x28: ("call", 4), 0x2a: ("ret", 0),
    0x2b: ("br.s", 1), 0x2c: ("brfalse.s", 1), 0x2d: ("brtrue.s", 1), 0x2e: ("beq.s", 1),
    0x2f: ("bge.s", 1), 0x30: ("bgt.s", 1), 0x31: ("ble.s", 1), 0x32: ("blt.s", 1),
    0x38: ("br", 4), 0x39: ("brfalse", 4), 0x3a: ("brtrue", 4),
    0x6f: ("callvirt", 4), 0x72: ("ldstr", 4), 0x7e: ("ldsfld", 4), 0x80: ("stsfld", 4)
}

i = 0x160
while i < 0x230 and i < len(raw):
    op = raw[i]
    if op in opcodes:
        name, arglen = opcodes[op]
        arg_bytes = raw[i+1:i+1+arglen]
        arg_str = ""
        if name == "ldstr":
            tok = int.from_bytes(arg_bytes, 'little') & 0x00FFFFFF
            try:
                arg_str = f"'{pe.net.user_strings.get(tok)}'"
            except:
                pass
        elif name in ("call", "callvirt"):
            tok = int.from_bytes(arg_bytes, 'little')
            t_id = tok >> 24
            r_id = tok & 0x00FFFFFF
            try:
                if t_id == 6: arg_str = pe.net.mdtables.MethodDef[r_id-1].Name
                elif t_id == 10: arg_str = pe.net.mdtables.MemberRef[r_id-1].Name
                else: arg_str = f"tok_{hex(tok)}"
            except:
                arg_str = f"tok_{hex(tok)}"
        elif arglen > 0:
            arg_str = hex(int.from_bytes(arg_bytes, 'little'))
        print(f"{hex(i)}: {name} {arg_str}")
        i += 1 + arglen
    else:
        print(f"{hex(i)}: db {hex(op)}")
        i += 1
