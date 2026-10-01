import dnfile

dn = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")
us = dn.net.metadata.streams.get("#US")
if us:
    data = us.get_data()
    # Find strings containing Camp or Butcher or Cook or Eat or Stomach
    for term in [b"Camp", b"Butcher", b"Harvest", b"Cook", b"Eat", b"Hunger", b"Famished"]:
        pos = 0
        matches = set()
        while True:
            idx = data.find(term, pos)
            if idx == -1: break
            # Each entry in #US is length-prefixed UTF-16LE
            # Scan backwards to null or length byte
            start = max(0, idx - 40)
            end = min(len(data), idx + 60)
            snippet = data[start:end]
            try:
                # find nulls or decode
                decoded = snippet.decode("utf-16le", errors="ignore")
                for line in decoded.split("\x00"):
                    if len(line) >= 3 and term.decode().lower() in line.lower():
                        matches.add(line)
            except Exception:
                pass
            pos = idx + len(term)
        print(f"\nTerm {term.decode()}: {len(matches)} matches")
        for m in sorted(matches)[:10]:
            print(f"  {repr(m)}")
