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
    rows.append(("LLM context", *llm_headroom()))
    rows.append(("AI switch", OK if flag_on(ex) else WARN, "ENGAGED (active.flag present)" if flag_on(ex) else "paused (no active.flag): the game plays itself no more"))
    return rows


def llm_headroom(trace_path=None, n=400):
    """How full the model's context window gets, from the `llm` block of recent trace rows (brain.py LAST_LLM_USAGE): (status, text).
    Warns when the largest prompt used more than 60 percent of the window."""
    rows = tail_jsonl(trace_path or os.path.join(REPO, "memory", "decision_trace.jsonl"), n)
    used = [(r["llm"].get("prompt_tokens"), r["llm"].get("ctx")) for r in rows if isinstance(r.get("llm"), dict) and r["llm"].get("prompt_tokens")]
    if not used:
        return UNKNOWN, "no model calls with token counts in the recent trace yet (restart the brain after updating it)"
    toks = sorted(u[0] for u in used)
    p95 = toks[min(len(toks) - 1, int(len(toks) * 0.95))]
    ctx = next((u[1] for u in reversed(used) if u[1]), None)
    text = f"{len(toks)} calls: largest prompt {toks[-1]} tokens, p95 {p95}, median {toks[len(toks) // 2]}"
    if not ctx:
        return UNKNOWN, text + "; the window size is not known (LM Studio did not report it)"
    share = toks[-1] / float(ctx)
    text += f"; window {ctx} tokens ({share:.0%} used at most)"
    if share > 0.6:
        return WARN, text + ". Raise the context length in LM Studio (reload the model) before adding more to the prompt."
    return OK, text


# ---------------------------------------------------------------------------
# Game control: start and stop Caves of Qud from the console (HANDOFF issue 100)
# ---------------------------------------------------------------------------
STEAM_APP_ID = 333640                 # appmanifest_333640.acf: "Caves of Qud" [verified in the Steam library folder]
GAME_EXE = "CoQ.exe"                  # the game folder holds CoQ.exe [verified]


def _run_text(cmd):
    """Runs a command without a console window and returns (exit code, combined output)."""
    import subprocess
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    p = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags, timeout=15)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def game_running(runner=None):
    """True while CoQ.exe is a running process (tasklist). `runner(cmd) -> (code, text)` is injectable for tests."""
    try:
        _code, text = (runner or _run_text)(["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/NH"])
        return GAME_EXE.lower() in text.lower()
    except Exception:
        return False


def steam_launch_url(app_id=STEAM_APP_ID):
    return f"steam://rungameid/{app_id}"


def start_game(opener=None):
    """Asks Steam to launch the game (it starts Steam if needed). -> (ok, text). `opener(url)` is injectable for tests."""
    try:
        if opener is None:
            os.startfile(steam_launch_url())            # Windows: hands the steam:// address to Steam
        else:
            opener(steam_launch_url())
        return True, "Asked Steam to start Caves of Qud."
    except Exception as e:                              # noqa: BLE001
        return False, f"Could not start the game: {e}"


def stop_game(force=False, runner=None):
    """Closes the game: a polite close request first (the game can save), `force=True` ends it at once. -> (ok, text)."""
    try:
        cmd = ["taskkill", "/IM", GAME_EXE] + (["/F"] if force else [])
        code, text = (runner or _run_text)(cmd)
        return code == 0, (text.strip() or ("closed" if code == 0 else f"taskkill exit {code}"))
    except Exception as e:                              # noqa: BLE001
        return False, f"Could not stop the game: {e}"


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


def threat_class(entity, state):
    """The catalogue's own threat class for one visible creature (creature_threat.py, display only), or '' when it is not in the catalogue."""
    try:
        import creature_threat as ct
        entry = ct.lookup(blueprint=entity.get("blueprint"), name=entity.get("name"))
        if entry is None:
            return ""
        s = state or {}
        r = ct.threat(entry, int(s.get("level") or 1), int(s.get("hp") or s.get("max_hp") or 20), enemy_hp=entity.get("hp") or None, us=s)
        return r["cls"]
    except Exception:
        return ""


def effective_hostiles(state):
    """The hostiles in view with the rating the BRAIN uses: the engine's difficulty, raised by the danger ledger (what that creature type has actually done to us, relative to
    the current max HP; danger_ledger.apply). A raised rating carries `difficulty_engine` (the engine's own). The console used to show only the engine's number, so a giant amoeba
    the engine called Average and the ledger called Impossible looked harmless while the brain's lethal guard was reacting to it (human run 2026-10-09, HANDOFF issue 95)."""
    ents = [e for e in (state or {}).get("visible_entities") or [] if e.get("is_enemy")]
    try:
        import danger_ledger
        danger_ledger.reset_cache()            # the brain writes the file while the console runs
        return danger_ledger.apply(ents, (state or {}).get("max_hp"))
    except Exception:
        return ents


def threat_summary(state, limit=5):
    """One line about the hostiles in view: name, difficulty relative to his level (the mod's own Trivial..Impossible scale, raised by the danger ledger exactly as the brain does,
    with the engine's own rating in brackets when they differ), distance, and the catalogue's class.
    -> (text, worst) where worst is 'danger' when any is Tough or worse, 'calm' when none are in view, else 'watch'."""
    ents = effective_hostiles(state)
    if not ents:
        return "No hostiles in view.", "calm"
    ents.sort(key=lambda e: e.get("dist", 999))
    parts = []
    for e in ents[:limit]:
        diff = e.get("difficulty", "?")
        est = threat_class(e, state)
        raised = f" (engine: {e['difficulty_engine']})" if e.get("difficulty_engine") and e.get("difficulty_engine") != diff else ""
        parts.append(f"{'!! ' if diff in DANGEROUS else ''}{e.get('name', '?')} [{diff}{raised}]{' ~' + est if est else ''} {e.get('dist', '?')} tiles{' (rooted)' if e.get('is_stationary') else ''}")
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


# ---------------------------------------------------------------------------
# Lab tab: wish scenarios (BACKLOG B13). Cards only: nothing here talks to the game.
# ---------------------------------------------------------------------------
WISH_SCENARIOS_PATH = os.path.join(REPO, "data", "wish_scenarios.json")
LAB_LOG_PATH = os.path.join(REPO, "memory", "lab_runs.jsonl")
CONFIDENCE_TEXT = {"verified": "verified in game", "documented": "documented in the game's WishCommands.xml", "named": "name recognised by the wish handler; effect not read (tell me what it did)"}


def load_wish_scenarios(path=None):
    doc = read_json(path or WISH_SCENARIOS_PATH, {}) or {}
    return [s for s in doc.get("scenarios", []) if isinstance(s, dict) and s.get("id") and s.get("wishes") is not None]


def xp_for_level(level):
    """XP needed to reach `level`: floor(15 x level^3) + 100, 0 for level 1 (ENGINE_INTERNALS 14.16, verified in code and against a live character)."""
    return 0 if level <= 1 else 15 * level ** 3 + 100


def xp_wish_for_level(target_level, current_xp):
    """The wish that adds the XP missing for `target_level`, or '' when the character is already there. `xp:N` adds N XP (the game's own menu: 'Gain 25,000 XP' is xp:25000)."""
    need = xp_for_level(int(target_level)) - int(current_xp or 0)
    return f"xp:{need}" if need > 0 else ""


def wish_lines(scenario, level=None, current_xp=0):
    """The wish commands of a scenario, ready to type; the xp placeholder is filled from the chosen level and the current XP."""
    out = []
    for w in scenario.get("wishes", []):
        cmd = str(w.get("cmd", ""))
        if "<computed>" in cmd:
            cmd = xp_wish_for_level(level, current_xp) if level else ""
        if cmd:
            out.append(cmd)
    return out


def scenario_text(scenario, level=None, current_xp=0):
    L = [scenario.get("title", scenario.get("id", "")), "", "Why: " + str(scenario.get("why", "")), "", "Set up:"]
    L += [f"  {i + 1}. {s}" for i, s in enumerate(scenario.get("setup", []))]
    L += ["", "Wish for (Ctrl+W in the game, one per prompt):"]
    for w in scenario.get("wishes", []):
        cmd = str(w.get("cmd", ""))
        if "<computed>" in cmd:
            cmd = xp_wish_for_level(level, current_xp) or "(already at or above that level)" if level else "(choose a level below)"
        L.append(f"  {cmd}")
        L.append(f"      [{CONFIDENCE_TEXT.get(w.get('confidence'), w.get('confidence', ''))}] {w.get('note', '')}")
    L += ["", "Watch for:"] + [f"  - {x}" for x in scenario.get("watch", [])]
    if scenario.get("tests"):
        L += ["", f"Covers: {scenario['tests']}"]
    L += ["", "The prompt takes ONE line: copy and enter one wish at a time (the Copy button gives you the next one each time).",
          "Wishes are cheats: use a throwaway character, pause the AI first, and archive the death it leaves behind from the Memory tab if you do not want its lesson."]
    return "\n".join(L)


def log_lab_use(scenario_id, note="", path=None):
    """Appends 'a lab scenario was used now' to memory/lab_runs.jsonl so later analysis can tell wished runs from real ones. Returns the record."""
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "scenario": scenario_id, "note": note}
    p = path or LAB_LOG_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + chr(10))
    return rec


# ---------------------------------------------------------------------------
# Memory tab: every stored memory, with approve / archive / delete
# ---------------------------------------------------------------------------
MEMORY_KINDS = ("lesson", "chronicle", "postmortem", "run", "lab", "data")
MEMORY_KIND_NAMES = {"lesson": "Ancestral lessons", "chronicle": "Chronicles", "postmortem": "Post-mortems", "run": "Run records",
                     "lab": "Model lab results", "data": "Live data (used by the brain: view only)"}
DATA_FILES = ("ability_stats.json", "danger_ledger.json", "exit_choices.jsonl", "item_drops.jsonl", "decision_trace.jsonl", "decision_trace.jsonl.1", "generation_counter.json")
VIEW_ONLY_KINDS = ("data",)


def _mem_dir():
    return os.path.join(REPO, "memory")


def _chron_dir():
    return os.path.join(REPO, "chronicles")


def _wisdom_dir():
    import chronicler
    return os.path.dirname(chronicler.WISDOM_FILE)


def _archived_lessons_path():
    return os.path.join(_wisdom_dir(), "archive", "ancestral_wisdom_archived.json")


def list_memory_items(mem_dir=None, chron_dir=None):
    """Every stored memory as dicts {kind, key, title, path, gen, approved, safe}, grouped in MEMORY_KINDS order, newest first within a group.
    `safe` is False for the live data files the brain reads, which are shown but never archived or deleted from here."""
    mem_dir = mem_dir or _mem_dir()
    chron_dir = chron_dir or _chron_dir()
    items = []
    for w in sorted(lessons(), key=lambda x: x.get("generation") or 0, reverse=True):
        gen = w.get("generation")
        approved = w.get("approved") is True
        items.append({"kind": "lesson", "key": f"lesson:{gen}", "gen": gen, "approved": approved, "safe": True, "path": None,
                      "title": f"Gen {gen}  {'APPROVED' if approved else 'hidden'}  {w.get('name', '?')} L{w.get('level', '?')}: {str(w.get('lesson', ''))[:70]}"})

    def files(folder, kind, match, safe=True):
        try:
            names = [n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n)) and match(n)]
        except OSError:
            return
        for n in sorted(names, key=lambda n: os.path.getmtime(os.path.join(folder, n)), reverse=True):
            items.append({"kind": kind, "key": f"{kind}:{n}", "gen": None, "approved": None, "safe": safe, "path": os.path.join(folder, n), "title": n})

    files(chron_dir, "chronicle", lambda n: n.startswith("Chronicle_") and n.endswith(".md"))
    files(chron_dir, "postmortem", lambda n: n.startswith("Postmortem_") and n.endswith(".md"))
    files(os.path.join(mem_dir, "runs"), "run", lambda n: n.endswith(".json"))
    files(os.path.join(mem_dir, "model_lab"), "lab", lambda n: n.endswith((".json", ".md")))
    files(mem_dir, "data", lambda n: n in DATA_FILES, safe=False)
    order = {k: i for i, k in enumerate(MEMORY_KINDS)}
    items.sort(key=lambda it: order[it["kind"]])          # stable: keeps the newest-first order inside each kind
    return items


def memory_item_text(item, max_bytes=300_000):
    """The whole memory as text for the right-hand pane."""
    if item["kind"] == "lesson":
        for w in lessons():
            if w.get("generation") == item.get("gen"):
                head = f"Generation {w.get('generation')}   {'APPROVED: shown to the combat model' if w.get('approved') is True else 'hidden: NOT shown to the combat model'}\n"
                head += f"Character: {w.get('name')}  level {w.get('level')}  turns {w.get('turns')}  zone {w.get('zone')}\nDied to: {w.get('death_reason')}\nRecorded: {w.get('timestamp')}\n\nLesson:\n{w.get('lesson')}\n"
                return head
        return "This lesson is no longer in the active list (archived or deleted)."
    text = read_text(item["path"], max_bytes)
    return text if text else "(empty or unreadable)"


def _unique_path(folder, name):
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, name)
    if not os.path.exists(dest):
        return dest
    stem, ext = os.path.splitext(name)
    return os.path.join(folder, f"{stem}_{int(time.time())}{ext}")


def archive_memory_item(item, mem_dir=None, chron_dir=None):
    """Takes a memory out of the active set without losing it. A lesson moves (whole) to memory/archive/ancestral_wisdom_archived.json; a chronicle or
    post-mortem moves to chronicles/archive/; a run record or lab result moves to memory/archive/<kind>/. Returns a short description of where it went."""
    import chronicler
    if item["kind"] in VIEW_ONLY_KINDS or not item.get("safe", True):
        raise ValueError("live data files are never archived from here")
    if item["kind"] == "lesson":
        wisdom = chronicler.load_ancestral_wisdom()
        entry = next((w for w in wisdom if w.get("generation") == item.get("gen")), None)
        if entry is None:
            raise ValueError("that lesson is not in the active list")
        path = _archived_lessons_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        archived = read_json(path, []) or []
        archived.append(dict(entry, approved=False, archived_at=time.strftime("%Y-%m-%d %H:%M:%S")))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(archived, f, indent=2)                          # written first: a failure here leaves the lesson where it was
        chronicler.save_ancestral_wisdom([w for w in wisdom if w is not entry])
        return f"lesson Gen {item.get('gen')} -> {path}"
    import shutil
    folder = os.path.dirname(item["path"])
    if item["kind"] in ("chronicle", "postmortem"):
        dest_dir = os.path.join(chron_dir or _chron_dir(), "archive")
    else:
        dest_dir = os.path.join(mem_dir or _mem_dir(), "archive", item["kind"])
    dest = _unique_path(dest_dir, os.path.basename(item["path"]))
    shutil.move(item["path"], dest)
    return f"{os.path.basename(item['path'])} -> {dest}"


def delete_memory_item(item):
    """Permanently removes a memory (a lesson entry, or the file). Live data files are refused. Returns a short description."""
    import chronicler
    if item["kind"] in VIEW_ONLY_KINDS or not item.get("safe", True):
        raise ValueError("live data files are never deleted from here")
    if item["kind"] == "lesson":
        wisdom = chronicler.load_ancestral_wisdom()
        keep = [w for w in wisdom if w.get("generation") != item.get("gen")]
        if len(keep) == len(wisdom):
            raise ValueError("that lesson is not in the active list")
        chronicler.save_ancestral_wisdom(keep)
        return f"lesson Gen {item.get('gen')} deleted"
    os.remove(item["path"])
    return f"{os.path.basename(item['path'])} deleted"


def drop_log_text(path):
    rows = tail_jsonl(path, 100)
    if not rows:
        return "No items dropped yet."
    return "\n".join(f"{r.get('zone')} ({r.get('x')},{r.get('y')})  {r.get('name') or r.get('item')}  x{r.get('count', 1)}  {r.get('reason', '')}" for r in rows)


def pause_resume_bytes():
    """The brain toggles on a line from its console (input_listener), so the console sends one newline to its stdin. Writing
    active.flag directly would desynchronise the brain's own ai_active variable from the file."""
    return b"\n"
