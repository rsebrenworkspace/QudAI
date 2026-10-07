"""Model lab (HANDOFF issue 65): compare the language models in LM Studio on the brain's real combat call.

It replays the fixed situations in data/model_lab_scenarios.json (the deaths of this project and the everyday cases) through the brain's own
`query_llm_decision`, so the prompt, the menu of valid actions and the parser are exactly what a run uses. For every model it reports:

  parse%      the reply was JSON the brain can read (reasoning models that think aloud fail here)
  menu%       the chosen action is one of the VALID ACTIONS the brain offered
  policy%     the choice passes the scenario's checks (never rest next to an Impossible hostile, do not flee a weak attacker, ...)
  score%      all three at once: the number to rank by
  latency     p50 / p95 of the replies, and how many fit the brain's call timeout (6 s by default)
  same%       how often repeated runs of one scenario give the same action
  VRAM        GPU memory in use after the model loaded (nvidia-smi, if present)

    python tools/model_lab.py --list                       models LM Studio knows, with load state
    python tools/model_lab.py                              the model that is loaded now, 3 repeats
    python tools/model_lab.py --models google/gemma-4-12b,qwen/qwen3-vl-8b-instruct
    python tools/model_lab.py --all                        every chat model (LOADS EACH ONE: close the game first)

Safety: the brain is imported against a throw-away exchange folder, never the live game folder. LM Studio loads a model on the first request
(just-in-time loading must be on); `lms unload --all` is run between models when the `lms` command is available (--no-unload to skip).
Results are written to memory/model_lab/ (not committed). Nothing here changes the game or the brain's settings.
"""
import argparse
import datetime
import json
import os
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


def gpu_used_mib():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8).stdout.strip().splitlines()
        return int(out[0]) if out else None
    except Exception:
        return None


def find_lms():
    exe = shutil.which("lms")
    if exe:
        return exe
    guess = os.path.join(os.path.expanduser("~"), ".lmstudio", "bin", "lms.exe")
    return guess if os.path.exists(guess) else None


def try_unload_all():
    exe = find_lms()
    if not exe:
        return False
    try:
        subprocess.run([exe, "unload", "--all"], capture_output=True, text=True, timeout=60)
        return True
    except Exception:
        return False


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
    """First request loads the model (just-in-time); returns (seconds, ok)."""
    t0 = time.time()
    try:
        r = requests.post(base + "/v1/chat/completions", json={"model": model, "messages": [{"role": "user", "content": "Reply with the single word: ready"}], "max_tokens": 8, "temperature": 0}, timeout=wait)
        return time.time() - t0, r.status_code == 200
    except Exception:
        return time.time() - t0, False


def run_scenario(brain, scn, model, repeat):
    """The results of `repeat` calls of the brain's combat function on one scenario."""
    state = scn["state"]
    enemies = scn.get("enemies", [])
    abilities = state.get("abilities", [])
    cur = (state.get("x", 0), state.get("y", 0))
    valid_moves = brain.get_valid_moves(state.get("surroundings", {}), cur, None, is_in_combat=True)
    template = brain.build_templates.detect_build(state)
    runs = []
    for _ in range(repeat):
        probe = {}
        brain.LLM_PROBE = probe
        brain.active_model_id = model
        try:
            result = brain.query_llm_decision(state, enemies, valid_moves, abilities, template, took_damage=False)
        finally:
            brain.LLM_PROBE = None
        raw_action = probe.get("parsed_action")
        menu = {norm_action(c) for c in probe.get("choices", [])}
        raw = probe.get("raw") or ""
        if probe.get("error") and probe.get("raw") is None:
            kind = "timeout" if "Timeout" in str(probe.get("error")) else "error"
        elif probe.get("http_status") not in (None, 200):
            kind = "error"
        elif result is None and raw_action is None:
            kind = "think_leak" if ("<think" in raw.lower() or "</think" in raw.lower()) else "bad_json"
        else:
            kind = "ok"
        parsed = raw_action is not None and raw_action != ""
        in_menu = parsed and norm_action(raw_action) in menu
        pol_ok, pol_why = policy_verdict(raw_action, scn.get("checks", {})) if parsed else (False, "no action")
        runs.append({"kind": kind, "latency": probe.get("latency"), "action": raw_action, "final_action": probe.get("final_action"), "parsed": parsed,
                     "in_menu": in_menu, "policy_ok": pol_ok, "policy_why": pol_why, "menu_size": len(menu), "prompt_chars": probe.get("prompt_chars"),
                     "raw": raw[:300]})
    return runs


def pct(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def summarize(model, per_scenario, brain_timeout, warm=None, vram=None):
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
    return {
        "model": model, "runs": n,
        "parse_pct": pct(sum(r["parsed"] for r in runs), n),
        "menu_pct": pct(sum(r["in_menu"] for r in runs), n),
        "policy_pct": pct(sum(r["policy_ok"] for r in runs), n),
        "score_pct": pct(sum(1 for r in runs if r["parsed"] and r["in_menu"] and r["policy_ok"]), n),
        "latency_p50": round(statistics.median(ok_lat), 2) if ok_lat else None,
        "latency_p95": round(ok_lat[min(len(ok_lat) - 1, int(0.95 * len(ok_lat)))], 2) if ok_lat else None,
        "within_brain_timeout_pct": pct(sum(1 for r in runs if r["kind"] == "ok" and r["latency"] is not None and r["latency"] <= brain_timeout), n),
        "timeouts": sum(r["kind"] == "timeout" for r in runs), "bad_json": sum(r["kind"] == "bad_json" for r in runs),
        "think_leaks": sum(r["kind"] == "think_leak" for r in runs), "errors": sum(r["kind"] == "error" for r in runs),
        "same_action_pct": pct(consistent, groups) if groups else None,
        "load_seconds": round(warm[0], 1) if warm else None, "warm_ok": warm[1] if warm else None, "gpu_used_mib": vram,
    }


def render(summaries, per_model, brain_timeout):
    lines = [f"# Model lab {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
             f"Brain call timeout assumed: {brain_timeout:g}s. Each row replays the same scenarios; `score` = parsed AND in the offered menu AND passes the scenario checks.", "",
             "| model | score% | parse% | menu% | policy% | p50 s | p95 s | in time% | same% | timeouts | bad json | think | load s | GPU MiB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(summaries, key=lambda x: (-x["score_pct"], x["latency_p50"] if x["latency_p50"] is not None else 999)):
        lines.append(f"| {s['model']} | {s['score_pct']} | {s['parse_pct']} | {s['menu_pct']} | {s['policy_pct']} | {s['latency_p50']} | {s['latency_p95']} | "
                     f"{s['within_brain_timeout_pct']} | {s['same_action_pct']} | {s['timeouts']} | {s['bad_json']} | {s['think_leaks']} | {s['load_seconds']} | {s['gpu_used_mib']} |")
    lines.append("")
    lines.append("## Scenario by scenario (first run of each; P = passes the checks)")
    lines.append("")
    models = list(per_model.keys())
    ids = list(next(iter(per_model.values())).keys()) if per_model else []
    lines.append("| scenario | " + " | ".join(models) + " |")
    lines.append("|---|" + "---|" * len(models))
    for sid in ids:
        cells = []
        for m in models:
            r = per_model[m][sid][0]
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


def run_lab(models, scenarios, base=DEFAULT_BASE, repeat=3, timeout=30.0, brain_timeout=6.0, unload=True, out_dir=None, do_warm=True, log=print):
    """Runs every scenario on every model. Returns {"summaries": [...], "per_model": {...}}. Used by the command line and by the tests."""
    brain = load_brain()
    brain.LM_STUDIO_URL = base + "/v1/chat/completions"
    brain.LM_STUDIO_TIMEOUT = float(timeout)
    summaries, per_model = [], {}
    for mi, model in enumerate(models):
        if unload and mi > 0:
            try_unload_all()
        warm = warm_up(base, model) if do_warm else None
        vram = gpu_used_mib()
        log(f"[lab] {model}: loaded in {warm[0]:.1f}s" if warm else f"[lab] {model}")
        if warm and not warm[1]:
            log(f"[lab] {model}: the warm-up request failed; results below will show errors")
        per_scn = {}
        for scn in scenarios:
            per_scn[scn["id"]] = run_scenario(brain, scn, model, repeat)
        per_model[model] = per_scn
        summaries.append(summarize(model, per_scn, brain_timeout, warm, vram))
        s = summaries[-1]
        log(f"[lab] {model}: score {s['score_pct']}%  parse {s['parse_pct']}%  menu {s['menu_pct']}%  policy {s['policy_pct']}%  p50 {s['latency_p50']}s  timeouts {s['timeouts']}")
    md = render(summaries, per_model, brain_timeout)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(os.path.join(out_dir, f"lab_{stamp}.json"), "w", encoding="utf-8") as f:
            json.dump({"summaries": summaries, "per_model": per_model, "repeat": repeat, "timeout": timeout}, f, indent=1)
        with open(os.path.join(out_dir, f"lab_{stamp}.md"), "w", encoding="utf-8") as f:
            f.write(md)
        log(f"[lab] report: {os.path.join(out_dir, f'lab_{stamp}.md')}")
    return {"summaries": summaries, "per_model": per_model, "markdown": md}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare LM Studio models on the brain's combat call.")
    ap.add_argument("--list", action="store_true", help="list models and exit")
    ap.add_argument("--models", help="comma-separated model ids (default: the model that is loaded now)")
    ap.add_argument("--all", action="store_true", help="every chat model; each one is loaded in turn")
    ap.add_argument("--repeat", type=int, default=3, help="runs per scenario (default 3)")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds a reply may take during the lab (default 30)")
    ap.add_argument("--brain-timeout", type=float, default=6.0, help="the brain's real call timeout, for the 'in time' column (default 6)")
    ap.add_argument("--scenarios", default=SCENARIOS_PATH)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--no-unload", action="store_true")
    args = ap.parse_args(argv)

    models_info = chat_models(args.base)
    if args.list:
        for mid, loaded in models_info:
            print(f"{'LOADED ' if loaded else '       '}{mid}")
        return 0
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    elif args.all:
        models = [m for m, _ in models_info]
        print(f"[lab] --all: {len(models)} models will be loaded one after another. Close the game first.")
    else:
        models = [m for m, loaded in models_info if loaded][:1] or [m for m, _ in models_info][:1]
    if not models:
        print("[lab] no chat model found in LM Studio")
        return 1
    with open(args.scenarios, "r", encoding="utf-8") as f:
        scenarios = json.load(f)["scenarios"]
    print(f"[lab] {len(scenarios)} scenarios x {args.repeat} repeats x {len(models)} model(s): {', '.join(models)}")
    result = run_lab(models, scenarios, base=args.base, repeat=args.repeat, timeout=args.timeout, brain_timeout=args.brain_timeout, unload=not args.no_unload, out_dir=OUT_DIR)
    print()
    print(result["markdown"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
