"""Generation report: what the lives of the agent have looked like (human, 2026-10-12: "death of a character is a mechanic of roguelike games ... learn from the mistakes";
HANDOFF issues 172 and 173). The reading of chronicles, the ledger and the collection switch lives in death_stats.py (repo root); this prints: the baseline (median level and turns, best
life), the last N lives against the earlier ones, the cause classes and which repeat, the deaths nobody has classified yet, and which lives COUNT as evidence for the agent (the lives that
ended while data collection was ON). Read-only; never writes. `python tools/generation_report.py [--last 10]`.

A death is classified into one of four kinds, so that only some of them become code (see docs/DECISIONS.md, "Calibration note"):
  bug       a loop or a defect: fix it.
  gap       a rule that was missing and the death repeated or was clearly avoidable: build the rule.
  decision  a choice a better agent could have made: it belongs in the agent's memory (ancestral wisdom), not in code.
  luck      accept it.
  lab       a deliberate test run (a wished creature, a retry from a saved state): not a real death.
"""
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from death_stats import (CHRONICLE_DIR, LEDGER_PATH, KINDS, clean_cause, cause_class, _front_matter, _name_root, parse_chronicles, load_ledger, mark_retries,  # noqa: E402,F401
                         collection_state, counted_lives, killer_stats)


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
    cs = collection_state()
    counted = counted_lives(rows, ledger)
    out.append(f"Data collection: {'ON' if cs['collecting'] else 'OFF'}" + (f" since generation {cs['since_generation']}" if cs["collecting"] and cs["since_generation"] else "")
               + f". {len(counted)} of {len(rows)} lives count as evidence for the agent (only lives that ended while it was ON); the rest are history.")
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
