with open(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll", "rb") as f:
    data = f.read()

needle = "CookWhipUp".encode("utf-16le")
idx = data.find(needle)
if idx != -1:
    start = max(0, idx - 500)
    end = min(len(data), idx + 800)
    snippet = data[start:end]
    # Decode utf-16 strings
    pos = 0
    while pos + 1 < len(snippet):
        if snippet[pos+1] == 0 and 32 <= snippet[pos] <= 126:
            s_start = pos
            while pos + 1 < len(snippet) and snippet[pos+1] == 0 and 32 <= snippet[pos] <= 126:
                pos += 2
            try:
                s = snippet[s_start:pos].decode("utf-16le")
                if len(s) >= 3:
                    print(f"UTF16 String: {s}")
            except Exception:
                pass
        else:
            pos += 1
