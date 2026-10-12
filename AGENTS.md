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
(Decompiler: `ilspycmd` 9.1.0.7988, a dotnet tool. `ilspycmd "<Managed>\Assembly-CSharp.dll" -t XRL.World.Parts.LocationFinder -o scratch/decomp/X` gives readable C#; the type name needs its namespace. Output stays in `scratch/` and is never committed.)
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

**R9. Backlog items need a human.**
New ideas go in `docs/BACKLOG.md`; do not start a backlog item unless a human has promoted it.

## 3. Verification (required before any commit that touches code)

```
python -m py_compile brain.py build_templates.py chronicler.py skill_database.py
python dry_run.py        # deterministic, offline: QUDAI_LM_URL=http://127.0.0.1:9/x python dry_run.py (uses a temp exchange dir, never the live game files)
python tools/check_docs.py
python -c "t=open(r'mod/QudAIBrain/AIBrainPart.cs',encoding='utf-8').read(); assert t.count('{')==t.count('}'), 'Braces unbalanced'"
pwsh -NoProfile -File tools/compile_check.ps1   # only if the C# changed: needs PowerShell 7; must print COMPILE OK before deploy
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
- **After a death, classify it** in `data/death_ledger.json` (kind: bug, gap, decision, luck or lab, plus a one-line note and the issue that answered it) and run `python tools/generation_report.py`. Only a repeated cause with no fix, or a bug, becomes code; a decision a better agent could have made goes to the agent's memory (ancestral wisdom), not to a rule (DECISIONS calibration note).
- **End every session by updating `docs/HANDOFF.md`** (what changed, what is unverified, what is broken, next step).
- `PROJECT_HISTORY.md` is append-only history. Do not use it as the source of truth for current behavior.

## 5. Repo hygiene

- Never commit: Twitch tokens or `twitch_config.json`, decompiled game source, game DLL copies, `Player.log`.
- Build artifacts (`*.dll`) and one-off probes belong in `scratch/` (git-ignored), not the repo root.
- Paths: user-specific absolute paths (exchange dir, mod dir) must come from one config, not be hard-coded in
  multiple files. Known offenders are listed in `docs/HANDOFF.md`.
- Seed `random` once per run and log the seed (also write it into death chronicles) so failures reproduce.

### Git safety (applies to every tool; the human is still learning git)

- **Never run a destructive git command without explicit confirmation in chat:** `git reset --hard`, `git clean`, `git checkout .`,
  `git restore .`, `git stash drop`, `git branch -D`, `git push --force`, or a GitHub Desktop "Discard changes".
- **Never discard or overwrite uncommitted files under `memory/` or `chronicles/`.** They are the agent's failure memory, and git cannot
  recover untracked files.
- **Stage by explicit path.** Do not use `git add -A` or `git add .`: game output lands in the repo and must not ride along in unrelated commits.
- **Explain each git command before running it.**
- **When git state is confusing, run `python tools/git_report.py`** (read-only) and show the output instead of guessing.
- Close other tools (Antigravity, Claude Code, GitHub Desktop, File Explorer on the repo) before switching branches. Windows may refuse to delete
  folders it holds open; answer `n` or press Ctrl+C. The "Deletion of directory failed" prompt is harmless.

## 6. When blocked

If you cannot verify something (needs the running game, `Player.log`, or a human decision), say so in
`docs/HANDOFF.md` under *Needs a human* instead of guessing.

**Missing tools (human decision, 2026-10-12).** If a tool, install, permission or data feed is missing and slows or weakens the
current task, stop that task and get it addressed first: name the exact fix (command, working version, source, size) and let the
human run it; never install anything silently and never work around it quietly. The one exception: a console or tooling
convenience waits while a lab is running, unless the lab needs it for the test.

**The human is the weak link on purpose, and that is fine.** They sometimes forget a step or a piece of information. Design for it:
say exactly what to do and when, list what you need before a test starts, and read the files yourself (`scratch/captures/latest/`,
`last_state.json`, `memory/decision_trace.jsonl`) instead of asking for pastes. If a capture lacks something, say which file or step
and why it matters. No blame. If a change to the agent's environment would make the work easier or more reliable, propose it and
record it in `docs/HANDOFF.md`.
