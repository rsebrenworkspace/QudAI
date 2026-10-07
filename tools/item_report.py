"""Writes docs/ITEM_SCORES.md: how many items the game has, and which items each build should prefer, with scores (HANDOFF issue 66).

    python tools/item_report.py

Reads data/items.json (tools/build_item_catalog.py) and the build templates; scores every loot item under each build profile with item_scoring.py.
Re-run after changing a weight in item_scoring.py and read the diff in docs/ITEM_SCORES.md.
"""
import collections
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QUDAI_EXCHANGE_DIR", os.path.join(ROOT, "scratch", "_report_exchange"))
import build_templates  # noqa: E402
import item_scoring  # noqa: E402

# One entry per distinct build: several template ids are aliases of the same build (same name).
CANONICAL = ["auspicious_beginnings", "praetorian_generalist", "limb_off", "esper_ited_away", "uncle_iroh", "bullet_specter", "classic_punchkin", "gunkin", "gas_giant"]
EQUIP_GROUPS = ["melee_weapon", "missile_weapon", "shield", "armor"]


def top(items, profile, group, n, slot=None):
    rows = []
    for iid, it in items.items():
        if it["group"] != group or (slot and it.get("slot") != slot):
            continue
        s, kv, why = item_scoring.score_item(it, profile)
        rows.append((s, iid, it))
    rows.sort(key=lambda r: (-r[0], r[2]["name"]))
    return rows[:n]


def fmt(rows):
    return "; ".join(f"{it['name']} ({s:g})" for s, _, it in rows) or "(none)"


def main():
    cat = item_scoring.catalog()
    meta = cat.get("_meta", {})
    all_loot = {k: v for k, v in cat["items"].items() if v.get("loot")}
    loot = {k: v for k, v in all_loot.items() if not v.get("rare")}      # random loot only; placed unique items are listed once, below
    out = []
    out.append("# Items in Caves of Qud, and which builds should prefer which")
    out.append("")
    out.append(f"*Generated {datetime.date.today()} by `tools/item_report.py` from `data/items.json` (built by `tools/build_item_catalog.py` from the game's own blueprint files). "
               "Scores are policy: every weight is a named constant in `item_scoring.py`. Confidence: `[verified in game data]` for the counts, `[policy guess]` for the scores.*")
    out.append("")
    out.append("## How many items are there")
    out.append("")
    c = meta.get("counts", {})
    out.append(f"The game defines **{c.get('blueprints_total')} object blueprints** in total. Of those, **{c.get('inherit_item')}** inherit from `Item`; "
               f"**{c.get('abstract_bases')}** are abstract base blueprints, leaving **{c.get('concrete_items')} concrete item blueprints**. "
               f"Excluding creature natural weapons ({c.get('natural_weapons')}), projectiles ({c.get('projectiles')}) and things that cannot be picked up, "
               f"**{c.get('loot_items')} are loot items** a character can actually carry. `[verified in game data {meta.get('generated')}]`")
    out.append("")
    out.append(f"> {meta.get('caveat')}")
    out.append("")
    out.append("| group | loot items |")
    out.append("|---|---|")
    for g, n in meta.get("loot_by_group", {}).items():
        out.append(f"| {g.replace('_', ' ')} | {n} |")
    out.append("")
    out.append("By tier (0 weakest, 8 strongest; `None` = untiered goods such as food and trade items): " + ", ".join(f"{k}: {v}" for k, v in meta.get("loot_by_tier", {}).items()))
    out.append("")
    profiles = {}
    seen = set()
    for bid in CANONICAL:
        t = build_templates.BUILD_TEMPLATES[bid]
        profiles[bid] = item_scoring.build_profile(t, cat)
    out.append("## What each build values (derived from its template, nothing hand-written)")
    out.append("")
    out.append("| build | trained weapon skills | caster | ranged | shield | weight class | stat priorities (3 = top) |")
    out.append("|---|---|---|---|---|---|---|")
    for bid, p in profiles.items():
        out.append(f"| {p['name']} | {', '.join(p['weapon_skills']) or '(none)'} | {'yes' if p['caster'] else ''} | {'yes' if p['ranged'] else ''} | {'yes' if p['wants_shield'] else ''} | "
                   f"{p['weight_class']} | {', '.join(f'{k} {v:g}' for k, v in p['stat_weights'].items())} |")
    out.append("")
    out.append("## Best items per build (top of each class, with score)")
    out.append("")
    for bid, p in profiles.items():
        out.append(f"### {p['name']}")
        out.append("")
        out.append(f"- **Melee:** {fmt(top(loot, p, 'melee_weapon', 5))}")
        out.append(f"- **Firearms/bows:** {fmt(top(loot, p, 'missile_weapon', 4))}")
        out.append(f"- **Shields:** {fmt(top(loot, p, 'shield', 3))}")
        for slot in ("Body", "Head", "Hands", "Feet", "Back"):
            out.append(f"- **{slot} armor:** {fmt(top(loot, p, 'armor', 3, slot))}")
        boosted = []
        for iid, it in loot.items():
            b = item_scoring.parse_boosts(((it.get("parts") or {}).get("EquipStatBoost") or {}).get("Boosts"))
            if b:
                s, kv, why = item_scoring.score_item(it, p)
                boosted.append((s, iid, it))
        boosted.sort(key=lambda r: -r[0])
        out.append(f"- **Stat/defence boosters:** {fmt(boosted[:4])}")
        out.append("")
    out.append("## Cross-build check: where does the same item rank?")
    out.append("")
    out.append("For a sanity check, the single best melee weapon and firearm for each build, side by side:")
    out.append("")
    out.append("| build | best melee | best firearm |")
    out.append("|---|---|---|")
    for bid, p in profiles.items():
        m = top(loot, p, "melee_weapon", 1)
        w = top(loot, p, "missile_weapon", 1)
        out.append(f"| {p['name']} | {fmt(m)} | {fmt(w)} |")
    out.append("")
    out.append("## Junk: what scores low for every build")
    out.append("")
    low = collections.defaultdict(list)
    for iid, it in loot.items():
        scores = [item_scoring.score_item(it, p) for p in profiles.values()]
        if it["group"] in item_scoring.EQUIPMENT_GROUPS:
            if max(s for s, kv, _ in scores) < 0:       # equipment is junk only if it would make EVERY build worse; otherwise it is merely outclassed by better gear
                low[it["group"]].append(it["name"])
        elif max(s + kv for s, kv, _ in scores) < item_scoring.KEEP_FLOOR:
            low[it["group"]].append(it["name"])
    out.append(f"Non-equipment items scoring below {item_scoring.KEEP_FLOOR:g} (score plus trade value) for **every** build, and equipment that would make every build worse, by group. "
               "Dropped only when the pack is under pressure; never anything equipped. Armor and weapons are otherwise never junk by themselves: they are replaced when something better is carried (`choose_equips`/`choose_drops`)."),
    out.append("")
    for g, names in sorted(low.items(), key=lambda kv: -len(kv[1])):
        out.append(f"- **{g.replace('_', ' ')}** ({len(names)}): " + ", ".join(sorted(set(names))[:12]) + (" ..." if len(set(names)) > 12 else ""))
    out.append("")
    out.append("## Placed unique items (not random loot)")
    out.append("")
    out.append("Marked by the game with `StaticObjectsTable:` tags: quest rewards and story artifacts. Excluded from the lists above.")
    out.append("")
    for iid, it in sorted(all_loot.items(), key=lambda kv: kv[1]["name"].lower()):
        if it.get("rare"):
            out.append(f"- {it['name']} ({it['group'].replace('_', ' ')}, tier {it.get('tier')})")
    out.append("")
    dest = os.path.join(ROOT, "docs", "ITEM_SCORES.md")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("wrote", dest, f"({len(out)} lines)")


if __name__ == "__main__":
    main()
