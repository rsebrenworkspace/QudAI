"""Builds data/creatures.json: every concrete creature blueprint the game defines, with the facts a fight or a plan needs, from the game's own data (BACKLOG B12, HANDOFF issue 81).

Needs the game installed. Run locally:
    python tools/build_creature_catalog.py [path to CoQ_Data]
The output holds creature names and numbers only (no game text, art or code) and is committed so tools and cloud agents can use it without the game. Re-run after a game update.

Static facts only. The live state.json (level, difficulty, hp, max_hp, is_stationary, has_los...) stays the truth for the creature in front of the character: heroes, mutated
creatures and legendaries differ from their blueprint (BACKLOG B12), and R3 forbids copying engine rules into Python. This catalog is a PRIOR for planning, reports and prompts.

How "a creature" is decided (AGENTS R1: engine data, not name guessing): the blueprint inherits from `Creature` (resolving `Inherits` across all ObjectBlueprints/*.xml, later
definitions overriding earlier ones, the same resolver as tools/build_item_catalog.py) and is concrete (not a base blueprint).
"""
import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_item_catalog as bic  # noqa: E402  (sanitize, load_blueprints, Catalog, clean_name, num)

DEFAULT_DATA = bic.DEFAULT_DATA
STATS = ("Level", "Hitpoints", "AV", "DV", "MA", "Speed", "MoveSpeed", "Strength", "Agility", "Toughness", "Intelligence", "Willpower", "Ego",
         "HeatResistance", "ColdResistance", "AcidResistance", "ElectricResistance")
# Parts and tags worth a flag; the full part list is not kept (it is mostly rendering and bookkeeping).
FLAG_PARTS = {"Swarmer": "swarmer", "AIShootAndScoot": "shoot_and_scoot", "AISelfPreservation": "self_preserving", "MentalShield": "mental_shield", "Plant": "plant", "Fungus": "fungus",
              "Robot": "robot", "GivesRep": "gives_rep", "RandomMutations": "random_mutations", "Pettable": "pettable", "Raycat": "raycat", "Interesting": "interesting",
              "HasGuards": "has_guards", "GenericInventoryRestocker": "restocks"}
# Left out on purpose: ConversationScript and Springy are on almost every creature (a default), so a flag for them says nothing.
FLAG_TAGS = {"Turret": "turret", "TinkerTurret": "tinker_turret", "VillagePet": "village_pet", "Immobile": "immobile", "Noswap": "noswap", "HeroNameTitleWiseDescriptor": "hero_capable"}


LIKELY_HOSTILE_REP = -250      # the engine's "disliked" threshold (RuleSettings.REPUTATION_DISLIKED); a starting reputation at or below it is read as hostile on sight [inferred]


def faction_start_reputation(folder):
    """{faction: InitialPlayerReputation} from Factions.xml (the player's starting standing with each faction)."""
    import xml.etree.ElementTree as ET
    path = os.path.join(os.path.dirname(folder), "Factions.xml")
    out = {}
    try:
        root = ET.fromstring(bic.sanitize(open(path, encoding="utf-8-sig", errors="replace").read()))
    except (OSError, ET.ParseError):
        return out
    for f in root.iter("faction"):
        if f.get("Name") and f.get("InitialPlayerReputation") is not None:
            out[f.get("Name")] = bic.num(f.get("InitialPlayerReputation"))
    return out


def start_reputation(factions_attr, rep_by_faction):
    """The lowest starting reputation among the creature's factions ("Snapjaws-100,Humanoids-50"), or None when none of them defines one."""
    vals = []
    for part in (factions_attr or "").split(","):
        name = part.strip().rsplit("-", 1)[0] if "-" in part else part.strip()
        if name in rep_by_faction and rep_by_faction[name] is not None:
            vals.append(rep_by_faction[name])
    return min(vals) if vals else None


def stat_table(cat, name):
    """Merged <stat> definitions along the inheritance chain: {stat: {Value, sValue, Boost}} with later definitions overriding per attribute."""
    merged = {}
    for b in cat.chain(name):
        for s in cat.raw[b][0].findall("stat"):
            n = s.get("Name")
            if n in STATS:
                cur = merged.setdefault(n, {})
                if "sValue" in s.attrib:
                    cur.pop("Value", None)          # a later formula replaces an inherited fixed value (and the other way round)
                if "Value" in s.attrib:
                    cur.pop("sValue", None)
                cur.update({k: v for k, v in s.attrib.items() if k in ("Value", "sValue", "Boost")})
    return merged


def number_or_range(stat):
    """(low, high) from a stat definition: a fixed Value, or an sValue that is a number or an 'a-b' range; (None, None) for a dice or tier formula."""
    if not stat:
        return None, None
    v = stat.get("Value")
    if v is not None:
        n = bic.num(v)
        return n, n
    s = (stat.get("sValue") or "").strip()
    import re as _re
    m = _re.fullmatch(r"(\d+)(?:-(\d+))?", s)
    if m:
        lo = int(m.group(1))
        return lo, int(m.group(2) or lo)
    return None, None


def weapons(cat, name):
    """The creature's carried weapons by role: natural melee (name, damage, count) and ranged (name). Inventory objects along the whole chain."""
    natural, ranged = {}, {}
    for b in cat.chain(name):
        for rm in cat.raw[b][0].findall("removeinventoryobject"):      # e.g. a defanged girshling has no bite
            natural.pop(rm.get("Blueprint"), None)
            ranged.pop(rm.get("Blueprint"), None)
        for io in cat.raw[b][0].findall("inventoryobject"):
            bp = io.get("Blueprint")
            if not bp or bp not in cat.raw:
                continue
            chain = cat.chain(bp)
            parts = cat.parts(bp)
            n = io.get("Number") or "1"
            if "NaturalWeapon" in chain:
                natural[bp] = {"name": bp, "damage": (parts.get("MeleeWeapon") or {}).get("BaseDamage"), "skill": (parts.get("MeleeWeapon") or {}).get("Skill"), "count": n}
            elif "MissileWeapon" in chain or "MissileWeapon" in parts:
                ranged[bp] = bp
    return list(natural.values()), list(ranged.values())


def build_entry(cat, name, reps=None):
    parts = cat.parts(name)
    tags = cat.tags(name)
    st = stat_table(cat, name)
    brain = parts.get("Brain", {})
    natural, ranged = weapons(cat, name)
    render = parts.get("Render", {})
    level, level_max = number_or_range(st.get("Level"))
    hp, hp_max = number_or_range(st.get("Hitpoints"))
    flags = sorted({v for k, v in FLAG_PARTS.items() if k in parts} | {v for k, v in FLAG_TAGS.items() if k in tags})
    rooted = brain.get("Mobile") == "false" or brain.get("LivesOnWalls") == "true" or "plant" in flags or "fungus" in flags or "turret" in flags
    entry = {
        "name": bic.clean_name(render.get("DisplayName")) or name, "file": cat.raw[name][1], "tier": bic.num(tags.get("Tier")), "level": level, "level_max": level_max if level_max != level else None, "hp": hp,
        "hp_max": hp_max if hp_max != hp else None, "level_formula": (st.get("Level") or {}).get("sValue") if level is None else None,
        "hp_formula": (st.get("Hitpoints") or {}).get("sValue") if hp is None else None,
        "stats": {k: v for k, v in st.items() if k not in ("Level", "Hitpoints")},
        "start_rep": start_reputation(brain.get("Factions"), reps or {}), "wanders": brain.get("Wanders") != "false", "rooted": rooted, "factions": brain.get("Factions"),
        "species": tags.get("Species"), "role": tags.get("Role"), "anatomy": parts.get("Body", {}).get("Anatomy"),
        "melee": natural[:4], "ranged": ranged[:3], "is_ranged": bool(ranged) or "shoot_and_scoot" in flags,
        "mutations": sorted({m.get("Name") for b in cat.chain(name) for m in cat.raw[b][0].findall("mutation") if m.get("Name")}),
        "skills": sorted({s.get("Name") for b in cat.chain(name) for s in cat.raw[b][0].findall("skill") if s.get("Name")}),
        "flags": flags, "has_ma": "MA" in st,
    }
    sr = entry.get("start_rep")
    entry["likely_hostile"] = sr is not None and sr <= LIKELY_HOSTILE_REP
    return {k: v for k, v in entry.items() if v not in (None, [], {}, "")} | {"likely_hostile": entry["likely_hostile"], "rooted": rooted, "is_ranged": entry["is_ranged"]}


def main():
    data = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA
    folder = os.path.join(data, "StreamingAssets", "Base", "ObjectBlueprints")
    raw = bic.load_blueprints(folder)
    cat = bic.Catalog(raw)
    reps = faction_start_reputation(folder)
    out = {}
    for name in raw:
        chain = cat.chain(name)
        if "Creature" not in chain or cat.is_abstract(name):
            continue
        out[name] = build_entry(cat, name, reps)
    by_level = collections.Counter((e.get("level") or 0) // 5 * 5 for e in out.values())
    doc = {"meta": {"built": datetime.date.today().isoformat(), "source": "StreamingAssets/Base/ObjectBlueprints/*.xml", "creatures": len(out),
                    "with_level": sum(1 for e in out.values() if e.get("level") is not None), "with_hp": sum(1 for e in out.values() if e.get("hp") is not None),
                    "level_by_formula": sum(1 for e in out.values() if e.get("level") is None),
                    "ranged": sum(1 for e in out.values() if e["is_ranged"]), "rooted": sum(1 for e in out.values() if e["rooted"]),
                    "likely_hostile": sum(1 for e in out.values() if e["likely_hostile"]),
                    "level_bands": {f"{k}-{k + 4}": v for k, v in sorted(by_level.items())}},
           "creatures": out}
    target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "creatures.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    print(f"wrote {target}: {len(out)} creatures; {doc['meta']['with_level']} with a level, {doc['meta']['ranged']} ranged, {doc['meta']['rooted']} rooted")


if __name__ == "__main__":
    main()
