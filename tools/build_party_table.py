"""Builds data/parties.json: how many of each creature a game "party" table spawns together (BACKLOG B12 stage 4 start, HANDOFF issue 84).

Source: StreamingAssets/Base/PopulationTables.xml. A party table (BaboonParty, SnapjawParty1, ...) lists members with a Chance and a Number;
this expands nested tables and writes the EXPECTED count per blueprint, so the threat score can ask "how many of these arrive together".
Expected counts are an average, not a roll: a 'pickeach' member adds chance * average(number); a 'pickone' group splits by weight.
Usage: python tools/build_party_table.py [path to CoQ_Data]
"""
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

DEFAULT_DATA = r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data"
MAX_DEPTH = 4


def number_average(text):
    """Average of '3-4', '1d4', '3d6+1', '2'; 1 when absent or unreadable."""
    s = (text or "").strip()
    if not s:
        return 1.0
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2.0
    m = re.fullmatch(r"(\d+)d(\d+)\s*([+-]\s*\d+)?", s)
    if m:
        bonus = int(m.group(3).replace(" ", "")) if m.group(3) else 0
        return int(m.group(1)) * (int(m.group(2)) + 1) / 2.0 + bonus
    try:
        return float(s)
    except ValueError:
        return 1.0


def chance_fraction(node):
    """Chance='25' -> 0.25; the engine also writes '10,3' (probably chance,tier), only the first number is read here."""
    s = node.get("Chance")
    if not s:
        return 1.0
    m = re.match(r"\s*([\d.]+)", s)
    return min(1.0, float(m.group(1)) / 100.0) if m else 1.0


def weight(node):
    try:
        return float(node.get("Weight") or 1)
    except ValueError:
        return 1.0


def expand(container, tables, stack, depth):
    """{blueprint: expected count} for one population or group element."""
    out = {}
    style = (container.get("Style") or "pickone").lower()
    kids = [c for c in container if c.tag in ("object", "group", "table")]
    total_w = sum(weight(c) for c in kids) or 1.0
    for c in kids:
        factor = chance_fraction(c) * number_average(c.get("Number"))
        if style == "pickone":
            factor *= weight(c) / total_w
        if c.tag == "object":
            bp = c.get("Blueprint")
            if bp:
                out[bp] = out.get(bp, 0.0) + factor
        elif c.tag == "group":
            sub = expand(c, tables, stack, depth + 1)
            for bp, n in sub.items():
                out[bp] = out.get(bp, 0.0) + factor * n
        else:
            name = c.get("Name")
            if name in tables and name not in stack and depth < MAX_DEPTH:
                sub = expand(tables[name], tables, stack | {name}, depth + 1)
                for bp, n in sub.items():
                    out[bp] = out.get(bp, 0.0) + factor * n
    return out


def build(path):
    root = ET.parse(path).getroot()
    tables = {p.get("Name"): p for p in root.iter("population") if p.get("Name")}
    parties = {}
    for name, node in tables.items():
        if "Party" not in name:
            continue
        members = expand(node, tables, {name}, 0)
        members = {bp: round(n, 2) for bp, n in members.items() if n > 0}
        if members:
            parties[name] = {"members": members, "expected_total": round(sum(members.values()), 2)}
    return parties


def main():
    data = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA
    path = os.path.join(data, "StreamingAssets", "Base", "PopulationTables.xml")
    parties = build(path)
    by_creature = {}
    for pname, p in parties.items():
        for bp, n in p["members"].items():
            by_creature.setdefault(bp, {})[pname] = n
    doc = {"meta": {"built": datetime.date.today().isoformat(), "source": "StreamingAssets/Base/PopulationTables.xml", "parties": len(parties),
                    "note": "expected counts (averages), nested tables expanded to depth %d; a group without Style is read as pickone [unverified]" % MAX_DEPTH},
           "parties": parties, "by_creature": by_creature}
    target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "parties.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    print(f"{len(parties)} party tables -> {target}")


if __name__ == "__main__":
    main()
