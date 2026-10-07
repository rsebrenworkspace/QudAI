"""Model lab (HANDOFF issue 65): compare the language models in LM Studio on the brain's real combat call.

It replays the fixed situations in data/model_lab_scenarios.json (the deaths of this project and the everyday cases) through the brain's own
`query_llm_decision`, so the prompt, the menu of valid actions and the parser are exactly what a run uses. For every model it reports:

  parse%      the reply was JSON the brain can read
  menu%       the chosen action is one of the VALID ACTIONS the brain offered
  policy%     the choice passes the scenario's checks (never rest next to an Impossible hostile, do not flee a weak attacker, ...)
  score%      all three at once: the number to rank by
  latency     p50 / p95 of the replies, and how many fit the brain's call timeout (6 s by default)
  same%       how often repeated runs of one scenario give the same action
  VRAM        GPU memory in use after the model loaded (nvidia-smi, if present)
  empty/think a reply with no text at all (often a thinking model that spent its token budget thinking) or with <think> text in it

    python tools/model_lab.py --list                       models LM Studio knows, with load state
    python tools/model_lab.py                              the model that is loaded now, 3 repeats
    python tools/model_lab.py --models google/gemma-4-12b,qwen/qwen3-vl-8b-instruct
    python tools/model_lab.py --all                        every chat model, one at a time

How models are loaded (this matters on a 16 GB card shared with the game): with the `lms` command available the lab UNLOADS everything first, loads
one model at a time with a fixed small context (--ctx, 8192), ONE parallel slot (LM Studio's default of 4 slots multiplies the cache by four) and full
GPU offload, and at the end unloads the lab's model and RELOADS the model that was loaded when it started (--no-restore to skip). Without `lms` it falls
back to just-in-time loading and cannot control any of that. A model that returns nothing usable for its first four calls in a row is abandoned.

The brain is imported against a throw-away exchange folder, never the live game folder. Results go to memory/model_lab/ (not committed).
"""
import argparse
import contextlib
import datetime
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS_PATH = os.path.join(ROOT, "data", "model_lab_scenarios.json")
OUT_DIR = os.path.join(ROOT, "memory", "model_lab")
DIRS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}
DEFAULT_BASE = "http://localhost:1234"
ABORT_AFTER = 4          # consecutive unusable replies before a model is abandoned


def load_brain():
    """Imports brain.py against a temporary exchange folder (never the live one)."""
    if "brain" in sys.modules:
        return sys.modules["brain"]
    os.environ["QUDAI_EXCHANGE_DIR"] = tempfile.mkdtemp(prefix="qudai_lab_")
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import brain  # noqa: E402
    return brain


def norm_action(action):
    """'USE_ABILITY:CommandLase:SE' and 'USE_ABILITY:CommandLase' compare equal; only the first word counts."""
    a = (action or "").split()[0] if action else ""
    parts = a.split(":")
    if len(parts) >= 3 and parts[-1] in DIRS:
        parts = parts[:-1]
    return ":".join(parts)


def policy_verdict(action, checks):
    """(passed, reason) for the scenario's prefix checks, judged on the model's raw action."""
    a = (action or "").split()[0] if action else ""
    for p in checks.get("must_not", []):
        if a.startswith(p):
            return False, f"chose {a}, which the scenario forbids ({p})"
    should = checks.get("should_any", [])
    if should and not any(a.startswith(p) for p in should):
        return False, f"chose {a}, expected one of {should}"
    return True, ""


# ---------------------------------------------------------------- machine state

def gpu_used_mib():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8).stdout.strip().splitlines()
        return int(out[0]) if out else None
    except Exception:
        return None


def ram_used_gb():
    """System RAM in use, in GB (Windows via `wmic`-free ctypes, else None)."""
    try:
        import ctypes

        class MEM(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEM(); m.dwLength = ctypes.sizeof(MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round((m.ullTotalPhys - m.ullAvailPhys) / 1024 ** 3, 1)
    except Exception:
        return None


# ---------------------------------------------------------------- LM Studio control

def find_lms():
    exe = shutil.which("lms")
    if exe:
        return exe
    guess = os.path.join(os.path.expanduser("~"), ".lmstudio", "bin", "lms.exe")
    return guess if os.path.exists(guess) else None


def _lms(args, timeout=600):
    exe = find_lms()
    if not exe:
        return None
    try:
        return subprocess.run([exe] + args, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def lms_ps():
    """[{identifier, model, context, parallel}] for the models LM Studio has in memory (parsed from `lms ps`), or []."""
    r = _lms(["ps"], 30)
    out = []
    if not r or r.returncode != 0:
        return out
    for line in r.stdout.splitlines():
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) >= 6 and cols[2] in ("IDLE", "GENERATING", "LOADING", "READY"):
            out.append({"identifier": cols[0], "model": cols[1], "context": int(cols[4]) if cols[4].isdigit() else None,
                        "parallel": int(cols[5]) if cols[5].isdigit() else None})
    return out


def try_unload_all():
    r = _lms(["unload", "--all"], 120)
    return bool(r and r.returncode == 0)


def lms_load(model, ctx, parallel=1, gpu="max", ttl=1800):
    """Loads `model` with a fixed context and slot count (ttl None: never auto-unload). Returns (ok, seconds, message)."""
    t0 = time.time()
    args = ["load", model, "--context-length", str(ctx), "--parallel", str(parallel), "--gpu", str(gpu), "--identifier", model]
    if ttl:
        args += ["--ttl", str(ttl)]
    r = _lms(args + ["-y"], 900)
    if r is None:
        return False, time.time() - t0, "the lms command is not available"
    return r.returncode == 0, time.time() - t0, (r.stdout + r.stderr).strip()[-300:]


def list_models(base):
    """(v0 models with load state, v1 models). Either may be empty."""
    v0, v1 = [], []
    try:
        v0 = requests.get(base + "/api/v0/models", timeout=5).json().get("data", [])
    except Exception:
        pass
    try:
        v1 = requests.get(base + "/v1/models", timeout=5).json().get("data", [])
    except Exception:
        pass
    return v0, v1


def chat_models(base):
    v0, v1 = list_models(base)
    if v0:
        return [(m["id"], m.get("state") == "loaded") for m in v0 if m.get("type") in ("llm", "vlm")]
    return [(m["id"], False) for m in v1 if "embed" not in str(m.get("id", "")).lower()]


def warm_up(base, model, wait=300):
    """A tiny request; with just-in-time loading it also loads the model. Returns (seconds, ok)."""
    t0 = time.time()
    try:
        r = requests.post(base + "/v1/chat/completions", json={"model": model, "messages": [{"role": "user", "content": "Reply with the single word: ready"}], "max_tokens": 8, "temperature": 0}, timeout=wait)
        return time.time() - t0, r.status_code == 200
    except Exception:
        return time.time() - t0, False


# ---------------------------------------------------------------- scoring

def run_scenario(brain, scn, model, repeat, on_run=None, abort_state=None):
    """The results of up to `repeat` calls of the brain's combat function on one scenario."""
    state = scn["state"]
    enemies = scn.get("enemies", [])
    abilities = state.get("abilities", [])
    cur = (state.get("x", 0), state.get("y", 0))
    valid_moves = brain.get_valid_moves(state.get("surroundings", {}), cur, None, is_in_combat=True)
    template = brain.build_templates.detect_build(state)
    runs = []
    for k in range(repeat):
        probe = {}
        brain.LLM_PROBE = probe
        brain.active_model_id = model
        try:
            with contextlib.redirect_stdout(io.StringIO()):          # the brain prints one line per failed call; the lab reports them itself
                result = brain.query_llm_decision(state, enemies, valid_moves, abilities, template, took_damage=False)
        finally:
            brain.LLM_PROBE = None
        raw_action = probe.get("parsed_action")
        menu = {norm_action(c) for c in probe.get("choices", [])}
        raw = probe.get("raw")
        raw_s = raw or ""
        if probe.get("error") and raw is None:
            kind = "timeout" if "Timeout" in str(probe.get("error")) else "error"
        elif probe.get("http_status") not in (None, 200):
            kind = "error"
        elif raw is not None and raw_s.strip() == "":
            kind = "empty_reply"          # HTTP 200 but no text: a thinking model spending its whole token budget, or a template problem
        elif result is None and raw_action is None:
            kind = "think_leak" if ("<think" in raw_s.lower() or "</think" in raw_s.lower()) else "bad_json"
        else:
            kind = "ok"
        parsed = raw_action is not None and raw_action != ""
        in_menu = parsed and norm_action(raw_action) in menu
        pol_ok, pol_why = policy_verdict(raw_action, scn.get("checks", {})) if parsed else (False, "no action")
        run = {"kind": kind, "latency": probe.get("latency"), "action": raw_action, "final_action": probe.get("final_action"), "parsed": parsed,
               "in_menu": in_menu, "policy_ok": pol_ok, "policy_why": pol_why, "menu_size": len(menu), "prompt_chars": probe.get("prompt_chars"),
               "finish_reason": probe.get("finish_reason"), "reasoning_chars": probe.get("reasoning_chars"), "completion_tokens": probe.get("completion_tokens"),
               "raw": raw_s[:300]}
        runs.append(run)
        if on_run:
            on_run(scn["id"], k + 1, repeat, run)
        if abort_state is not None:
            abort_state["bad"] = 0 if parsed else abort_state.get("bad", 0) + 1
            abort_state["seen"] = abort_state.get("seen", 0) + 1
            if abort_state["bad"] >= ABORT_AFTER and abort_state["seen"] == abort_state["bad"]:
                abort_state["aborted"] = True
                break
    return runs


def pct(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def summarize(model, per_scenario, brain_timeout, warm=None, vram=None, aborted=False, ram=None):
    runs = [r for s in per_scenario.values() for r in s]
    n = len(runs)
    ok_lat = sorted(r["latency"] for r in runs if r["kind"] == "ok" and r["latency"] is not None)
    consistent = 0
    groups = 0
    for s in per_scenario.values():
        acts = [norm_action(r["action"]) for r in s if r["parsed"]]
        if len(s) > 1 and acts:
            groups += 1
            consistent += 1 if len(set(acts)) == 1 and len(acts) == len(s) else 0
    thinking = [r for r in runs if (r.get("reasoning_chars") or 0) > 0]
    return {
        "model": model, "runs": n, "aborted": aborted,
        "parse_pct": pct(sum(r["parsed"] for r in runs), n),
        "menu_pct": pct(sum(r["in_menu"] for r in runs), n),
        "policy_pct": pct(sum(r["policy_ok"] for r in runs), n),
        "score_pct": pct(sum(1 for r in runs if r["parsed"] and r["in_menu"] and r["policy_ok"]), n),
        "latency_p50": round(statistics.median(ok_lat), 2) if ok_lat else None,
        "latency_p95": round(ok_lat[min(len(ok_lat) - 1, int(0.95 * len(ok_lat)))], 2) if ok_lat else None,
        "within_brain_timeout_pct": pct(sum(1 for r in runs if r["kind"] == "ok" and r["latency"] is not None and r["latency"] <= brain_timeout), n),
        "timeouts": sum(r["kind"] == "timeout" for r in runs), "bad_json": sum(r["kind"] == "bad_json" for r in runs),
        "think_leaks": sum(r["kind"] == "think_leak" for r in runs), "errors": sum(r["kind"] == "error" for r in runs),
        "empty_replies": sum(r["kind"] == "empty_reply" for r in runs), "reasoning_runs": len(thinking),
        "same_action_pct": pct(consistent, groups) if groups else None,
        "load_seconds": round(warm[0], 1) if warm else None, "warm_ok": warm[1] if warm else None, "gpu_used_mib": vram, "ram_used_gb": ram,
    }


def render(summaries, per_model, brain_timeout, settings=""):
    lines = [f"# Model lab {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
             f"Brain call timeout assumed: {brain_timeout:g}s. {settings} Each row replays the same scenarios; `score` = parsed AND in the offered menu AND passes the scenario checks.", "",
             "| model | score% | parse% | menu% | policy% | p50 s | p95 s | in time% | same% | timeouts | bad json | think | empty | load s | GPU MiB | RAM GB | note |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(summaries, key=lambda x: (-x["score_pct"], x["latency_p50"] if x["latency_p50"] is not None else 999)):
        note = "abandoned: no usable reply in the first calls" if s.get("aborted") else ""
        if s["empty_replies"] and s["reasoning_runs"]:
            note += " the model thought but returned no answer (token budget spent thinking?)"
        elif s["empty_replies"]:
            note += " empty replies"
        lines.append(f"| {s['model']} | {s['score_pct']} | {s['parse_pct']} | {s['menu_pct']} | {s['policy_pct']} | {s['latency_p50']} | {s['latency_p95']} | "
                     f"{s['within_brain_timeout_pct']} | {s['same_action_pct']} | {s['timeouts']} | {s['bad_json']} | {s['think_leaks']} | {s['empty_replies']} | {s['load_seconds']} | {s['gpu_used_mib']} | {s.get('ram_used_gb')} | {note.strip()} |")
    lines.append("")
    lines.append("## Scenario by scenario (first run of each; P = passes the checks)")
    lines.append("")
    models = list(per_model.keys())
    ids = []
    for m in models:
        for sid in per_model[m]:
            if sid not in ids:
                ids.append(sid)
    lines.append("| scenario | " + " | ".join(models) + " |")
    lines.append("|---|" + "---|" * len(models))
    for sid in ids:
        cells = []
        for m in models:
            rs = per_model[m].get(sid)
            if not rs:
                cells.append("(not run)")
                continue
            r = rs[0]
            tag = "P" if (r["parsed"] and r["in_menu"] and r["policy_ok"]) else ("x" if r["parsed"] else r["kind"])
            cells.append(f"{tag} {str(r['action'] or '')[:34]}".replace("|", "/"))
        lines.append(f"| {sid} | " + " | ".join(cells) + " |")
    fails = []
    for m, scn in per_model.items():
        for sid, runs in scn.items():
            for r in runs:
                if r["parsed"] and not r["policy_ok"]:
                    fails.append(f"- {m} / {sid}: {r['policy_why']}")
                    break
    if fails:
        lines += ["", "## Policy failures", ""] + fails
    return "\n".join(lines) + "\n"


def run_lab(models, scenarios, base=DEFAULT_BASE, repeat=3, timeout=30.0, brain_timeout=6.0, unload=True, out_dir=None, do_warm=True, log=print,
            manage_models=True, ctx=8192, parallel=1, gpu="max", restore=True):
    """Runs every scenario on every model. Returns {"summaries": [...], "per_model": {...}, "markdown": str}. Used by the command line and by the tests.

    manage_models=True (command line): needs `lms`; unloads everything, loads each model with `ctx`/`parallel`/`gpu`, and restores the original model.
    manage_models=False: no loading control at all (just-in-time loading by the first request)."""
    brain = load_brain()
    brain.LM_STUDIO_URL = base + "/v1/chat/completions"
    brain.LM_STUDIO_TIMEOUT = float(timeout)
    use_lms = bool(manage_models and find_lms())
    if manage_models and not use_lms:
        log("[lab] the `lms` command was not found: models load just-in-time with LM Studio's own settings (context, parallel slots) and cannot be controlled")
    original = lms_ps() if use_lms else []
    summaries, per_model = [], {}
    try:
        for mi, model in enumerate(models):
            warm = None
            if use_lms:
                try_unload_all()
                ok, secs, msg = lms_load(model, ctx, parallel, gpu)
                warm = (secs, ok)
                log(f"[lab] {model}: {'loaded' if ok else 'LOAD FAILED'} in {secs:.1f}s (context {ctx}, {parallel} slot, gpu {gpu})" + ("" if ok else f": {msg}"))
                if not ok:
                    per_model[model] = {}
                    summaries.append(summarize(model, {}, brain_timeout, warm, gpu_used_mib(), aborted=True, ram=ram_used_gb()))
                    continue
            else:
                if unload and mi > 0:
                    try_unload_all()
                if do_warm:
                    warm = warm_up(base, model)
                    log(f"[lab] {model}: loaded in {warm[0]:.1f}s")
                    if not warm[1]:
                        log(f"[lab] {model}: the warm-up request failed; results below will show errors")
                else:
                    log(f"[lab] {model}")
            vram, ram = gpu_used_mib(), ram_used_gb()
            log(f"[lab] {model}: GPU {vram} MiB, RAM {ram} GB in use")
            per_scn, abort_state = {}, {"bad": 0, "seen": 0}

            def on_run(sid, k, n, r, _model=model):
                log(f"[lab]   {sid} {k}/{n}: {r['kind']:<11} {str(r['action'] or '-')[:40]:<40} {('%.1fs' % r['latency']) if r['latency'] is not None else '-'}" + ("" if r['kind'] == "ok" else f"  finish={r.get('finish_reason')} reasoning={r.get('reasoning_chars')}"))

            for scn in scenarios:
                per_scn[scn["id"]] = run_scenario(brain, scn, model, repeat, on_run=on_run, abort_state=abort_state)
                if abort_state.get("aborted"):
                    log(f"[lab] {model}: no usable reply in the first {ABORT_AFTER} calls: abandoning this model")
                    break
            per_model[model] = per_scn
            summaries.append(summarize(model, per_scn, brain_timeout, warm, vram, aborted=bool(abort_state.get("aborted")), ram=ram))
            s = summaries[-1]
            log(f"[lab] {model}: score {s['score_pct']}%  parse {s['parse_pct']}%  menu {s['menu_pct']}%  policy {s['policy_pct']}%  p50 {s['latency_p50']}s  timeouts {s['timeouts']}  empty {s['empty_replies']}")
    finally:
        if use_lms:
            try_unload_all()
            if restore:
                for m in original:
                    ok, secs, msg = lms_load(m["model"], m.get("context") or ctx, m.get("parallel") or parallel, "max", None)
                    log(f"[lab] restored {m['model']} (context {m.get('context')}, {m.get('parallel')} slots): {'ok' if ok else 'FAILED: ' + msg}")
    md = render(summaries, per_model, brain_timeout, f"Loaded with context {ctx}, {parallel} slot(s), gpu {gpu}." if use_lms else "Loaded just-in-time with LM Studio's own settings.")
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(os.path.join(out_dir, f"lab_{stamp}.json"), "w", encoding="utf-8") as f:
            json.dump({"summaries": summaries, "per_model": per_model, "repeat": repeat, "timeout": timeout, "ctx": ctx, "parallel": parallel}, f, indent=1)
        with open(os.path.join(out_dir, f"lab_{stamp}.md"), "w", encoding="utf-8") as f:
            f.write(md)
        log(f"[lab] report: {os.path.join(out_dir, f'lab_{stamp}.md')}")
    return {"summaries": summaries, "per_model": per_model, "markdown": md}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare LM Studio models on the brain's combat call.")
    ap.add_argument("--list", action="store_true", help="list models and exit")
    ap.add_argument("--models", help="comma-separated model ids (default: the model that is loaded now)")
    ap.add_argument("--all", action="store_true", help="every chat model, one at a time")
    ap.add_argument("--repeat", type=int, default=3, help="runs per scenario (default 3)")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds a reply may take during the lab (default 30)")
    ap.add_argument("--brain-timeout", type=float, default=6.0, help="the brain's real call timeout, for the 'in time' column (default 6)")
    ap.add_argument("--ctx", type=int, default=8192, help="context length each model is loaded with (default 8192)")
    ap.add_argument("--parallel", type=int, default=1, help="parallel slots each model is loaded with (default 1)")
    ap.add_argument("--max-tokens", type=int, default=None, help="output token budget of the combat call (the brain's default is 128; a thinking model needs more)")
    ap.add_argument("--extra", default=None, help='extra JSON merged into the request, e.g. \'{"chat_template_kwargs": {"enable_thinking": false}}\' (what LM Studio honours depends on the model)')
    ap.add_argument("--scenarios", default=SCENARIOS_PATH)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--no-unload", action="store_true", help="(without lms) do not unload between models")
    ap.add_argument("--no-manage", action="store_true", help="do not load or unload anything: use whatever LM Studio does just-in-time")
    ap.add_argument("--no-restore", action="store_true", help="do not reload the model that was loaded when the lab started")
    args = ap.parse_args(argv)

    models_info = chat_models(args.base)
    if args.list:
        for mid, loaded in models_info:
            print(f"{'LOADED ' if loaded else '       '}{mid}")
        for m in lms_ps():
            print(f"  in memory: {m['model']} (context {m['context']})")
        return 0
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    elif args.all:
        models = [m for m, _ in models_info]
        print(f"[lab] --all: {len(models)} models will be loaded one after another.")
    else:
        models = [m for m, loaded in models_info if loaded][:1] or [m for m, _ in models_info][:1]
    if not models:
        print("[lab] no chat model found in LM Studio")
        return 1
    with open(args.scenarios, "r", encoding="utf-8") as f:
        scenarios = json.load(f)["scenarios"]
    manage = not args.no_manage
    brain = load_brain()
    if args.max_tokens:
        brain.LM_MAX_TOKENS = args.max_tokens
    if args.extra:
        try:
            brain.LM_EXTRA_PAYLOAD = json.loads(args.extra)
        except ValueError as ex:
            print(f"[lab] --extra is not valid JSON: {ex}")
            return 1
    if brain.LM_MAX_TOKENS != 128 or brain.LM_EXTRA_PAYLOAD:
        print(f"[lab] request settings: max_tokens {brain.LM_MAX_TOKENS}, extra {json.dumps(brain.LM_EXTRA_PAYLOAD)}")
    print(f"[lab] {len(scenarios)} scenarios x {args.repeat} repeats x {len(models)} model(s): {', '.join(models)}")
    if manage and find_lms():
        print("[lab] LM Studio will be emptied, each model loaded alone, and the model that is loaded now restored at the end. Close the game for big models.")
    result = run_lab(models, scenarios, base=args.base, repeat=args.repeat, timeout=args.timeout, brain_timeout=args.brain_timeout, unload=not args.no_unload,
                     out_dir=OUT_DIR, manage_models=manage, ctx=args.ctx, parallel=args.parallel, restore=not args.no_restore)
    print()
    print(result["markdown"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
