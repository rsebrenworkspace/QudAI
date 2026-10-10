"""Automatic post-mortem (HANDOFF issue 63): the facts of a death, written from the decision trace and the last game state, with no language model.

The chronicle is flavour and the ancestral lesson is a guess; this file is evidence. It answers the questions that used to need a manual trace read:
who was in view and how the engine rated them, what the HP did in the last turns, what the brain decided and why, and whether the last turns show
a pattern (fleeing while being hit, a position flip, one ability repeated). The "Observations" are rule-based and labelled as heuristics.
"""
import json
import os
import re

FLEE_PREFIXES = ("SPRINT_", "ACTIVATE_SPRINT", "USE_STAIRS_UP", "NAVIGATE_ZONE_EXIT")
HEAVY_HIT_FRACTION = 0.25


def load_trace_run(path, max_lines=6000):
    """The rows of the most recent run (the trace's turn counter `t` restarts at every brain start). Never raises."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-max_lines:]:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        return []
    start = 0
    for i in range(1, len(rows)):
        if rows[i].get("t", 0) < rows[i - 1].get("t", 0):
            start = i
    return rows[start:]


def classify(action):
    a = action or ""
    if a.startswith(FLEE_PREFIXES):
        return "flee/escape"
    if a.startswith("USE_ABILITY"):
        return "ability"
    if a == "REST" or a.startswith("REST"):
        return "rest"
    if a.startswith(("NAVIGATE", "AUTOEXPLORE", "MOVE_")):
        return "move/explore"
    return "other"


def observations(rows, max_hp):
    """Rule-based remarks about the last turns. Each is a heuristic, not a diagnosis."""
    obs = []
    tail = rows[-30:]
    if len(tail) >= 2 and max_hp:
        drops = [(tail[i]["t"], tail[i - 1].get("hp", 0) - tail[i].get("hp", 0)) for i in range(1, len(tail))]
        t_big, big = max(drops, key=lambda d: d[1])
        if big > 0:
            pct = round(100 * big / max_hp)
            obs.append(f"Largest single-turn HP loss in the last {len(tail)} turns: {big} ({pct}% of max HP) arriving at turn {t_big}." + (" A burst this large can end a run in two hits." if pct >= HEAVY_HIT_FRACTION * 100 else ""))
    fled_hit = 0
    for i in range(1, len(tail)):
        if classify(tail[i - 1].get("action")) == "flee/escape" and tail[i].get("hp", 0) < tail[i - 1].get("hp", 0):
            fled_hit += 1
    if fled_hit >= 1:
        obs.append(f"He took damage on {fled_hit} turn(s) right after a flee action: running did not shake the attacker.")
    rested = [r for r in tail if r.get("action") == "REST" and r.get("combat")]
    if rested:
        obs.append(f"He chose REST {len(rested)} time(s) while the combat flag was set.")
    last10 = rows[-10:]
    cells = {tuple(r.get("pos", ())) for r in last10}
    if len(last10) >= 10 and len(cells) <= 3:
        obs.append(f"Position flip: the last {len(last10)} turns used only {len(cells)} cell(s) {sorted(cells)}.")
    abil = [r.get("action") for r in tail if str(r.get("action", "")).startswith("USE_ABILITY")]
    if abil:
        top = max(set(abil), key=abil.count)
        if abil.count(top) >= 4:
            obs.append(f"One ability dominated: {top} x{abil.count(top)} in the last {len(tail)} turns.")
    hp_first = tail[0].get("hp") if tail else None
    if hp_first and max_hp and hp_first >= 0.9 * max_hp and tail[-1].get("hp", 0) <= 0.3 * max_hp:
        obs.append(f"He went from {hp_first}/{max_hp} HP to {tail[-1].get('hp')} within {len(tail)} turns.")
    return obs


def build_postmortem(death_data, last_state, rows, generation=None):
    """Markdown text. `last_state` is the last exported game state (dict or None); `rows` the decision-trace rows of the run."""
    death_data = death_data or {}
    last_state = last_state or {}
    max_hp = last_state.get("max_hp") or 0
    name = death_data.get("player_name", "?")
    out = [f"# Post-mortem: {name}" + (f" (Gen {generation})" if generation else ""), ""]
    out.append(f"- Level {death_data.get('level', last_state.get('level', '?'))}, {death_data.get('turns', '?')} turns, zone: {death_data.get('zone', last_state.get('zone_name', '?'))}")
    out.append(f"- Cause: {death_data.get('death_reason', '?')}")
    models = sorted({str(r.get("model")) for r in rows if r.get("model")})
    if models:
        out.append(f"- Combat model(s) this run: {', '.join(models)}")
    if last_state.get("psychic_glimmer") is not None:
        out.append(f"- Psychic glimmer {last_state.get('psychic_glimmer')} (the engine's number; -1 means the mod could not read it). Hunters are placed when a new zone is entered, more likely with high glimmer (BACKLOG B25).")
    out.append(f"- Final HP {last_state.get('hp', '?')}/{max_hp or '?'} | effects: {', '.join(last_state.get('effects', [])) or 'none'} | position ({last_state.get('x', '?')}, {last_state.get('y', '?')}) z={last_state.get('z', '?')}")
    out.append("")

    ents = last_state.get("visible_entities") or []
    foes = sorted([e for e in ents if e.get("is_enemy")], key=lambda e: e.get("dist", 999))
    pets = [e for e in ents if e.get("is_companion")]
    out.append("## Who was in view at the end")
    if foes:
        out.append("| hostile | dist | dir | engine rating | level | line of sight | psychic hunter |")
        out.append("|---|---|---|---|---|---|---|")
        for e in foes[:12]:
            out.append(f"| {str(e.get('name')).replace('|', '/')} | {e.get('dist')} | {e.get('dir')} | {e.get('difficulty')} | {e.get('level')} | {e.get('has_los')} | {'YES' if e.get('psychic_hunter') else ''} |")
    else:
        out.append("No hostile in the last exported state.")
    if pets:
        out.append("")
        out.append("Companions: " + ", ".join(f"{str(p.get('name')).replace('|', '/')} (dist {p.get('dist')})" for p in pets))
    abil = last_state.get("abilities") or []
    if abil:
        out.append("")
        out.append("Abilities: " + "; ".join(f"{a.get('name')} cd {a.get('cooldown')}" for a in abil))
    out.append("")

    tail = rows[-25:]
    out.append("## HP and decisions, last turns")
    if tail:
        out.append("| turn | pos | HP | combat | decision | why |")
        out.append("|---|---|---|---|---|---|")
        prev = None
        for r in tail:
            hp = r.get("hp", "?")
            mark = ""
            if prev is not None and isinstance(hp, (int, float)) and isinstance(prev, (int, float)) and hp < prev:
                mark = f" (-{prev - hp})"
            prev = hp
            reason = re.sub(r"\s+", " ", str(r.get("reason", "")))[:110].replace("|", "/")
            out.append(f"| {r.get('t')} | {r.get('pos')} | {hp}{mark} | {'C' if r.get('combat') else ''} | {r.get('action')} | {reason} |")
    else:
        out.append("No decision trace found for this run.")
    out.append("")

    last30 = rows[-30:]
    counts = {}
    for r in last30:
        counts[classify(r.get("action"))] = counts.get(classify(r.get("action")), 0) + 1
    if counts:
        out.append("## Decision mix, last %d turns" % len(last30))
        out.append(", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
        out.append("")

    obs = observations(rows, max_hp)
    out.append("## Observations (heuristics, not diagnoses)")
    out.extend([f"- {o}" for o in obs] or ["- Nothing in the last turns matched a known pattern."])
    out.append("")
    return "\n".join(out)


def write_postmortem(directory, death_data, last_state, rows, generation=None, timestamp=None):
    """Writes the post-mortem next to the chronicles and returns its path."""
    import time
    safe = re.sub(r"[^\w-]", "_", str((death_data or {}).get("player_name", "Nomad")))
    path = os.path.join(directory, f"Postmortem_Gen{generation or 0}_{safe}_{timestamp or int(time.time())}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_postmortem(death_data, last_state, rows, generation))
    return path
