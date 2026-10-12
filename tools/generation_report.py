"""Generation report: what the lives of the agent have looked like (human, 2026-10-12: "death of a character is a mechanic of roguelike games ... learn from the mistakes";
HANDOFF issue 172). Reads the chronicles the game writes after each death (`chronicles/Chronicle_Gen*.md`, front matter) and the death ledger (`data/death_ledger.json`,
kept by hand), and prints: the baseline (median level and turns, best life), the last N lives against the earlier ones, the cause classes and which repeat, and the deaths nobody
has classified yet. Read-only; never writes. `python tools/generation_report.py [--last 10]`.

A death is classified into one of four kinds, so that only some of them become code (see docs/DECISIONS.md, "Calibration note"):
  bug       a loop or a defect: fix it.
  gap       a rule that was missing and the death repeated or was clearly avoidable: build the rule.
  decision  a choice a better agent could have made: it belongs in the agent's memory (ancestral wisdom), not in code.
  luck      accept it.
  lab       a deliberate test run (a wished creature, a retry from a saved state): not a real death.
"""
import json
import os
import re
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_HERE)
CHRONICLE_DIR = os.path.join(REPO, "chronicles")
LEDGER_PATH = os.path.join(REPO, "data", "death_ledger.json")
KINDS = ("bug", "gap", "decision", "luck", "lab")

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
    """[{gen, name, root, level, turns, place, cause, cls, category, date}] sorted by generation. A chronicle that cannot be read is skipped."""
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
                         "category": fm.get("category", ""), "date": fm.get("date_recorded", "")})
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


def _stats(rows):
    if not rows:
        return {"lives": 0}
    lv = [r["level"] for r in rows]
    tn = [r["turns"] for r in rows]
    return {"lives": len(rows), "median_level": statistics.median(lv), "median_turns": int(statistics.median(tn)), "best_level": max(lv), "longest": max(tn)}


def _fmt_stats(label, s):
    if not s.get("lives"):
        return f"{label}: no lives"
    return f"{label}: {s['lives']} lives, median level {s['median_level']:g}, median {s['median_turns']} turns, best level {s['best_level']}, longest {s['longest']} turns"


def build_report(chron_dir=None, ledger_path=None, last=10):
    rows = mark_retries(parse_chronicles(chron_dir))
    ledger = load_ledger(ledger_path)
    if not rows:
        return "Generation report: no chronicles found (looked in " + str(chron_dir or CHRONICLE_DIR) + ")."
    for r in rows:
        led = ledger.get(r["gen"], {})
        r["kind"] = led.get("kind") or ""
        r["lcls"] = led.get("cls") or r["cls"]
        r["note"] = led.get("note", "")
        r["issue"] = led.get("issue", "")
    out = []
    chars = 1 + sum(1 for r in rows[1:] if not r.get("retry_of"))
    out.append(f"== Generation report: {len(rows)} lives of {chars} characters (a life with the same name as the one before it is a retry), generations {rows[0]['gen']} to {rows[-1]['gen']} ==")
    labs = sum(1 for r in rows if (ledger.get(r["gen"], {}).get("kind") == "lab"))
    out.append(f"({len(ledger)} of {len(rows)} lives are in the ledger, {labs} marked as labs; many recent lives were lab runs, so the trend below is only fair once those are marked.)")
    out.append(_fmt_stats("All lives     ", _stats(rows)))
    recent, earlier = rows[-last:], rows[:-last]
    out.append(_fmt_stats(f"Earlier lives ", _stats(earlier)))
    out.append(_fmt_stats(f"Last {len(recent):<2} lives  ", _stats(recent)))
    out.append("")
    out.append("== Lives (newest last) ==")
    out.append("gen  name                    lvl  turns  cause class          kind      note")
    for r in rows[-max(last, 20):]:
        tag = f"retry of {r['retry_of']}" if r.get("retry_of") else ""
        note = (r["note"] or tag)[:48]
        out.append(f"{r['gen']:<4} {r['root'][:22]:<23} {r['level']:<4} {r['turns']:<6} {r['lcls'][:19]:<20} {(r['kind'] or '?'):<9} {note}")
    out.append("")
    real = [r for r in rows if r["kind"] != "lab"]
    counts = {}
    for r in real:
        counts.setdefault(r["lcls"], []).append(r)
    out.append("== Causes (labs and retries left out) ==")
    for cls, rs in sorted(counts.items(), key=lambda kv: -len(kv[1])):
        fixed = sum(1 for x in rs if x["kind"] in ("gap", "bug") and x["issue"])
        out.append(f"{len(rs):>3}  {cls}" + (f"  ({fixed} with a fix recorded)" if fixed else ""))
    repeats = [cls for cls, rs in counts.items() if len(rs) >= 2 and not all(x["kind"] in ("gap", "bug") and x["issue"] for x in rs) and cls not in ("unknown",)]
    out.append("")
    out.append("== Repeated causes with no recorded fix (candidates for a rule, DECISIONS calibration note) ==")
    out.extend([f"  {c} ({len(counts[c])} lives, generations {', '.join(str(x['gen']) for x in counts[c])})" for c in sorted(repeats, key=lambda c: -len(counts[c]))] or ["  none"])
    unclassified = [r for r in real if not r["kind"]]
    out.append("")
    out.append(f"== Not classified yet: {len(unclassified)} of {len(real)} real deaths (add them to data/death_ledger.json: kind, cls, note, issue) ==")
    out.extend([f"  Gen {r['gen']} {r['root']} (level {r['level']}, {r['turns']} turns): {r['cause'][:70]}" for r in unclassified[-12:]])
    return "\n".join(out)


if __name__ == "__main__":
    n = 10
    if "--last" in sys.argv:
        try:
            n = int(sys.argv[sys.argv.index("--last") + 1])
        except (ValueError, IndexError):
            pass
    print(build_report(last=n))
