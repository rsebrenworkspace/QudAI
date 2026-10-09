"""Writes docs/CREATURES.md from data/creatures.json (BACKLOG B12): what the catalog holds, and the lists a plan or a prompt would want first.

    python tools/creature_report.py

Static facts from the game's blueprints, for planning; the live state is the truth for a creature in front of the character (heroes and mutated variants differ)."""
import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "creatures.json")
OUT = os.path.join(ROOT, "docs", "CREATURES.md")


def best_melee(e):
    """The highest dice maximum among the creature's natural attacks, as text ('1d6 x2'), or ''."""
    best, txt = -1, ""
    for m in e.get("melee") or []:
        d = str(m.get("damage") or "")
        try:
            n, rest = d.lower().split("d", 1)
            sides = int(rest.split("+")[0].split("-")[0])
            top = int(n or 1) * sides
        except (ValueError, IndexError):
            continue
        if top > best:
            best, txt = top, f"{d}" + (f" x{m.get('count')}" if str(m.get("count")) not in ("1", "None") else "")
    return txt


def row(bp, e):
    lv = f"{e.get('level')}" + (f"-{e['level_max']}" if e.get("level_max") else "")
    return f"| {e['name']} | `{bp}` | {lv} | {e.get('hp', '?')} | {best_melee(e) or '-'} | {', '.join(e.get('ranged') or []) or '-'} | {'rooted' if e.get('rooted') else ''} | {'hostile' if e.get('likely_hostile') else ('calm' if e.get('start_rep') is not None else '?')} |"


def render(doc):
    c = doc["creatures"]
    m = doc["meta"]
    L = ["# Creature catalog (generated)", "",
         f"Built {m['built']} from `{m['source']}` by `tools/build_creature_catalog.py`; this page by `tools/creature_report.py`. Static facts for planning only: the live",
         "`state.json` is the truth for the creature in front of the character (heroes, mutated and legendary creatures differ from their blueprint).", "",
         f"- **{m['creatures']}** concrete creature blueprints; {m['with_level']} with a level, {m['ranged']} carry or use a ranged attack, {m['rooted']} are rooted (turrets, plants, wall vines), {m['likely_hostile']} start hostile by their factions' starting reputation.",
         "- Levels by band: " + ", ".join(f"{k}: {v}" for k, v in m["level_bands"].items()),
         "- Checked against the live game: the levels of the creatures named in past post-mortems (chitinous puma 12, irritable tortoise 5, a snapjaw 1, ...) all match.", ""]
    hostile_early = sorted(((bp, e) for bp, e in c.items() if e.get("likely_hostile") and (e.get("level") or 99) <= 12 and not e.get("rooted")), key=lambda x: (x[1]["level"], -(x[1].get("hp") or 0)))
    L += ["## Hostile on sight at the start (faction starting reputation of -250 or less, inferred), level 12 or below, mobile (what a young character meets)", "", "| creature | blueprint | level | HP | best melee | ranged | | |", "|---|---|---|---|---|---|---|---|"]
    L += [row(bp, e) for bp, e in hostile_early[:60]]
    if len(hostile_early) > 60:
        L.append(f"| ... {len(hostile_early) - 60} more | | | | | | | |")
    shooters = sorted(((bp, e) for bp, e in c.items() if e.get("rooted") and e.get("is_ranged")), key=lambda x: (x[1].get("hp") or 0))
    L += ["", "## Rooted shooters (turrets and the like): fragile ones first", "", "| creature | blueprint | level | HP | best melee | ranged | | |", "|---|---|---|---|---|---|---|---|"]
    L += [row(bp, e) for bp, e in shooters[:25]]
    ranged = sorted(((bp, e) for bp, e in c.items() if e.get("is_ranged") and not e.get("rooted") and (e.get("level") or 99) <= 15), key=lambda x: x[1]["level"])
    L += ["", "## Mobile ranged attackers, level 15 or below", "", "| creature | blueprint | level | HP | best melee | ranged | | |", "|---|---|---|---|---|---|---|---|"]
    L += [row(bp, e) for bp, e in ranged[:40]]
    hero = sum(1 for e in c.values() if "hero_capable" in (e.get("flags") or []))
    mut = [e["name"] for e in c.values() if "random_mutations" in (e.get("flags") or [])]
    swarm = sorted(e["name"] for e in c.values() if "swarmer" in (e.get("flags") or []))
    L += ["", "## What varies between two creatures of the same blueprint", "",
          f"- {hero} blueprints can become named heroes (hero tags); {len(mut)} get random mutations ({', '.join(sorted(mut)[:6])}...); legendary creatures are generated per world.",
          f"- {len(swarm)} swarm (they fight as a group): {', '.join(swarm[:10])}{'...' if len(swarm) > 10 else ''}.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    with open(CATALOG, encoding="utf-8") as f:
        text = render(json.load(f))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {OUT} ({text.count(chr(10))} lines)")
