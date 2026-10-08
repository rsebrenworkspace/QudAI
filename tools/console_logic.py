"""Pure logic behind the QudAI console (tools/qudai_console.py): no GUI code here, so dry_run.py can test it offline.

Everything reads files; the only writes are the brain's stdin (pause/resume) and the ancestral-wisdom approvals, both through the
same code the command line uses. Paths come from the same environment variable as brain.py (QUDAI_EXCHANGE_DIR) so tests use a temp dir."""
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

EXCHANGE_DIR = os.environ.get("QUDAI_EXCHANGE_DIR") or r"C:\Users\rsebr\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI"


def game_dir(exchange_dir=None):
    """The CavesOfQud data folder is the parent of the exchange folder (build_log.txt, Player.log, game_log.txt, Mods live there)."""
    return os.path.dirname(os.path.abspath(exchange_dir or EXCHANGE_DIR))


def read_text(path, max_bytes=2_000_000):
    """Last `max_bytes` of a text file, or '' when it is missing. Never raises."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def tail_lines(path, n=200, max_bytes=400_000):
    return read_text(path, max_bytes).splitlines()[-n:]


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def tail_jsonl(path, n=200):
    """The last n parsable JSON objects of a .jsonl file (a half-written last line is skipped)."""
    out = []
    for line in tail_lines(path, n + 5):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out[-n:]


def age_text(path):
    try:
        secs = max(0, int(time.time() - os.path.getmtime(path)))
    except OSError:
        return "missing"
    if secs < 90:
        return f"{secs}s ago"
    if secs < 5400:
        return f"{secs // 60} min ago"
    return f"{secs // 3600} h ago"


# ---------------------------------------------------------------------------
# Mod health
# ---------------------------------------------------------------------------
OK, WARN, BAD, UNKNOWN = "ok", "warn", "bad", "unknown"


def parse_build_log(text):
    """The game compiles the mod at launch. Look at the LAST 'Compiling' block: Success, or the error lines. -> (status, detail)"""
    if not text.strip():
        return UNKNOWN, "build_log.txt is missing or empty"
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if "Compiling" in l]
    block = lines[starts[-1]:] if starts else lines
    for l in block:
        if re.search(r"\berror\b|\bfailed\b", l, re.IGNORECASE) and "Success" not in l:
            return BAD, l.strip()[:300]
    if any("Success :)" in l for l in block):
        stamp = re.match(r"\[([^\]]+)\]", block[-1])
        return OK, "the mod compiled" + (f" (log written {stamp.group(1)})" if stamp else "")
    return WARN, "no 'Success :)' after the last compile; the game may still be building"


def parse_player_log(text):
    """-> list of (name, status, detail) from the [QudAI] startup lines in Player.log."""
    checks = []
    if not text.strip():
        return [("Player.log", UNKNOWN, "missing or empty; start the game")]
    if "[QudAI] PlayerTurn patch ACTIVE" in text:
        checks.append(("PlayerTurn patch", OK, "active"))
    else:
        checks.append(("PlayerTurn patch", BAD, "no 'PlayerTurn patch ACTIVE' line: the patch failed or the mod did not load"))
    m = re.findall(r"Patch check: (\d+)/(\d+) applied", text)
    if m:
        got, want = int(m[-1][0]), int(m[-1][1])
        checks.append(("Harmony patches", OK if got == want else BAD, f"{got}/{want} applied"))
    else:
        checks.append(("Harmony patches", UNKNOWN, "no 'Patch check' line yet"))
    errs = [l for l in text.splitlines() if "[QudAI" in l and re.search(r"exception|\berror\b|failed(?!=0)", l, re.IGNORECASE)]   # "failed=0" is a success report
    if errs:
        checks.append(("Mod errors", WARN, f"{len(errs)} line(s); last: {errs[-1].strip()[:200]}"))
    else:
        checks.append(("Mod errors", OK, "none logged by the mod"))
    return checks


def deployed_matches_repo(repo_dir=None, mods_dir=None):
    """Is the C# the game compiled the same as the repo's? (Forgetting `python sync_mod.py deploy` is a classic.)"""
    repo_cs = os.path.join(repo_dir or REPO, "mod", "QudAIBrain", "AIBrainPart.cs")
    game_cs = os.path.join(mods_dir or os.path.join(game_dir(), "Mods", "QudAIBrain"), "AIBrainPart.cs")
    try:
        a = open(repo_cs, "rb").read()
        b = open(game_cs, "rb").read()
    except OSError as e:
        return UNKNOWN, f"cannot compare ({e.__class__.__name__})"
    if a == b:
        return OK, "the game's mod folder matches the repo"
    return WARN, "the repo C# differs from the game's mod folder: run  python sync_mod.py deploy  and restart the game"


def mod_health(exchange_dir=None):
    gd = game_dir(exchange_dir)
    ex = exchange_dir or EXCHANGE_DIR
    rows = []
    status, detail = parse_build_log(read_text(os.path.join(gd, "build_log.txt")))
    rows.append(("Mod compile", status, detail))
    rows.extend(parse_player_log(read_text(os.path.join(gd, "Player.log"))))
    rows.append(("Mod deployed", *deployed_matches_repo(mods_dir=os.path.join(gd, "Mods", "QudAIBrain"))))
    st = os.path.join(ex, "last_state.json")
    if os.path.exists(st):
        secs = time.time() - os.path.getmtime(st)
        rows.append(("Game state", OK if secs < 30 else WARN, f"last_state.json updated {age_text(st)}" + ("" if secs < 30 else "; the game is idle, paused or closed")))
    else:
        rows.append(("Game state", UNKNOWN, "no last_state.json yet"))
    rows.append(("AI switch", OK if flag_on(ex) else WARN, "ENGAGED (active.flag present)" if flag_on(ex) else "paused (no active.flag): the game plays itself no more"))
    return rows


def flag_on(exchange_dir=None):
    return os.path.exists(os.path.join(exchange_dir or EXCHANGE_DIR, "active.flag"))


# ---------------------------------------------------------------------------
# Readable views
# ---------------------------------------------------------------------------
def describe_state(s):
    """last_state.json -> a short readable report."""
    if not isinstance(s, dict) or not s:
        return "No state yet. Start the game and engage the AI."
    L = []
    L.append(f"{s.get('genotype', '?')} {s.get('subtype') or s.get('calling') or ''}   level {s.get('level', '?')}   HP {s.get('hp', '?')}/{s.get('max_hp', '?')}   XP {s.get('xp', '?')}")
    L.append(f"Zone: {s.get('zone_name') or '?'}  ({s.get('zone_id') or '?'})   cell {s.get('x', '?')},{s.get('y', '?')}   unexplored cells: {s.get('unexplored_cells', '?')}")
    L.append(f"Hunger: {s.get('hunger_level', '?')}   food: {s.get('food_count', '?')}   water drams: {s.get('water_drams', '?')}   companion: {'yes' if s.get('has_companion') else 'no'}")
    L.append(f"Hostiles nearby: {s.get('hostiles_nearby')}   adjacent: {s.get('hostiles_adjacent')}   on fire: {s.get('is_on_fire')}")
    L.append(f"Carrying {s.get('carry_weight', '?')} of {s.get('max_carry_weight', '?')}   avoid-tagged vines: {s.get('avoid_tagged', 0)}")
    if s.get("equipped_summary"):
        L.append(f"Wearing: {s['equipped_summary']}")
    lia = s.get("last_inventory_action")
    if lia:
        L.append(f"Last inventory action: {lia.get('kind')} ok={lia.get('ok')} failed={lia.get('failed')} at {lia.get('zone')} {lia.get('x')},{lia.get('y')}")
    ab = s.get("abilities") or []
    if ab:
        L.append("")
        L.append("Abilities:")
        for a in ab:
            if isinstance(a, dict):
                cd = a.get("cooldown") or a.get("cooldown_turns") or 0
                L.append(f"  {a.get('name', a.get('command', '?'))}: " + ("ready" if not cd else f"cooldown {cd}"))
    inv = s.get("inventory") or []
    if inv:
        L.append("")
        L.append("Inventory:")
        for i in inv:
            L.append(f"  {'*' if i.get('equipped') else ' '} {i.get('name')} x{i.get('count', 1)}  ({i.get('weight', 0)} lb)")
    return "\n".join(L)


def describe_quests(state):
    """The mod's read-only quest log (state `quests`, `finished_quests`) as readable text for the console."""
    quests = (state or {}).get("quests") or []
    done = (state or {}).get("finished_quests") or []
    if not quests and not done:
        return "No quests in the last state (none taken yet, or the game has not exported the log)."
    L = []
    for q in quests:
        steps = q.get("steps") or []
        fin = sum(1 for s in steps if s.get("finished"))
        L.append(f"{'[done] ' if q.get('finished') else ''}{q.get('name')}  (level {q.get('level')}, {fin}/{len(steps)} steps"
                 + (f", from {q.get('giver')}" if q.get("giver") else "") + ")")
        for s in steps:
            mark = "x" if s.get("finished") else ("!" if s.get("failed") else " ")
            L.append(f"   [{mark}] {s.get('name')}  ({s.get('xp', 0)} XP){'  optional' if s.get('optional') else ''}")
            if s.get("text") and not s.get("finished"):
                L.append(f"        {s.get('text')}")
        if q.get("giver_place"):
            L.append(f"   given at {q.get('giver_place')} {q.get('giver_zone') or ''}")
    if done:
        L.append("")
        L.append("Finished: " + ", ".join(str(d) for d in done))
    return "\n".join(L)


def format_trace_row(r):
    reason = re.sub(r"^\[LLM in [\d.]+s\]\s*", "", str(r.get("reason") or ""))
    return f"{r.get('t', '?'):>5}  HP{str(r.get('hp', '?')):>4}  {str(r.get('action', '')):<34} {reason[:110]}"


def trace_text(path, n=150):
    return "\n".join(format_trace_row(r) for r in tail_jsonl(path, n)) or "No decision trace yet."


DANGEROUS = ("Tough", "Very Tough", "Impossible")


def threat_summary(state, limit=5):
    """One line about the hostiles in view: name, difficulty relative to his level (the mod's own Trivial..Impossible scale), distance.
    -> (text, worst) where worst is 'danger' when any is Tough or worse, 'calm' when none are in view, else 'watch'."""
    ents = [e for e in (state or {}).get("visible_entities") or [] if e.get("is_enemy")]
    if not ents:
        return "No hostiles in view.", "calm"
    ents.sort(key=lambda e: e.get("dist", 999))
    parts = []
    for e in ents[:limit]:
        diff = e.get("difficulty", "?")
        parts.append(f"{'!! ' if diff in DANGEROUS else ''}{e.get('name', '?')} [{diff}] {e.get('dist', '?')} tiles{' (rooted)' if e.get('is_stationary') else ''}")
    more = f"  (+{len(ents) - limit} more)" if len(ents) > limit else ""
    worst = "danger" if any(e.get("difficulty") in DANGEROUS for e in ents) else "watch"
    return "Hostiles: " + "  |  ".join(parts) + more, worst


def feed_tag(row, prev_hp=None):
    """Colour class of one decision row in the live feed: what an observer wants to notice. 'hp' (he lost HP), 'loop' (the loop breaker stepped in:
    erratic movement), 'flee' (leaving or retreating), 'ability', 'loot', or ''."""
    action = str(row.get("action") or "")
    reason = str(row.get("reason") or "")
    hp = row.get("hp")
    if "Loop Breaker" in reason:
        return "loop"
    if isinstance(hp, (int, float)) and isinstance(prev_hp, (int, float)) and hp < prev_hp:
        return "hp"
    if action.startswith("NAVIGATE_ZONE_EXIT") or "retreat" in reason.lower() or "flee" in reason.lower():
        return "flee"
    if action.startswith("USE_ABILITY"):
        return "ability"
    if action == "LOOT" or reason.startswith("Loot:"):
        return "loot"
    return ""


def feed_rows(path, n=60):
    """The latest n decision rows as (text, tag) pairs; the tag needs the previous row's HP."""
    rows = tail_jsonl(path, n + 1)
    out, prev = [], None
    for r in rows:
        out.append((format_trace_row(r), feed_tag(r, prev)))
        prev = r.get("hp")
    return out[-n:]


def colour_tag(line):
    """Which colour tag a brain console line gets in the GUI."""
    for tag in ("[INVENTORY]", "[AVOID]", "[LOOT]", "[STAND AND FIGHT]", "[Loop Breaker]", "[AI ENGAGED]", "[AI PAUSED]", "Traceback", "Error"):
        if tag in line:
            return tag
    return ""


def filter_lines(lines, needle):
    needle = (needle or "").strip().lower()
    return [l for l in lines if needle in l.lower()] if needle else list(lines)


# ---------------------------------------------------------------------------
# Review: runs, lessons, drop log
# ---------------------------------------------------------------------------
def list_runs(runs_dir):
    out = []
    try:
        names = sorted(os.listdir(runs_dir), reverse=True)
    except OSError:
        return out
    for n in names:
        d = read_json(os.path.join(runs_dir, n))
        t = (d or {}).get("telemetry") or {}
        if t:
            out.append({"file": n, "name": t.get("player_name"), "level": t.get("level"), "turns": t.get("turns"), "zone": t.get("zone"), "death": t.get("death_reason")})
    return out


def find_chronicle_files(chronicles_dir, name):
    """Chronicle and post-mortem files whose name mentions the character (names contain the character's name)."""
    if not name:
        return []
    try:
        return sorted(os.path.join(chronicles_dir, f) for f in os.listdir(chronicles_dir) if str(name) in f)
    except OSError:
        return []


def lessons():
    import chronicler
    return chronicler.load_ancestral_wisdom()


def set_approval(generations, approve):
    """Same effect as `python tools/wisdom.py approve|reject N...`. Returns the generations that matched."""
    import chronicler
    wisdom = chronicler.load_ancestral_wisdom()
    changed = []
    for w in wisdom:
        if w.get("generation") in set(generations):
            w["approved"] = bool(approve)
            changed.append(w["generation"])
    if changed:
        chronicler.save_ancestral_wisdom(wisdom)
    return changed


def drop_log_text(path):
    rows = tail_jsonl(path, 100)
    if not rows:
        return "No items dropped yet."
    return "\n".join(f"{r.get('zone')} ({r.get('x')},{r.get('y')})  {r.get('name') or r.get('item')}  x{r.get('count', 1)}  {r.get('reason', '')}" for r in rows)


def pause_resume_bytes():
    """The brain toggles on a line from its console (input_listener), so the console sends one newline to its stdin. Writing
    active.flag directly would desynchronise the brain's own ai_active variable from the file."""
    return b"\n"
