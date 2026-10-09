"""Odds of Proselytize by level gap, from memory/proselytize_log.jsonl (written by brain.py, BACKLOG B11).

    python tools/proselytize_report.py            the table
    python tools/proselytize_report.py --last 10  also the last 10 attempts

Gap = the target's level minus ours. The game's rule is "Ego + level attack vs. MA + level", so a target at or below our level adds nothing to its difficulty and each
level above adds one (ENGINE_INTERNALS 14.20). A bucket needs a handful of attempts before its rate means anything."""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG = os.path.join(HERE, "memory", "proselytize_log.jsonl")
BUCKETS = (("below our level (gap <= -1)", lambda g: g <= -1), ("same level (gap 0)", lambda g: g == 0), ("1 above", lambda g: g == 1), ("2 above", lambda g: g == 2),
           ("3 above", lambda g: g == 3), ("4 or more above", lambda g: g >= 4))


def load(path=DEFAULT_LOG):
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows


def summarize(rows):
    """-> list of (label, attempts, recruited) over the resolved attempts that have a gap, plus (unknown gap) and the totals."""
    res = [r for r in rows if r.get("outcome") in ("recruited", "not_recruited")]
    out = []
    for label, test in BUCKETS:
        sel = [r for r in res if isinstance(r.get("gap"), int) and test(r["gap"])]
        out.append((label, len(sel), sum(1 for r in sel if r["outcome"] == "recruited")))
    nogap = [r for r in res if not isinstance(r.get("gap"), int)]
    out.append(("gap unknown (target not listed)", len(nogap), sum(1 for r in nogap if r["outcome"] == "recruited")))
    return out


def format_report(rows, last=0):
    lines = [f"Proselytize log: {len(rows)} record(s), {sum(1 for r in rows if r.get('outcome') == 'unresolved')} unresolved", ""]
    lines.append(f"{'target level compared with ours':<36}{'tries':>7}{'recruited':>11}{'rate':>8}")
    for label, n, k in summarize(rows):
        lines.append(f"{label:<36}{n:>7}{k:>11}{(f'{100 * k // n}%' if n else '-'):>8}")
    hostile = [r for r in rows if r.get("outcome") in ("recruited", "not_recruited") and r.get("hostile") is True]
    calm = [r for r in rows if r.get("outcome") in ("recruited", "not_recruited") and r.get("hostile") is False]
    lines.append("")
    lines.append(f"hostile targets: {sum(1 for r in hostile if r['outcome'] == 'recruited')}/{len(hostile)} recruited;  calm targets: {sum(1 for r in calm if r['outcome'] == 'recruited')}/{len(calm)}")
    if last:
        lines.append("")
        for r in rows[-last:]:
            lines.append(f"{r.get('ts')}  {r.get('outcome'):<14} {str(r.get('target')):<24} L{r.get('target_level')} vs ours L{r.get('our_level')} (Ego {r.get('ego')}, gap {r.get('gap')}, {'hostile' if r.get('hostile') else 'calm'})")
    return "\n".join(lines)


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--last") + 1]) if "--last" in sys.argv else 0
    print(format_report(load(), n))
