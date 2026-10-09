"""Creature catalogue adapter and threat score (BACKLOG B12 stage 2, HANDOFF issue 84).

Display only: nothing in brain.py acts on these numbers yet. The catalogue (data/creatures.json) is built from the game's own XML by
tools/build_creature_catalog.py; this module looks a creature up and answers "how dangerous is it to the character we have now".

The score is a race: turns we need to kill it against turns it needs to kill us. Every constant that is a guess is named below and
is calibrated against the recorded deaths by tools/threat_calibration.py. [unverified] until that tool says otherwise.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(ROOT, "data", "creatures.json")

# --- guesses, tuned by tools/threat_calibration.py (change them there, not in the middle of a fight) ---
HIT_CHANCE = 0.75             # share of attacks that land
RANGED_DAMAGE = 7.0           # per shot when the catalogue knows the weapon's name but not its damage
OUR_ARMOR = 4                 # AV of a starting character; the state does not export it yet (R3: C# should), so a guess
WEAPON_PV = 2                 # penetration bonus a creature's natural weapon adds to its strength modifier; a guess, fitted to the damage ledger
OUR_BASE_DAMAGE = 3.0         # what a starting character deals per swing before level
OUR_DAMAGE_PER_LEVEL = 0.35
APPROACH_TURNS = 4            # turns a shooter fires at us while we close the distance (a melee-only character cannot answer it)

CLASSES = ((0.25, "trivial"), (0.6, "easy"), (1.0, "fair"), (1.6, "dangerous"), (float("inf"), "deadly"))

_cache = {}


def _exploding_distribution(depth=6):
    """Distribution of the engine's penetration roll: 1d10 - 2, and a result of 8 (a natural 10) adds 8 and rolls again.
    [verified in code: Stat.RollDamagePenetrations, decoded from the IL 2026-10-08]"""
    res = {}

    def rec(p, acc, k):
        for face in range(1, 11):
            r = face - 2
            if r == 8 and k < depth:
                rec(p / 10.0, acc + r, k + 1)
            else:
                res[acc + r] = res.get(acc + r, 0.0) + p / 10.0
    rec(1.0, 0, 0)
    return res


_PEN_DIST = _exploding_distribution()


def expected_penetrations(armor, bonus):
    """The engine rolls three trials; each one that beats the target's AV (roll + min(bonus, cap)) is a penetration, and a hit deals
    one roll of the weapon's damage dice PER penetration. So a hit is worth between 0 and 3 times the dice.
    [verified in code: Stat.RollDamagePenetrations (3 trials) and Combat.MeleeAttackWithWeaponInternal (damage summed per penetration)]"""
    p = sum(prob for v, prob in _PEN_DIST.items() if v + bonus > armor)
    return 3.0 * p


def strength_modifier(entry):
    """(Strength - 16) // 2 from the catalogue's strength formula ('16,1d3,(t-1)d2' starts at 16 and the dice add about 2). [unverified: the divisor]"""
    s = ((entry.get("stats") or {}).get("Strength") or {})
    text = str(s.get("sValue") or s.get("Value") or "16")
    m = re.match(r"\s*(\d+)", text)
    base = int(m.group(1)) if m else 16
    if re.search(r"1d3", text):
        base += 2
    return (base - 16) // 2


def load_catalog(path=CATALOG_PATH):
    """{blueprint: entry} from the catalogue file; {} when the file is missing, so the console and the brain never break on it."""
    if path in _cache:
        return _cache[path]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f).get("creatures", {})
    except (OSError, ValueError):
        data = {}
    _cache[path] = data
    return data


_name_index = {}


def _by_name(catalog):
    """{lower-case display name: blueprint}, built once per catalogue."""
    idx = _name_index.get(id(catalog))
    if idx is None:
        idx = {}
        for bp, e in catalog.items():
            idx.setdefault(str(e.get("name", "")).lower(), bp)
        _name_index[id(catalog)] = idx
    return idx


def lookup(blueprint=None, name=None, catalog=None):
    """The catalogue entry for a blueprint id, or failing that for a display name. A display name carries adjectives
    ('wet chitinous puma', 'shrewd baboon'), so the longest trailing run of words that is a catalogue name wins."""
    cat = catalog if catalog is not None else load_catalog()
    if blueprint and blueprint in cat:
        return cat[blueprint]
    if not name:
        return None
    clean = re.sub(r"\{\{[^|]*\||\}\}|\[[^\]]*\]|[^a-zA-Z' -]", " ", str(name)).lower().split()
    idx = _by_name(cat)
    for i in range(len(clean)):
        bp = idx.get(" ".join(clean[i:]))
        if bp:
            return cat[bp]
    return None


def _dice_average(text):
    """Average of '2d4+1', '1d3', '5'; 0 when it is not dice."""
    m = re.fullmatch(r"\s*(\d+)d(\d+)\s*([+-]\s*\d+)?\s*", str(text or ""))
    if m:
        n, s = int(m.group(1)), int(m.group(2))
        bonus = int(m.group(3).replace(" ", "")) if m.group(3) else 0
        return n * (s + 1) / 2.0 + bonus
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def damage_per_turn(entry, observed_per_hit=None, armor=None):
    """Expected damage the creature deals to us per turn. observed_per_hit (from memory/danger_ledger.json: total_damage / hits) beats the dice."""
    if entry is None:
        return 0.0
    melee = 0.0
    for atk in entry.get("melee") or []:
        try:
            count = int(atk.get("count") or 1)
        except ValueError:
            count = 1
        melee += count * _dice_average(atk.get("damage"))
    melee *= expected_penetrations(OUR_ARMOR if armor is None else armor, strength_modifier(entry) + WEAPON_PV)
    if observed_per_hit:
        melee = max(melee, observed_per_hit * max(1, sum(int(a.get("count") or 1) for a in (entry.get("melee") or []))))
    ranged = RANGED_DAMAGE if entry.get("ranged") else 0.0
    return max(melee, ranged) * HIT_CHANCE


def creature_armor(entry):
    """The creature's AV from the catalogue (a fixed Value or the first number of a formula); 0 when unknown."""
    s = ((entry or {}).get("stats") or {}).get("AV") or {}
    m = re.match(r"\s*(-?\d+)", str(s.get("Value", s.get("sValue", "0"))))
    return int(m.group(1)) if m else 0


def our_damage_per_turn(level, us=None, target=None):
    """What we deal per turn. With the state's own `melee` block (main-hand dice and penetration, exported by the mod) it is the engine's rule against the
    target's AV; without it, a guess from our level."""
    melee = (us or {}).get("melee") or {}
    if melee.get("damage"):
        return _dice_average(melee["damage"]) * expected_penetrations(creature_armor(target), int(melee.get("penetration") or 0)) * HIT_CHANCE
    return (OUR_BASE_DAMAGE + OUR_DAMAGE_PER_LEVEL * max(1, level)) * HIT_CHANCE


def classify(ratio):
    for limit, label in CLASSES:
        if ratio < limit:
            return label
    return "deadly"


def threat(entry, our_level, our_hp, enemy_hp=None, observed_per_hit=None, us=None):
    """-> {ratio, cls, turns_to_kill_it, turns_to_kill_us, their_dps, notes}. ratio > 1 means it wins the race.
    enemy_hp is the live hit points when the state has them; otherwise the catalogue's base hit points (a floor: the engine adds hit points per level)."""
    if entry is None:
        return {"ratio": None, "cls": "unknown", "notes": ["not in the catalogue"]}
    notes = []
    hp = enemy_hp if enemy_hp else entry.get("hp") or 1
    if not enemy_hp:
        notes.append("base hit points")
    ours = max(0.1, our_damage_per_turn(our_level, us, entry))
    theirs = damage_per_turn(entry, observed_per_hit, (us or {}).get("av"))
    ttk_it = hp / ours
    if entry.get("ranged") or entry.get("is_ranged"):
        our_hp = max(1, our_hp - theirs * APPROACH_TURNS)
        notes.append("free shots while we close in")
    ttk_us = (our_hp / theirs) if theirs > 0 else 999.0
    ratio = ttk_it / ttk_us if ttk_us else 999.0
    if entry.get("rooted"):
        notes.append("rooted")
    if entry.get("is_ranged") or entry.get("ranged"):
        notes.append("ranged")
    return {"ratio": round(ratio, 2), "cls": classify(ratio), "turns_to_kill_it": round(ttk_it, 1),
            "turns_to_kill_us": round(ttk_us, 1), "their_dps": round(theirs, 1), "notes": notes}
