"""Builds data/items.json: every item blueprint the game defines, with the stats a scorer needs, from the game's own data (HANDOFF issue 66).

Needs the game installed. Run locally:
    python tools/build_item_catalog.py [path to CoQ_Data]
The output holds item names and numbers only (no game text, art or code) and is committed so tools and cloud agents can use it without the game.
Re-run after a game update.

How "an item" is decided (AGENTS R1: engine data, not name guessing):
  * the blueprint inherits from `Item` (resolving `Inherits` across all ObjectBlueprints/*.xml, later parts overriding earlier ones);
  * it is concrete: not a base blueprint (name starting "Base" or "*", or an own `BaseObject` tag);
  * "loot" additionally means: defined in Items.xml or Foods.xml, takeable, not a projectile, not a creature's natural weapon.
Every concrete item inherits a default improvised `MeleeWeapon` part from `Item`, so a real weapon is recognised by its ANCESTRY (`MeleeWeapon`,
`MissileWeapon`, `Armor`, `Shield`, `Grenade`...), never by that part alone.
"""
import collections
import datetime
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

DEFAULT_DATA = r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data"
LOOT_FILES = {"Items.xml", "Foods.xml"}
# Parts whose attributes a scorer may want (kept verbatim as strings).
KEEP_PARTS = ["Armor", "Shield", "MissileWeapon", "ThrownWeapon", "EquipStatBoost", "CyberneticsBaseItem", "CyberneticsStatModifier", "Food", "Tonic",
              "Medication", "LightSource", "EnergyCell", "ElementalDamage", "Book", "DataDisk", "Cookbook", "ModImprovedMutationLevel", "MentalShield",
              "ArmorModifier", "MoveSpeedModifier", "HeatResistanceModifier", "ColdResistanceModifier"]


def sanitize(text):
    """The game's XML contains invalid character references; drop them so a strict parser accepts the file."""
    def ok(m):
        code = int(m.group(1), 16) if m.group(1) else int(m.group(2))
        return m.group(0) if (code in (9, 10, 13) or 32 <= code <= 0xD7FF or 0xE000 <= code <= 0xFFFD or 0x10000 <= code <= 0x10FFFF) else ""
    return re.sub(r"&#(?:x([0-9a-fA-F]+)|(\d+));", ok, text)


def load_blueprints(folder):
    raw = {}
    for f in sorted(glob.glob(os.path.join(folder, "*.xml"))):
        txt = sanitize(open(f, encoding="utf-8-sig", errors="replace").read())
        root = ET.fromstring(txt)
        for o in root.iter("object"):
            n = o.get("Name")
            if n:
                raw[n] = (o, os.path.basename(f))
    return raw


def clean_name(s):
    """'{{w|bronze}} dagger' -> 'bronze dagger'; '&Yred^k' colour codes removed."""
    s = re.sub(r"\{\{[^|}]*\|", "", s or "")
    s = s.replace("}}", "")
    s = re.sub(r"[&^][a-zA-Z]", "", s)
    return s.strip()


class Catalog:
    def __init__(self, raw):
        self.raw = raw
        self._chain = {}

    def chain(self, name):
        if name in self._chain:
            return self._chain[name]
        out, cur = [], name
        while cur and cur in self.raw and cur not in out:
            out.append(cur)
            cur = self.raw[cur][0].get("Inherits")
        out.reverse()
        self._chain[name] = out
        return out

    def parts(self, name):
        merged = {}
        for b in self.chain(name):
            for p in self.raw[b][0].findall("part"):
                merged.setdefault(p.get("Name"), {}).update({k: v for k, v in p.attrib.items() if k != "Name"})
        return merged

    def tags(self, name):
        tags = {}
        chain = self.chain(name)
        for b in chain:
            for t in self.raw[b][0].findall("tag"):
                if t.get("Value") == "*noinherit" and b != name:
                    continue
                tags[t.get("Name")] = t.get("Value")
        return tags

    def own_tags(self, name):
        return {t.get("Name"): t.get("Value") for t in self.raw[name][0].findall("tag")}

    def is_abstract(self, name):
        return name.startswith("Base") or name.startswith("*") or "BaseObject" in self.own_tags(name)


CATEGORY_GROUP = {"Tonics": "tonic", "Meds": "medication", "Applicators": "applicator", "Artifacts": "artifact", "Light Sources": "light_source",
                  "Water Containers": "water_container", "Trade Goods": "trade_good", "Quest Items": "quest_item", "Tools": "tool", "Trinkets": "trinket",
                  "Thrown Weapons": "thrown_weapon", "Energy Cells": "power_cell", "Corpses": "corpse", "Scrap": "scrap", "Books": "book",
                  "Data Disks": "data_disk", "Food": "food", "Clothes": "clothes", "Cybernetic Implants": "cybernetics", "Shields": "shield"}


def group_of(chain, parts, tags, category=""):
    anc = set(chain)
    if "CyberneticsBaseItem" in parts:
        return "cybernetics"
    if "Armor" in anc or ("Armor" in parts and parts["Armor"].get("WornOn")):
        return "armor"
    if "Shield" in anc or "Shield" in parts:
        return "shield"
    if "MissileWeapon" in anc:
        return "missile_weapon"
    if "MeleeWeapon" in anc:
        return "melee_weapon"
    if "Grenade" in anc:
        return "grenade"
    if category in CATEGORY_GROUP:
        return CATEGORY_GROUP[category]
    if "Ammo" in tags or any(p.startswith("Ammo") for p in parts):
        return "ammo"
    if "EnergyCell" in parts:
        return "power_cell"
    if "Tonic" in parts:
        return "tonic"
    if "Medication" in parts:
        return "medication"
    if "Food" in parts:
        return "food"
    if "Book" in parts or "Cookbook" in parts:
        return "book"
    if "DataDisk" in parts:
        return "data_disk"
    if "Scrap" in anc:
        return "scrap"
    if "Corpse" in anc:
        return "corpse"
    if "LightSource" in parts:
        return "light_source"
    return "other"


# Parts that make an item matter beyond its stats: faction reputation trophies (`AddsRep`), quest items, faction deeds, Sultanate relics.
PROTECT_PARTS = {"AddsRep": "reputation", "CompleteQuestOnTaken": "quest", "QuestStepFinisher": "quest", "QuestStarter": "quest", "FactionDeed": "faction",
                 "SultanMask": "relic"}


def protect_reasons(parts):
    out = sorted({why for p, why in PROTECT_PARTS.items() if p in parts})
    if "AddsRep" in parts and parts["AddsRep"].get("Faction"):
        out = [f"reputation:{parts['AddsRep']['Faction']}" if w == "reputation" else w for w in out]
    return out


def num(v, default=None):
    try:
        return float(v) if "." in str(v) else int(v)
    except (TypeError, ValueError):
        return default


def build_entry(cat, name):
    parts, tags, chain = cat.parts(name), cat.tags(name), cat.chain(name)
    file = cat.raw[name][1]
    phys = parts.get("Physics", {})
    grp = group_of(chain, parts, tags, phys.get("Category", ""))
    natural = "NaturalWeapon" in chain or "NaturalEquipment" in parts
    projectile = "Projectile" in chain
    takeable = str(phys.get("Takeable", "true")).lower() != "false"
    loot = (file in LOOT_FILES) and takeable and not natural and not projectile
    e = {"name": clean_name(parts.get("Render", {}).get("DisplayName") or name), "group": grp, "category": phys.get("Category", ""), "file": file,
         "tier": num(tags.get("Tier")), "weight": num(phys.get("Weight"), 0), "value": num(parts.get("Commerce", {}).get("Value")),
         "loot": loot, "natural": natural, "projectile": projectile, "takeable": takeable,
         "rare": any(k.startswith("StaticObjectsTable:") for k in tags),      # placed unique items (quest rewards, story artifacts), not random loot
         "escape": any("Teleport" in p for p in parts)}                        # recoilers and other teleporting gear: how the character gets out of trouble
    why = protect_reasons(parts)
    if why:
        e["protect"] = why
    if "DiggingTool" in parts:
        e["digger"] = True                                                  # the engine marks digging tools with this part (Pickaxe, Nanopneumatic Jackhammer): they cut through rock
    if grp in ("armor", "shield"):
        a = parts.get("Armor") or parts.get("Shield") or {}
        e.update({"slot": a.get("WornOn", ""), "av": num(a.get("AV"), 0), "dv": num(a.get("DV"), 0), "ma": num(a.get("MA")), "armor_attrs": a})
    if grp == "melee_weapon" or (grp in ("armor", "shield") and False):
        m = parts.get("MeleeWeapon", {})
        e.update({"damage": m.get("BaseDamage"), "skill": m.get("Skill"), "stat": m.get("Stat"), "pen": num(m.get("PenBonus"), 0), "hit": num(m.get("HitBonus"), 0),
                  "two_handed": str(phys.get("UsesTwoSlots", "false")).lower() == "true", "melee_attrs": m})
    if grp == "missile_weapon":
        w = parts.get("MissileWeapon", {})
        e.update({"skill": w.get("Skill"), "ammo_char": w.get("AmmoChar"), "accuracy": num(w.get("WeaponAccuracy")), "range": num(w.get("RangeIncrement")),
                  "shots": num(w.get("ShotsPerAction")), "two_handed": str(phys.get("UsesTwoSlots", "false")).lower() == "true", "missile_attrs": w})
        m = parts.get("MeleeWeapon", {})
    extras = {p: parts[p] for p in KEEP_PARTS if p in parts and p not in ("Armor", "Shield", "MissileWeapon")}
    if extras:
        e["parts"] = extras
    mods = tags.get("Mods")
    if mods:
        e["mods"] = mods
    return e


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA
    folder = os.path.join(data_dir, "StreamingAssets", "Base", "ObjectBlueprints")
    raw = load_blueprints(folder)
    cat = Catalog(raw)
    items_all = [n for n in raw if "Item" in cat.chain(n)]
    concrete = [n for n in items_all if not cat.is_abstract(n)]
    out = {}
    for n in concrete:
        out[n] = build_entry(cat, n)
    loot = {k: v for k, v in out.items() if v["loot"]}
    by_group = collections.Counter(v["group"] for v in loot.values())
    by_cat = collections.Counter(v["category"] or "(none)" for v in loot.values())
    by_tier = collections.Counter(str(v["tier"]) for v in loot.values())
    by_file = collections.Counter(v["file"] for v in out.values())
    meta = {
        "generated": datetime.date.today().isoformat(),
        "source": "StreamingAssets/Base/ObjectBlueprints/*.xml",
        "counts": {"blueprints_total": len(raw), "inherit_item": len(items_all), "abstract_bases": len(items_all) - len(concrete), "concrete_items": len(concrete),
                   "loot_items": len(loot), "natural_weapons": sum(1 for v in out.values() if v["natural"]), "projectiles": sum(1 for v in out.values() if v["projectile"]),
                   "not_takeable": sum(1 for v in out.values() if not v["takeable"])},
        "rare_loot_items": sum(1 for v in loot.values() if v["rare"]),
        "escape_loot_items": sum(1 for v in loot.values() if v["escape"]),
        "protected_loot_items": sum(1 for v in loot.values() if v.get("protect")),
        "loot_by_group": dict(by_group.most_common()),
        "loot_by_physics_category": dict(by_cat.most_common()),
        "loot_by_tier": dict(sorted(by_tier.items())),
        "concrete_by_file": dict(by_file.most_common()),
        "definition": "loot = concrete item blueprint in Items.xml or Foods.xml that is takeable, not a projectile, not a creature's natural weapon",
        "caveat": "Blueprints are not the number of distinct things a player can find: the game also generates relics, applies item mods (Mods tags) and tier-scaled variants at run time.",
    }
    dest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "items.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"_meta": meta, "items": dict(sorted(out.items()))}, f, ensure_ascii=True, separators=(",", ":"))
    print(f"wrote {dest} ({os.path.getsize(dest) // 1024} KB)")
    print(json.dumps(meta["counts"], indent=1))
    print("loot by group:", json.dumps(meta["loot_by_group"]))
    print("loot by physics category:", json.dumps(meta["loot_by_physics_category"]))
    print("loot by tier:", json.dumps(meta["loot_by_tier"]))


if __name__ == "__main__":
    main()
