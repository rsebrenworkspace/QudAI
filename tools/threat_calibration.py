"""Ranks the recorded deaths by the threat score (BACKLOG B12 stage 2): does the score put the things that killed us at the top?
Read-only. Usage: python tools/threat_calibration.py"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import creature_threat as ct  # noqa: E402

KILLER = re.compile(r"(?:killed|bitten to death|stung|crushed|slain|mauled|clawed|devoured|burned|shot|pierced|beaten)[^.]*? by (?:an?|the)\s+(.+?)(?: with | for |\.|$)")


def deaths():
    files = glob.glob(os.path.join(ROOT, "memory", "runs", "run_*.json")) + glob.glob(os.path.join(ROOT, "memory", "archive", "**", "run_*.json"), recursive=True)
    out = []
    for f in files:
        try:
            t = json.load(open(f, encoding="utf-8"))["telemetry"]
        except (OSError, ValueError, KeyError):
            continue
        reason = re.sub(r"@@|##|\|", "", str(t.get("death_reason", "")))
        m = KILLER.search(reason)
        out.append({"level": t.get("level") or 1, "killer": m.group(1).strip() if m else None, "reason": reason[:70]})
    return out


def ledger():
    try:
        return json.load(open(os.path.join(ROOT, "memory", "danger_ledger.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    cat = ct.load_catalog()
    led = ledger()
    rows, miss = [], []
    for d in deaths():
        if not d["killer"]:
            miss.append(d["reason"])
            continue
        e = ct.lookup(name=d["killer"], catalog=cat)
        if e is None:
            miss.append(d["killer"])
            continue
        # a starting character: the level he died at, with about 6 hit points per level plus a base of 15
        hp = 15 + 6 * int(d["level"])
        obs = None
        for bp, v in led.items():
            if str(v.get("name", "")).lower().split("[")[0].strip().endswith(str(e.get("name", "")).lower()) and v.get("hits"):
                obs = v["total_damage"] / float(v["hits"])
        r = ct.threat(e, int(d["level"]), hp, observed_per_hit=obs)
        rows.append((r["ratio"], d["killer"], d["level"], e.get("level"), e.get("hp"), r["their_dps"], r["cls"]))
    rows.sort(key=lambda x: -x[0])
    print("ratio  class      our L  their L/HP  dmg/turn  killer")
    for r in rows:
        print(f"{r[0]:5.2f}  {r[6]:<9}  {r[2]:>4}   {r[3]}/{r[4]:<6}   {r[5]:>6}   {r[1]}")
    if rows:
        calm = [r for r in rows if r[6] in ("trivial", "easy")]
        print(f"\n{len(rows)} deaths scored; {len(calm)} rated trivial or easy although they killed us (that is the miss list).")
    for m in miss:
        print("no catalogue match:", m)


if __name__ == "__main__":
    main()
