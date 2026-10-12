"""Death statistics shared by the generation report (tools/generation_report.py), the chronicler and the prompt (HANDOFF issues 172 and 173).

Chronicles are the record of every life; the death ledger (data/death_ledger.json, by hand) says what kind of death it was; the COLLECTION SWITCH (data/collection.json, human) says which
lives count as evidence for the agent. The human's rule (2026-10-12): the lives so far were played without the defensive systems, so they are history and are never shown to the agent; data
collection is OFF while a new character is being worked on and is switched ON when that character can operate (it uses its abilities, retreats, heals), and only lives that ENDED while it was
ON count.

Read-only except `set_collecting`. Never raises into the brain.
"""
import json
import os
import re
import statistics
import sys
import time

REPO = os.path.dirname(os.path.abspath(__file__))
CHRONICLE_DIR = os.path.join(REPO, "chronicles")
LEDGER_PATH = os.path.join(REPO, "data", "death_ledger.json")
COLLECTION_PATH = os.path.join(REPO, "data", "collection.json")
KINDS = ("bug", "gap", "decision", "luck", "lab")
KNOWN_KILLER_MIN_CHARACTERS = 2         # a class is shown to the agent only when it has ended at least this many different characters
KNOWN_KILLER_MAX_LINES = 3
_CACHE = {"rows": None, "ledger": None, "at": 0.0}

_KILL_VERBS = r"(?:killed|bitten to death|lased to death|clawed to death|stung to death|gored to death|stabbed to death|shot to death|burned to death|crushed to death|torn apart)"
_ADJECTIVES = {"wet", "bloody", "sappy", "salty", "tarred", "fiery", "flaming", "slimy", "oozing", "dilute", "wading", "stuck", "engulfed", "shrewd", "feral", "rusty", "glowing"}


def clean_cause(text):
    """The cause line without the game's @@ and ## markers, lower case."""
    return re.sub(r"@@|##", "", str(text or "")).strip().strip('"').lower()


def cause_class(cause):
    """A short class for a cause-of-death line: 'turret', 'poison', 'fire', 'bleeding', 'psychic hunter', or the killer's name without its adjectives."""
    c = clean_cause(cause)
    if not c:
        return "unknown"
    if "psychic" in c or "-no-longer" in c or "ptoh" in c:
        return "psychic hunter"
    if "turret" in c:
        return "turret"
    if "died of poison" in c or "poison" in c.split(" by ")[0]:
        return "poison"
    if "immolated" in c or "burned to death" in c:
        return "fire"
    if "bled to death" in c:
        return "bleeding"
    if " by " not in c:
        return c[:40]
    who = c.rsplit(" by ", 1)[1]
    who = re.sub(r" (?:with|in) .*$", "", who).rstrip(".")
    who = re.sub(r"^(?:an? |the )", "", who)
    who = re.sub(r"\[[^\]]*\]", " ", who).replace("|", " ")
    if ", the " in who:
        who = who.split(", the ", 1)[1]
    try:
        sys.path.insert(0, REPO)
        import creature_threat
        entry = creature_threat.lookup(name=who)
        if entry and entry.get("name"):
            return str(entry["name"]).lower()
    except Exception:
        pass
    words = [w for w in who.split() if w not in _ADJECTIVES]
    return " ".join(words) or who


def _front_matter(text):
    """{key: value} from the '---' block at the top of a chronicle, values unquoted."""
    out = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"')
    return out


def _name_root(title):
    """The character's own name: the last word of the title once the [...] tags are gone ('sappy bloody Nashrouun [engulfed by a ...]' -> 'Nashrouun')."""
    t = re.sub(r"\[[^\]]*\]", " ", str(title or ""))
    t = re.sub(r"^(?:the )?chronicle of ", "", t.strip(), flags=re.I)
    t = re.sub(r"\(gen \d+\)", " ", t, flags=re.I)
    words = [w for w in re.split(r"[\s|]+", t) if w]
    return words[-1] if words else "?"


def parse_chronicles(chron_dir=None):
    """[{gen, name, root, level, turns, place, cause, cls, category, date, collected}] sorted by generation. `collected` is True only when the chronicle says data_collection "on"
    (the chronicles before 2026-10-12 do not carry the field and never count). A chronicle that cannot be read is skipped."""
    chron_dir = chron_dir or CHRONICLE_DIR
    rows = []
    try:
        names = sorted(n for n in os.listdir(chron_dir) if n.startswith("Chronicle_Gen") and n.endswith(".md"))
    except OSError:
        return rows
    for n in names:
        try:
            with open(os.path.join(chron_dir, n), encoding="utf-8", errors="ignore") as f:
                head = f.read(2500)
            fm = _front_matter(head)
            title = fm.get("title", "")
            gen = int(fm.get("generation") or re.search(r"Gen(\d+)", n).group(1))
            cause = fm.get("cause_of_death", "")
            rows.append({"gen": gen, "name": re.sub(r"^The Chronicle of |\s*\(Gen \d+\)$", "", title).strip(), "root": _name_root(title), "level": int(fm.get("level") or 0),
                         "turns": int(fm.get("turns_survived") or 0), "place": fm.get("resting_place", ""), "cause": clean_cause(cause), "cls": cause_class(cause),
                         "category": fm.get("category", ""), "date": fm.get("date_recorded", ""), "collected": fm.get("data_collection", "").lower() == "on"})
        except (ValueError, AttributeError):
            continue
    rows.sort(key=lambda r: r["gen"])
    return rows


def load_ledger(path=None):
    """{gen (int): {kind, cls, note, issue}} from data/death_ledger.json; {} when missing or unreadable."""
    try:
        with open(path or LEDGER_PATH, encoding="utf-8") as f:
            raw = json.load(f).get("deaths", {})
        return {int(k): v for k, v in raw.items() if isinstance(v, dict)}
    except (OSError, ValueError, AttributeError):
        return {}


def mark_retries(rows):
    """Adds r['retry_of'] = the generation of the previous life when it had the same character name (a retry from a saved state, as Gen 30 to 33 and Gen 38 to 41)."""
    for prev, cur in zip(rows, rows[1:]):
        cur["retry_of"] = prev["gen"] if cur["root"] == prev["root"] and cur["root"] != "?" else None
    if rows:
        rows[0]["retry_of"] = None
    return rows


def collection_state(path=None):
    """{"collecting": bool, "since_generation": int or None, "note": str}. A missing or unreadable file means OFF."""
    try:
        with open(path or COLLECTION_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return {"collecting": bool(d.get("collecting")), "since_generation": d.get("since_generation"), "note": str(d.get("note", ""))}
    except (OSError, ValueError, AttributeError):
        return {"collecting": False, "since_generation": None, "note": ""}


def collecting(path=None):
    return collection_state(path)["collecting"]


def set_collecting(on, note="", path=None, since_generation=None):
    """Writes the switch and returns the new state."""
    path = path or COLLECTION_PATH
    state = {"collecting": bool(on), "since_generation": since_generation if on else None, "note": note, "changed": time.strftime("%Y-%m-%d %H:%M:%S"),
             "_meta": "Human switch (HANDOFF issue 173). ON: lives that END while it is on count as evidence and may be shown to the agent as known killers. OFF: development runs; their deaths do not count."}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    return collection_state(path)


def counted_lives(rows, ledger):
    """The lives that count as evidence for the agent: ended while collection was ON, and not marked as a lab in the ledger."""
    return [r for r in rows if r.get("collected") and ledger.get(r["gen"], {}).get("kind") != "lab"]


def killer_stats(rows, ledger):
    """{class: {"characters": n, "lives": n, "levels": [...], "gens": [...], "fixed": bool}} over the counted lives, plus "_all": {"characters": n, "lives": n}."""
    lives = counted_lives(rows, ledger)
    stats = {}
    roots_all = set()
    for r in lives:
        led = ledger.get(r["gen"], {})
        cls = led.get("cls") or r["cls"]
        s = stats.setdefault(cls, {"characters": set(), "lives": 0, "levels": [], "gens": [], "fixed": False})
        s["characters"].add(r["root"])
        s["lives"] += 1
        s["levels"].append(r["level"])
        s["gens"].append(r["gen"])
        s["fixed"] = s["fixed"] or bool(led.get("kind") in ("gap", "bug") and led.get("issue"))
        roots_all.add(r["root"])
    for s in stats.values():
        s["characters"] = len(s["characters"])
    stats["_all"] = {"characters": len(roots_all), "lives": len(lives)}
    return stats


def _snapshot(chron_dir=None, ledger_path=None):
    """Chronicles and ledger, re-read at most every 60 seconds (a prompt is built every turn)."""
    now = time.time()
    use_cache = not chron_dir and not ledger_path
    if use_cache and _CACHE["rows"] is not None and now - _CACHE["at"] < 60:
        return _CACHE["rows"], _CACHE["ledger"]
    rows = mark_retries(parse_chronicles(chron_dir))
    ledger = load_ledger(ledger_path)
    if use_cache:
        _CACHE.update({"rows": rows, "ledger": ledger, "at": now})
    return rows, ledger


def _classes_in_view(enemies, effects):
    """Cause classes of what is in view or on him: creature names through the catalogue, 'turret', and the poison, bleeding and fire effects."""
    found = []
    try:
        sys.path.insert(0, REPO)
        import creature_threat
    except Exception:
        creature_threat = None
    for e in enemies or []:
        blob = f"{e.get('blueprint', '')} {e.get('name', '')}".lower()
        if "turret" in blob:
            found.append("turret")
            continue
        if creature_threat:
            try:
                entry = creature_threat.lookup(blueprint=e.get("blueprint"), name=e.get("name"))
            except Exception:
                entry = None
            if entry and entry.get("name"):
                found.append(str(entry["name"]).lower())
    eff = " ".join(str(x).lower() for x in (effects or []))
    for word, cls in (("poison", "poison"), ("bleed", "bleeding"), ("burning", "fire"), ("on fire", "fire")):
        if word in eff:
            found.append(cls)
    seen = []
    for c in found:
        if c not in seen:
            seen.append(c)
    return seen


def _catalogue_facts(cls):
    try:
        sys.path.insert(0, REPO)
        import creature_threat
        entry = creature_threat.lookup(name=cls)
        if not entry:
            return ""
        spd = ((entry.get("stats") or {}).get("Speed") or {}).get("Value")
        bits = [f"level {entry.get('level')}"] if entry.get("level") is not None else []
        if spd:
            bits.append(f"speed {str(spd).split(',')[0]}")
        return (", " + ", ".join(bits)) if bits else ""
    except Exception:
        return ""


def prompt_block(enemies, effects, level=None, chron_dir=None, ledger_path=None):
    """A short 'known killers' block for the system prompt, or "" when nothing applies. Only what is in view or on him is mentioned, only classes that have ended at least
    KNOWN_KILLER_MIN_CHARACTERS different counted characters, and nothing at all while collection has produced no counted lives. History, not orders. Never raises."""
    try:
        rows, ledger = _snapshot(chron_dir, ledger_path)
        stats = killer_stats(rows, ledger)
        total = stats.get("_all", {}).get("characters", 0)
        if not total:
            return ""
        lines = []
        for cls in _classes_in_view(enemies, effects):
            s = stats.get(cls)
            if not s or s["characters"] < KNOWN_KILLER_MIN_CHARACTERS:
                continue
            lv = sorted(s["levels"])
            span = f"level {lv[0]}" if lv[0] == lv[-1] else f"levels {lv[0]} to {lv[-1]}"
            fix = " A defensive rule now exists for this." if s["fixed"] else ""
            you = f" You are level {level}." if level else ""
            lines.append(f"- {cls}: ended {s['characters']} of {total} earlier characters ({span}){_catalogue_facts(cls)}.{you}{fix}")
            if len(lines) >= KNOWN_KILLER_MAX_LINES:
                break
        if not lines:
            return ""
        return "KNOWN KILLERS (what has actually ended earlier characters of this lineage; history, not orders):\n" + "\n".join(lines)
    except Exception:
        return ""
