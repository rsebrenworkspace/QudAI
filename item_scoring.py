"""Item scoring, loadout and junk decisions (HANDOFF issue 66).

Everything is derived from the game's own item data (data/items.json, built by tools/build_item_catalog.py) and from the build templates; there is
no matching on item names (the old item_evaluator.py did that, and substring matching on names is the bug class behind the `charge`/Lase and `tam` fixes).

Three layers:
  build_profile(template)             what a build values: weapon skills it trains, stats it prioritises, caster or ranged, shield user, heavy-armor tolerance
  score_item(item, profile)           a number and the reasons behind it (explainable; every weight is a named constant below, policy, not engine rules)
  choose_equips / choose_drops        loadout and junk decisions over an inventory; pure functions, no game access

The weights are policy guesses meant to be argued with: change a constant, re-run tools/item_report.py, read docs/ITEM_SCORES.md.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(HERE, "data", "items.json")

# ---- policy weights (points) -------------------------------------------------------------------------------------------------------------------
W_AV, W_DV, W_MA = 3.0, 1.5, 1.0            # armor value, dodge value, mental armor
W_DV_AGILE = 2.5                             # dodge matters more to an Agility build
W_STAT_BOOST = 2.5                           # per point of a stat boost, times the build's weight for that stat (3 top priority ... 1)
W_SPEED_BOOST = 0.2                          # per point of Speed
W_DAMAGE = 2.0                               # per point of average damage
W_PEN = 1.5                                  # per point of penetration bonus
SKILL_MATCH_BONUS = 6.0                      # a weapon the build trains
SKILL_MATCH_MULT = 1.5
OFF_SKILL_MULT = 0.45                        # an untrained weapon is still a weapon, but an inferior one
CASTER_MELEE_MULT = 0.7             # was 0.35 (human, 2026-10-09): the brain's stand-and-fight rule makes a caster melee anyway, with a 1d2 staff at level 5 (Gen 27)
TWO_HANDED_WITH_SHIELD = -5.0       # only charged when he actually owns a shield (human, 2026-10-09; profile["owns_shield"], see with_inventory)
SHIELD_BONUS = 4.0                           # for a build that trains Shield
RANGED_BONUS = 8.0                           # a firearm for a build that trains that firearm skill
WEIGHT_FREE = {"heavy": 40, "normal": 25, "light": 18}   # carried weight an item may have before it is penalised, by build type
W_WEIGHT = 0.30
KEEP_FLOOR = 3.0                             # an unequipped item scoring below this is junk when the pack is under pressure
BURDEN_DROP_RATIO = 0.70                     # carried weight / capacity above which junk is dropped
DOMINATED_MARGIN = 2.0                       # an item must beat the one it replaces by this much to be worth equipping
EQUIPMENT_GROUPS = ("armor", "shield", "melee_weapon", "missile_weapon")
# Stage 2 is conservative (human, 2026-10-06: some "junk" raises factions or may be a quest item, to be re-evaluated later): only these groups are ever
# dropped automatically. Everything else (books, data disks, trade goods, keys, cybernetics, trinkets, tools, consumables...) is kept.
# Firearms and bows are NOT dropped (human, 2026-10-07: the jewel-encrusted Issachar rifle from Kuyukas stays "as a trade asset"; the blueprint value used here is far
# below what a modded one sells for, so the scorer cannot judge it). Re-evaluate when live item values are exported (BACKLOG B8).
DROPPABLE_GROUPS = ("armor", "shield", "melee_weapon", "scrap", "corpse")
MAX_KEPT = {"food": 6, "tonic": 8, "medication": 6, "power_cell": 3, "grenade": 4, "thrown_weapon": 4, "light_source": 1}   # no water cap: waterskins are trade currency (human, 2026-10-07)

SKILL_ROOTS = {"Axe": "Axe", "Cudgel": "Cudgel", "Pistol": "Pistol", "Rifles": "Rifle", "Rifle": "Rifle", "LongBlades": "LongBlades", "LongBlade": "LongBlades",
               "ShortBlades": "ShortBlades", "ShortBlade": "ShortBlades", "HeavyWeapons": "HeavyWeapons", "Shield": "Shield", "Multiweapon": "MULTI"}
WEAPON_SKILLS = {"Axe", "Cudgel", "Pistol", "Rifle", "LongBlades", "ShortBlades", "HeavyWeapons"}
RANGED_SKILLS = {"Pistol", "Rifle", "HeavyWeapons"}
STATS = ("Strength", "Agility", "Toughness", "Intelligence", "Willpower", "Ego")

_CATALOG = {"data": None}


def catalog():
    if _CATALOG["data"] is None:
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                _CATALOG["data"] = json.load(f)
        except (OSError, ValueError):
            _CATALOG["data"] = {"_meta": {}, "items": {}}
    return _CATALOG["data"]


def item_info(blueprint):
    return catalog().get("items", {}).get(blueprint)


# ---- helpers ------------------------------------------------------------------------------------------------------------------------------------

def dice_mean(expr):
    """'1d8+2' -> 6.5, '3d2' -> 4.5, '2d6-1' -> 6.0, a plain number -> itself, anything else 0."""
    if expr is None:
        return 0.0
    s = str(expr).replace(" ", "")
    m = re.fullmatch(r"(\d+)d(\d+)([+-]\d+)?", s)
    if m:
        n, sides, bonus = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        return n * (sides + 1) / 2.0 + bonus
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_boosts(text):
    """'DV:4;MA:-1' -> {'DV': 4, 'MA': -1}."""
    out = {}
    for part in str(text or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            try:
                out[k.strip()] = float(v)
            except ValueError:
                pass
    return out


# ---- build profiles -----------------------------------------------------------------------------------------------------------------------------

def build_profile(template, cat=None):
    """What this build values, derived from its template (skill list, stat priorities, preferred weapons). No hand-written per-build rules."""
    cat = cat or catalog()
    skills = set()
    for s in template.get("skill_progression", []):
        root = SKILL_ROOTS.get(s.split("_")[0])
        if root:
            skills.add(root)
    pref = [w.lower() for w in template.get("combat_doctrine", {}).get("preferred_weapons", [])]
    for iid, it in cat.get("items", {}).items():
        if it.get("group") in ("melee_weapon", "missile_weapon") and it.get("name", "").lower() in pref and it.get("skill") in WEAPON_SKILLS:
            skills.add(it["skill"])
    wants_shield = "Shield" in skills or any(re.search(r"\bshield\b", w) for w in pref)
    weights, w = {}, 3.0
    for rule in template.get("stat_priorities", []):
        st = rule.get("stat")
        if st in STATS and st not in weights:
            weights[st] = w
            w = max(1.0, w - 0.5)
    weapon_skills = skills & WEAPON_SKILLS
    targets = {r["stat"]: r.get("target", 0) for r in template.get("stat_priorities", []) if r.get("stat") in STATS}
    top_strength = max([r.get("target", 0) for r in template.get("stat_priorities", []) if r.get("stat") == "Strength"] or [0])
    top_agility = max([r.get("target", 0) for r in template.get("stat_priorities", []) if r.get("stat") == "Agility"] or [0])
    return {
        "name": template.get("name", ""),
        "skills": sorted(skills), "weapon_skills": sorted(weapon_skills), "stat_weights": weights, "stat_targets": targets,
        "caster": not weapon_skills, "ranged": bool(skills & RANGED_SKILLS), "wants_shield": wants_shield,
        "multi_arm": "MULTI" in skills,
        "weight_class": "heavy" if top_strength >= 22 else ("light" if (not weapon_skills or top_agility >= 24) else "normal"),
        "agile": top_agility >= 24,
    }


# ---- scoring ------------------------------------------------------------------------------------------------------------------------------------

def _weight_penalty(weight, profile):
    free = WEIGHT_FREE.get(profile["weight_class"], 25)
    return -W_WEIGHT * (weight - free) if weight > free else 0.0


def _boost_points(boosts, profile, reasons):
    pts = 0.0
    for k, v in boosts.items():
        if k in STATS:
            p = W_STAT_BOOST * profile["stat_weights"].get(k, 0.5) * v
        elif k == "Speed":
            p = W_SPEED_BOOST * v
        elif k == "DV":
            p = (W_DV_AGILE if profile["agile"] else W_DV) * v
        elif k == "AV":
            p = W_AV * v
        elif k == "MA":
            p = W_MA * v
        else:
            p = 0.0
        if p:
            reasons.append(f"{k} {v:+g}: {p:+.1f}")
        pts += p
    return pts


def score_item(item, profile):
    """(score, keep_value, reasons) for one catalog entry (or a live item dict with the same keys) under a build profile.

    `score` ranks items against each other for equipping and junk decisions; `keep_value` is a separate, small reason to carry something that scores low
    (it is worth coin for the merchants the character will visit later). Weights are the constants at the top of this file."""
    g = item.get("group", "other")
    reasons = []
    score = 0.0
    weight = item.get("weight") or 0
    if g in ("armor", "shield"):
        av, dv, ma = item.get("av") or 0, item.get("dv") or 0, item.get("ma") or 0
        score += W_AV * av
        score += (W_DV_AGILE if profile["agile"] else W_DV) * dv
        score += W_MA * ma
        reasons.append(f"AV {av:g} DV {dv:g}" + (f" MA {ma:g}" if ma else ""))
        boosts = parse_boosts(((item.get("parts") or {}).get("EquipStatBoost") or {}).get("Boosts"))
        score += _boost_points(boosts, profile, reasons)
        if g == "shield":
            if profile["wants_shield"]:
                score += SHIELD_BONUS
                reasons.append(f"trains Shield: +{SHIELD_BONUS:g}")
            elif profile["multi_arm"] or profile["ranged"]:
                score -= 2
                reasons.append("shield ties up a hand: -2")
        pen = _weight_penalty(weight, profile)
        if pen:
            reasons.append(f"weight {weight:g} for a {profile['weight_class']} build: {pen:.1f}")
        score += pen
    elif g == "melee_weapon":
        dmg = dice_mean(item.get("damage"))
        base = W_DAMAGE * dmg + W_PEN * (item.get("pen") or 0) + 0.5 * (item.get("hit") or 0)
        reasons.append(f"damage {item.get('damage')} (avg {dmg:g}), pen {item.get('pen') or 0}")
        sk = item.get("skill")
        if sk in profile["weapon_skills"]:
            base = base * SKILL_MATCH_MULT + SKILL_MATCH_BONUS
            reasons.append(f"trained skill {sk}: x{SKILL_MATCH_MULT:g} +{SKILL_MATCH_BONUS:g}")
        elif profile["caster"]:
            base *= CASTER_MELEE_MULT
            reasons.append(f"caster build: x{CASTER_MELEE_MULT:g}")
        else:
            base *= OFF_SKILL_MULT
            reasons.append(f"untrained skill {sk}: x{OFF_SKILL_MULT:g}")
        if item.get("two_handed") and profile["wants_shield"] and profile.get("owns_shield"):
            base += TWO_HANDED_WITH_SHIELD
            reasons.append(f"two-handed while he owns a shield: {TWO_HANDED_WITH_SHIELD:g}")
        score += base
        pen = _weight_penalty(weight, profile)
        if pen:
            reasons.append(f"weight {weight:g}: {pen:.1f}")
        score += pen
    elif g == "missile_weapon":
        sk = item.get("skill")
        base = (item.get("accuracy") or 10) / 4.0 + (item.get("range") or 3) + 2.0 * (item.get("shots") or 1)
        reasons.append(f"accuracy {item.get('accuracy')}, range {item.get('range')}, shots {item.get('shots')}")
        if sk in profile["weapon_skills"]:
            base += RANGED_BONUS
            reasons.append(f"trained skill {sk}: +{RANGED_BONUS:g}")
        else:
            base *= 0.3
            reasons.append(f"untrained skill {sk}: x0.3 (and it needs ammo)")
        score += base + _weight_penalty(weight, profile)
    elif g in ("tonic", "medication", "applicator"):
        score += 6.0
        reasons.append("healing or utility: +6")
    elif g == "food":
        score += 3.0
        reasons.append("food: +3")
    elif g == "water_container":
        score += 5.0
        reasons.append("water: +5")
    elif g == "light_source":
        score += 6.0 if profile["caster"] else 4.0
        reasons.append("light source")
    elif g == "cybernetics":
        score += 8.0
        reasons.append("cybernetic implant (installed at a clinic, valuable to merchants): +8")
    elif g in ("artifact", "tool"):
        score += 10.0 if g == "artifact" else 3.0
        reasons.append(g)
    elif g == "quest_item":
        score += 50.0
        reasons.append("quest item: never dropped")
    elif g == "power_cell":
        score += 2.0
        reasons.append("energy cell: +2")
    elif g == "grenade" or g == "thrown_weapon":
        score += 3.0
        reasons.append(g + ": +3")
    elif g == "ammo":
        score += 4.0 if profile["ranged"] else 0.0
        reasons.append("ammo for a firearm build" if profile["ranged"] else "ammo, but the build uses no firearm: 0")
    elif g == "data_disk":
        score += 2.0
    elif g == "book":
        score += 1.0
    elif g == "corpse":
        score -= 5.0
        reasons.append("a corpse is food on the ground, not pack material: -5")
    elif g in ("scrap", "trinket", "trade_good", "clothes", "other"):
        score += 0.0
    if item.get("escape"):
        score += 8.0
        reasons.append("teleporting/escape gear: +8")
    value = item.get("value") or 0
    keep_value = 0.0
    if value and weight is not None:
        keep_value = min(6.0, value / max(1.0, weight + 1.0) / 20.0)
    return round(score, 2), round(keep_value, 2), reasons


# ---- loadout and junk --------------------------------------------------------------------------------------------------------------------------

def _entry(inv_item):
    """A live inventory record merged over its catalog entry: {'blueprint', 'id', 'count', 'equipped', ...live overrides}."""
    base = dict(item_info(inv_item.get("blueprint")) or {})
    base.update({k: v for k, v in inv_item.items() if v is not None})
    return base


# The blueprints with a Cursed part `[verified in the XML 2026-10-09]`; a worn Gentling Mask held a human's Face slot (Ego -1). The mod also exports `cursed` per item (the engine's own answer),
# which wins; this list covers an item whose flag is not exported.
CURSED_BLUEPRINTS = {"Psychal Fleshgun", "Gentling Collar", "Gentling Mask", "Inhibitor Cuff", "BarathrumiteSafetyBand", "Cyclopean Prism"}


def is_cursed(it):
    return bool((it or {}).get("cursed")) or (it or {}).get("blueprint") in CURSED_BLUEPRINTS


def with_inventory(profile, inventory):
    """The profile plus what the pack says about it: `owns_shield` (a shield is carried or worn), which decides whether a two-handed weapon costs him the shield hand.
    Every caller that scores items against a pack goes through this, so the equip rule, the drop rule and the ground pickup agree."""
    owns = any(_entry(it).get("group") == "shield" for it in (inventory or []))
    return dict(profile, owns_shield=owns)


def choose_equips(inventory, profile):
    """Equip actions: [(inventory item, slot, why)]. One best item per armor slot; one main weapon; a shield only for a build that wants one.

    An item is chosen only if it beats the equipped one in that slot by DOMINATED_MARGIN."""
    inventory = [it for it in (inventory or []) if it.get("equipped") or not is_cursed(it)]        # never put on a cursed item: it cannot be taken off again
    profile = with_inventory(profile, inventory)
    actions = []
    by_slot = {}
    for it in inventory:
        e = _entry(it)
        if e.get("group") == "armor" and e.get("slot"):
            by_slot.setdefault(e["slot"], []).append((score_item(e, profile)[0], it, e))
    for slot, cands in by_slot.items():
        cands.sort(key=lambda c: -c[0])
        worn = [c for c in cands if c[1].get("equipped")]
        best = cands[0]
        if not best[1].get("equipped") and (not worn or best[0] >= worn[0][0] + DOMINATED_MARGIN):
            actions.append((best[1], slot, f"scores {best[0]:g} vs {worn[0][0]:g} worn" if worn else f"scores {best[0]:g}, slot empty"))
    holds_firearm = profile["ranged"] and any(_entry(it).get("group") == "missile_weapon" and _entry(it).get("skill") in profile["weapon_skills"] for it in inventory)
    weapons = [(score_item(_entry(it), profile)[0], it) for it in inventory if _entry(it).get("group") in ("melee_weapon",)]
    if weapons and not holds_firearm:      # a build that shoots carries a firearm to hold: no dagger swaps until it has none
        weapons.sort(key=lambda c: -c[0])
        worn = [c for c in weapons if c[1].get("equipped")]
        if not weapons[0][1].get("equipped") and (not worn or weapons[0][0] >= worn[0][0] + DOMINATED_MARGIN):
            actions.append((weapons[0][1], "Hand", f"scores {weapons[0][0]:g}" + (f" vs {worn[0][0]:g} wielded" if worn else "")))
    if profile["ranged"]:
        guns = [(score_item(_entry(it), profile)[0], it) for it in inventory if _entry(it).get("group") == "missile_weapon" and _entry(it).get("skill") in profile["weapon_skills"]]
        if guns:
            guns.sort(key=lambda c: -c[0])
            worn = [c for c in guns if c[1].get("equipped")]
            if not guns[0][1].get("equipped") and (not worn or guns[0][0] >= worn[0][0] + DOMINATED_MARGIN):
                actions.append((guns[0][1], "Missile", f"firearm scores {guns[0][0]:g}" + (f" vs {worn[0][0]:g} held" if worn else "")))
    if profile["wants_shield"]:
        shields = [(score_item(_entry(it), profile)[0], it) for it in inventory if _entry(it).get("group") == "shield"]
        if shields:
            shields.sort(key=lambda c: -c[0])
            worn = [c for c in shields if c[1].get("equipped")]
            if not shields[0][1].get("equipped") and (not worn or shields[0][0] >= worn[0][0] + DOMINATED_MARGIN):
                actions.append((shields[0][1], "Hand", f"shield scores {shields[0][0]:g}"))
    return actions


def choose_drops(inventory, profile, carried_weight=None, capacity=None, hungry=False):
    """Items to drop: [(inventory item, reason, how many)], most useless first. Never drops anything equipped.

    Dropped when (a) a better carried item of the same kind makes it redundant, or (b) it scores below KEEP_FLOOR AND the pack is under pressure
    (carried weight over BURDEN_DROP_RATIO of capacity). Quest items and artifacts are never dropped; stackable supplies are capped at MAX_KEPT."""
    profile = with_inventory(profile, inventory)
    entries = [(it, _entry(it)) for it in inventory]
    n_light = sum(1 for _, e in entries if e.get("group") == "light_source")
    n_ranged = sum(1 for _, e in entries if e.get("group") == "missile_weapon")
    pressure = bool(carried_weight is not None and capacity and carried_weight > BURDEN_DROP_RATIO * capacity)
    drops = []
    pressure_drops = []
    scored = []
    for it, e in entries:
        s, kv, why = score_item(e, profile)
        scored.append((it, e, s, kv))
    # redundancy: an unequipped armor piece / weapon / shield beaten by another carried item of the same slot or kind
    best = {}
    for it, e, s, kv in scored:
        key = ("armor", e.get("slot")) if e.get("group") == "armor" else (e.get("group"),)
        if e.get("group") in ("armor", "melee_weapon", "shield"):
            if key not in best or s > best[key]:
                best[key] = s
    for it, e, s, kv in scored:
        g = e.get("group")
        if it.get("equipped") or g in ("quest_item", "artifact") or it.get("never_drop") or e.get("escape") or it.get("identified") is False or it.get("unidentified"):
            continue                      # never: worn gear, quest items, artifacts, escape gear, anything not yet identified
        if e.get("protect"):
            continue                      # reputation trophies, quest items, faction deeds, relics (catalog `protect`)
        if g not in DROPPABLE_GROUPS:
            continue                      # conservative: only the whitelisted groups are ever dropped automatically
        if g == "light_source" and n_light <= 1:
            continue                      # the only light source
        if g == "missile_weapon" and n_ranged <= 1 and profile["ranged"]:
            continue                      # the only ranged weapon of a build that shoots
        key = ("armor", e.get("slot")) if g == "armor" else (g,)
        if g in ("armor", "melee_weapon", "shield") and key in best and s + DOMINATED_MARGIN <= best[key]:
            drops.append((s, it, f"outclassed: scores {s:g}, a carried {g.replace('_', ' ')} scores {best[key]:g}", it.get("count") or 1))
            continue
        cap = MAX_KEPT.get(g)
        if cap is not None and (it.get("count") or 1) > cap and not (g == "food" and hungry):
            drops.append((s - 1, it, f"more than {cap} {g.replace('_', ' ')} (carrying {it.get('count')}): drop the extra", (it.get("count") or 1) - cap))
            continue
        if not pressure or (e.get("weight") or 0) <= 0:
            continue                      # dropping something weightless (a credit wedge) never relieves a heavy pack
        pct = int(100 * carried_weight / capacity)
        if g in EQUIPMENT_GROUPS:
            # Equipment is never junk by an absolute threshold: any boots beat bare feet. It is junk only when outclassed (above) or harmful.
            if s < 0:
                pressure_drops.append((s, it, f"scores {s:g}: it would make him worse, and the pack is {pct}% full", it.get("count") or 1, e.get("weight") or 0))
        elif s + kv < KEEP_FLOOR:
            pressure_drops.append((s + kv, it, f"scores {s:g} (+{kv:g} trade value) below {KEEP_FLOOR:g} and the pack is {pct}% full", it.get("count") or 1, e.get("weight") or 0))
    drops.sort(key=lambda d: d[0])
    out = [(it, why, n) for _, it, why, n in drops]
    # under pressure, drop the least useful first and only as much as is needed to get comfortably under the limit
    if pressure:
        freed = sum((_entry(it).get("weight") or 0) * n for it, _, n in out)
        goal = 0.9 * BURDEN_DROP_RATIO * capacity
        for s, it, why, n, w in sorted(pressure_drops, key=lambda d: d[0]):
            if carried_weight - freed <= goal:
                break
            out.append((it, why, n))
            freed += w * n
    return out
