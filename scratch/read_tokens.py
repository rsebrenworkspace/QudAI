import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get("#US")
us_data = us.get_data() if us else b""

def get_str(offset):
    # offset in us_data
    b0 = us_data[offset]
    if b0 < 0x80:
        l = b0
        d = us_data[offset+1:offset+1+l-1]
    else:
        l = ((b0 & 0x3F) << 8) | us_data[offset+1]
        d = us_data[offset+2:offset+2+l-1]
    return d.decode("utf-16le", errors="ignore")

for tok in [0x0f29a8, 0x0f29c0, 0x0f29da, 0x0f29f6]:
    print(f"Token 0x{tok:x}: {repr(get_str(tok))}")
