# QudAI: Agent Rules (canonical)

Every agent working in this repo (Antigravity/Gemini, Claude, Codex, anything else) follows this file.
Tool-specific files (`GEMINI.md`, etc.) only point here. Do not copy rules into them.

## 1. Read order (do this before touching code)

1. This file.
2. `docs/HANDOFF.md`: what the last session changed, what is broken right now, what to try next.
2b. `docs/WORKFLOW.md`: how Claude and Antigravity share the repo (roles, task cards, branches, review checklist). Work from a task card in `docs/tasks/` when one exists.
2c. `docs/CODEMAP.md`: which functions live where. Read it *before* opening `AIBrainPart.cs` or `brain.py`, and read only the functions your task touches.
3. `docs/ARCHITECTURE.md`: how the system works *today* (overwritten, never appended to).
4. `ENGINE_INTERNALS.md`: verified facts about Qud's engine. Check here before decompiling again.
5. `docs/DECISIONS.md`: why things are the way they are, and the dead ends. Check here before trying an approach.
6. `PROJECT_HISTORY.md`: long chronological log. Reference only; do not read it end to end.

## 2. Hard rules

**R1. Three Strikes: engine truth over heuristic patches.**
If an issue is not fixed after two attempts, stop writing Python heuristics. Inspect `Assembly-CSharp.dll`
(`dnfile` or reflection, in `scratch/`) or the XML blueprints, and use the native engine API
(`AutoAct.TryFindEdgeStep`, `AutoAct.TryFindPathStep`, `SkillFactory`, ...).

**R2. One owner per piece of state.**
C# owns anything the engine can tell us: zone explored status, reachable edges, skill/mutation eligibility,
companion status. Python reads it and never overrides it. If Python needs a different view, add a new
field. Do not mutate a field the other side owns.

**R3. Never mirror engine rules in Python.**
Mutation caps, skill prerequisites, stat minimums: have C# export the answer. A Python copy of an engine
rule will drift and cause the next loop bug.

**R4. Every command costs a turn.**
Any action that returns without spending energy makes the game re-export the same state and Python re-send
the same action: an infinite loop. Energy accounting is enforced centrally in `Prefix`, not per command.

**R5. Structured results, not string parsing.**
C# reports `{status, reason}` for every command. Python never infers success from coordinates or from
substring matches on free text (the `"PATH_BLOCKED"` matching `"E"` bug).

**R6. Commit to a plan; do not re-derive it each turn.**
Movement uses committed intents (target, reason, timeout, failure condition). Greedy 1-step vector movement
is banned except as a last resort. Always path with the engine pathfinder.

**R7. Peaceful settlements are off limits.**
No attacking walls, huts, owned objects, or peaceful NPCs; no looting owned items. Check `is_settlement`.

**R8. Never kill or shoot companions.**
All beams, rays and missiles must pass the ray-trace check in both C# and Python.

## 3. Verification (required before any commit that touches code)

```
python -m py_compile brain.py build_templates.py chronicler.py skill_database.py
python dry_run.py
python tools/check_docs.py
python -c "t=open(r'mod/QudAIBrain/AIBrainPart.cs',encoding='utf-8').read(); assert t.count('{')==t.count('}'), 'Braces unbalanced'"
python sync_mod.py deploy     # only if the C# changed
```

`dry_run.py` tests single decisions. Oscillation is a multi-turn property. When fixing a loop/stall bug, add a
**multi-turn** regression test (simulate N turns on a small grid and assert progress), not just a snapshot.

## 4. Documentation discipline (this is how agents hand off)

- **Docs change in the same commit as the code they describe.** No exceptions.
- If you add/remove a Harmony patch, a command, or a `state.json` field: update `docs/ARCHITECTURE.md`
  (between the `<!-- ...:start/end -->` markers) so `tools/check_docs.py` passes.
- If you try an approach and it fails, add it to `docs/DECISIONS.md` under *Dead ends* with the reason.
- If you learn a verified engine fact, add it to `ENGINE_INTERNALS.md`.
- **Tag confidence.** Write `[verified in game YYYY-MM-DD]`, `[verified in code @commit]`, or `[unverified]`.
  Never state an inference as fact.
- **End every session by updating `docs/HANDOFF.md`** (what changed, what is unverified, what is broken, next step).
- `PROJECT_HISTORY.md` is append-only history. Do not use it as the source of truth for current behavior.

## 5. Repo hygiene

- Never commit: Twitch tokens or `twitch_config.json`, decompiled game source, game DLL copies, `Player.log`.
- Build artifacts (`*.dll`) and one-off probes belong in `scratch/` (git-ignored), not the repo root.
- Paths: user-specific absolute paths (exchange dir, mod dir) must come from one config, not be hard-coded in
  multiple files. Known offenders are listed in `docs/HANDOFF.md`.
- Seed `random` once per run and log the seed (also write it into death chronicles) so failures reproduce.

## 6. When blocked

If you cannot verify something (needs the running game, `Player.log`, or a human decision), say so in
`docs/HANDOFF.md` under *Needs a human* instead of guessing.
