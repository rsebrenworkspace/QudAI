"""Danger ledger (HANDOFF issue 64): what each creature type has actually done to us, kept across characters.

The engine's difficulty rating compares levels only. It rated a level-1 giant amoeba "Average" while its four pseudopods took 17 of an 18 HP
character's hit points in one turn. This ledger records the largest single-turn HP loss seen next to exactly one kind of hostile, and kills, per
blueprint, and `apply` raises the rating of a creature that has proved dangerous *relative to the current character's maximum HP*. It only ever
raises a rating (never lowers the engine's), so every rule that already reads `difficulty` (avoid, retreat, stand-and-fight limits) uses it.

Thresholds are policy, not engine rules, and can be changed freely: see VERY_TOUGH_FRACTION and IMPOSSIBLE_FRACTION.
"""
import json
import os
import re
import time

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
LEDGER_PATH = os.path.join(MEMORY_DIR, "danger_ledger.json")

ORDER = ["Trivial", "Easy", "Average", "Tough", "Very Tough", "Impossible"]
VERY_TOUGH_FRACTION = 0.35      # one observed hit this share of max HP or more
IMPOSSIBLE_FRACTION = 0.60
MIN_HITS = 2                    # a single observation can be a freak crit; a kill counts at once
IGNORED_EFFECTS = ("burning", "on fire", "bleeding", "poison")

_CACHE = {"data": None, "path": None}


def _load():
    if _CACHE["data"] is not None and _CACHE["path"] == LEDGER_PATH:
        return _CACHE["data"]
    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    _CACHE.update({"data": data, "path": LEDGER_PATH})
    return data


def reset_cache():
    _CACHE.update({"data": None, "path": None})


def _save(data):
    try:
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        tmp = LEDGER_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, sort_keys=True)
        os.replace(tmp, LEDGER_PATH)
    except OSError:
        pass


def _entry(data, blueprint, name):
    e = data.setdefault(blueprint, {"name": name, "hits": 0, "max_hit": 0, "total_damage": 0, "kills": 0})
    e["name"] = name or e.get("name", blueprint)
    return e


def record_turn_damage(game_state, previous_hp):
    """Call once per exported state. Attributes the HP lost since the last state to the single kind of hostile standing next to him, if there is exactly one."""
    try:
        hp, max_hp = game_state.get("hp"), game_state.get("max_hp")
        if previous_hp is None or hp is None or not max_hp or hp >= previous_hp:
            return False
        effects = " ".join(game_state.get("effects", []) or []).lower()
        if game_state.get("is_on_fire") or any(k in effects for k in IGNORED_EFFECTS):
            return False
        adjacent = [e for e in game_state.get("visible_entities", []) or [] if e.get("is_enemy") and e.get("dist") == 1 and e.get("blueprint")]
        kinds = {e["blueprint"] for e in adjacent}
        if len(kinds) != 1:
            return False
        drop = int(previous_hp - hp)
        data = _load()
        e = _entry(data, next(iter(kinds)), adjacent[0].get("name", ""))
        e["hits"] += 1
        e["total_damage"] += drop
        if drop > e["max_hit"]:
            e["max_hit"] = drop
            e["max_hit_player_max_hp"] = int(max_hp)
        e["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save(data)
        return True
    except Exception:
        return False


def record_death(last_state, death_reason):
    """Credits the kill to the adjacent hostile named in the death message (or the only one adjacent)."""
    try:
        adjacent = [e for e in (last_state or {}).get("visible_entities", []) or [] if e.get("is_enemy") and e.get("dist", 99) <= 1 and e.get("blueprint")]
        if not adjacent:
            return None
        cause = re.sub(r"[^a-z ]", " ", str(death_reason or "").lower())
        named = [e for e in adjacent if re.sub(r"[^a-z ]", " ", str(e.get("name", "")).lower()).split("[")[0].strip() and
                 re.sub(r"[^a-z ]", " ", str(e.get("name", "")).lower()).strip() in cause]
        pick = (named or (adjacent if len({e["blueprint"] for e in adjacent}) == 1 else []))
        if not pick:
            return None
        data = _load()
        e = _entry(data, pick[0]["blueprint"], pick[0].get("name", ""))
        e["kills"] += 1
        e["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save(data)
        return pick[0]["blueprint"]
    except Exception:
        return None


def rating_for(blueprint, max_hp):
    """'Very Tough', 'Impossible' or None for this creature type against a character with `max_hp`."""
    e = _load().get(blueprint)
    if not e or not max_hp or (e.get("hits", 0) < MIN_HITS and e.get("kills", 0) < 1):
        return None
    frac = e.get("max_hit", 0) / float(max_hp)
    if frac >= IMPOSSIBLE_FRACTION:
        return "Impossible"
    if frac >= VERY_TOUGH_FRACTION:
        return "Very Tough"
    return None


def apply(enemies, max_hp):
    """A copy of the enemy list where proven-dangerous creatures carry the higher rating (`difficulty_engine` keeps the engine's)."""
    out = []
    for e in enemies or []:
        new = rating_for(e.get("blueprint"), max_hp)
        cur = e.get("difficulty", "")
        if new and (cur not in ORDER or ORDER.index(new) > ORDER.index(cur)):
            e = dict(e, difficulty=new, difficulty_engine=cur, ledger_note=f"max hit {_load()[e['blueprint']]['max_hit']} HP, {_load()[e['blueprint']]['kills']} kill(s)")
        out.append(e)
    return out
