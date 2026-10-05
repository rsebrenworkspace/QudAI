# QudAI: Handoff

<!-- handoff-updated: 2026-10-04 -->

> Read this first, update it last. Newest session on top. Keep *Current state*, *Open issues*, and *Next steps* true;
> move finished items into the session log. Tag confidence: `[verified in game DATE]`, `[verified in code @commit]`, `[unverified]`.

## Current state (as of commit c50b3c2)

- Agent explores, fights (LLM + fallbacks), levels, eats/camps, delves, recruits pets, and writes death chronicles.
- **Open blocker:** at character level 5 the mutation/advancement step does not complete correctly and the character loops.
  Cause not yet identified. See *Level 5 investigation*.
- The latest `Player.log` supplied for review (launch 2026-09-19) contained **no `[QudAI ...]` lines** and listed the
  enabled mod as `QUDAITEST`. That log is not from the level 5 hang. It shows a death by bleeding.
- Repo was made public temporarily for review. Set it back to private when finished.

## Level 5 investigation (open)

Working hypotheses, most likely first. None verified.
1. A Harmony patch in the level-up flow never applied (parameter-name or overload mismatch), so a modal blocks the game.
   Relevant patches: `Popup.ShowYesNo`, `Popup.PickOption`. The doc says Rapid Advancement uses a yes/no prompt followed by pickers.
2. The flow uses a different Popup method than the ones patched (the old docs claimed `ShowOptionList` is patched; the code does not).
3. A command returned without spending energy, so the same state was re-exported (see *Review findings* #1).

To discriminate (do this on the next hang, **before restarting the game**):
- Copy `Player.log` immediately (Unity keeps only one backup, `Player-prev.log`).
- Check `last_action_executed.txt` in the QudAI folder: timestamp advancing + same action = energy/no-op loop;
  timestamp frozen = C# exception or blocking modal (search the log for `[QudAI Prefix Error]`).
- Check which of `state.json` / `action.json` is sitting in the QudAI folder.

## Open issues (from the 2026-10-04 code review; all `[verified in code @c50b3c2]` unless noted, none reproduced in game)

**C# (`AIBrainPart.cs`)**
1. **fixed, verified in game 2026-10-04** (T-1.1, commit `1e61a29`, merged to `main`).
   Some commands `return` without spending energy (FIRE_MISSILE refusals, swim guards in MAKE_CAMP/COOK_MEAL). `Prefix` now spends a turn
   and logs `[QudAI EnergyGuard]` when `ExecuteCommand` leaves energy unchanged (`ACTIVATE_SPRINT` exempt). Manual COOK_MEAL-while-swimming
   test gave exactly one guard line; a 499-turn normal run (ended by character death) produced no new guard lines.
   Border crossings and stairs were not individually verified. `[unverified]` Whether this was the cause of the level 5 hang is still unknown.
2. `Prefix` catch does `return true`, which runs the vanilla turn and waits for a keypress. The game looks frozen after any exception.
3. `ReadAction` can throw (`Substring`) on a partially written `action.json`; only `IOException` is caught.
4. C# waits 6000 ms for an action; Python's LLM timeout is also 6.0 s. A slow LLM makes C# pass a turn, and the late action
   then applies to the next state. No turn id exists to discard stale actions.
5. `REST`/`PASS` call `ExecuteAutolevel("AUTOLEVEL")`, which uses a hard-coded rifle/acrobatics list and ignores the build template.
6. `AllocateStat`/`AllocateSkill` both add to `Penalty` and subtract from `BaseValue`. [unverified: may double-charge points. Log SP before/after one purchase.]
7. `AIPickOptionPatch`: `PreferredMutation` is a class name (`LightManipulation`) matched with `IndexOf` against display text
   (`Light Manipulation`), so it never matches; it then falls back to a fixed priority list that ignores the template.
8. `AIPickOptionPatch` sets `__result` and also invokes `OnResult`. [unverified: may apply the choice twice.]
9. Mutation level compared via `m.Level` but leveled with `BaseLevel + 1`. [unverified: possible mismatch with item/effect bonuses.]
10. `ExportDeath` returns silently if `death.json` already exists, so a stale file suppresses later death exports.

**Python (`brain.py`, `build_templates.py`, `chronicler.py`)**
11. `fallback_gunslinger`, `fallback_melee`, `fallback_nomad` reference `surroundings` that may be unassigned on some paths
    (`UnboundLocalError`). The exception is swallowed by `[Loop Error]` after `state.json` is already deleted, so no action is written.
12. `took_damage` ignores the source. Bleeding/poison sets it every turn, forcing combat mode and skipping Phase A (no rest/eat/level).
    Likely contributor to the death-by-bleeding in the 2026-09-19 log. [unverified]
13. A bad `state.json` is swallowed by `except Exception: continue`; the same file is re-read every ~20 ms with no message.
14. `detect_build()` re-runs every turn, so buying a mutation can switch archetype mid-run (priorities and doctrine change). Detect once and persist.
15. `update_zone_records` is called twice per turn, so `ZONE_STEP_COUNT` advances twice (the "first 4 turns" border logic is ~2 turns).
16. `is_peaceful_npc` uses substring matching; `"tam"` can match inside unrelated names, hiding real hostiles.
17. `zone_fully_explored` is overridden by Python in several places (see ARCHITECTURE 6b). Iterations 38 and 40 reverted each other.
18. Chronicler: lessons use only the last 6 action names (no state), only the last 4 are injected, LLM-timeout fallbacks are stored as wisdom,
    paths hard-coded to `D:\QudAI`.
19. `SKILL_DATABASE` is a static copy of engine data. C# exports only *affordable* skills, which is why Python needs the copy.

**Hygiene**
20. Hard-coded user paths in `brain.py` and `AIBrainPart.cs`; `D:\QudAI` in docs vs `C:\Users\...` in code.
21. `test_*.dll` and probe scripts are still on disk in the repo root (no longer tracked or committable since 3e3c105, but `check_docs.py` still warns because it checks disk, not git). README/ARCHITECTURE test counts fixed (50) in 8dd3548 / c861489.
22. `ENGINE_INTERNALS.md` is stale in places: says `isCycling` sets `isZoneFullyExplored = true` (code sets `false` + stuck flag), buffer size 10 (code 24),
    claims `Popup.Show`/`ShowOptionList` patches that do not exist, names `PlayerTurn.Prefix` and `bSuppressPopups` (code: `XRLCore.PlayerTurn`, `Popup.Suppress`).
    Section numbering repeats (11.4, 12.2).

**New (from the 2026-10-05 UTC baboon death, level 2; `[verified in code @T-1.10]`, in-game confirmation pending)**
27. **fixed in T-1.10 (branch `task/1.10-companion-name-cache`, not yet verified in game).** A name-based companion cache (C# `RegisteredCompanionNames`, Python `CHARMED_COMPANION_NAMES`, filled on every Proselytize *attempt*) made every baboon a "companion" after one recruit attempt. `last_state.json` showed 13 baboons with `is_companion: true`. Effects: hostile baboon had `is_enemy: false`, `is_in_combat` was false, Phase A chose `REST` at 6 and 2 HP with a baboon adjacent, offensive abilities aborted (`Lase (4 charges)` unused), the LLM only repositioned. Probably the cause of earlier "tried to disengage" runs. Also fixed in the same branch: issue 11 (`surroundings` unbound in all four fallbacks).

28. **fixed in T-1.11 (branch `task/1.11-occluded-threats`, not yet verified in game).** Enemies 2-4 tiles away behind an impassable wall (no line of sight) forced combat mode; the LLM spent ~14 turns "maneuvering to establish line of sight" while swimming in a lake, and Phase A never ran. New `get_close_threats` ignores non-adjacent enemies with `has_los: false`. Risk `[unverified]`: an unseen creature approaching in the dark is ignored until it is visible, adjacent, or damages us.
29. `[unverified]` Console shows "Zone fully explored: navigating ... exit S" while `unexplored_cells` was 1251 and `zone_fully_explored` false: Python overriding the engine flag (issue 17).

**New (from the T-1.1 in-game run, 2026-10-04; human-reported, not yet traced in code)**
23. Chronicler writes lessons from the last action only, and the Gen 7 lesson "Avoid moving SW..." is noise. Related to issue 18. `[unverified]`
24. Generation numbering collides after the wisdom file lost entries. Use `max(existing generation) + 1`, not a count. `[unverified]`
25. Phase B (LLM) advances and kites at low HP in melee instead of retreating, healing or fighting on. Reproduced in the 499-turn run that ended in death. `[unverified]`
26. Deploy note: the game logs the mod as `QUDAITEST` because that is the `Title` in `workshop.json`. The mod folder is `QudAIBrain`. This explains the
    `QUDAITEST` seen in the 2026-09-19 log (see *Needs a human*, mod folder question). Not a duplicate copy. `[verified in code @1e61a29]` for the Title; `[unverified]` that no duplicate folder exists.

## Next steps (suggested order)

1. ~~Startup self-check~~ done (T-1.8). Read it in `Player.log` (search `[QudAI]`): expect `PlayerTurn patch ACTIVE`, 10 `Patched:` lines, `Patch check: 10/10 applied`. Absence of the ACTIVE line means the `PlayerTurn` patch itself failed or the mod did not compile (check `build_log.txt`).
2. Add a logging-only prefix on every `Popup` method while `active.flag` exists (name + stack trace) to catch unpatched modals.
3. C# `Prefix`: on exception with the flag present, spend a turn and `return false`. (The central energy guarantee is done, T-1.1.)
4. Atomic `action.json` (write temp, `os.replace`), tolerant parse in `ReadAction`, add a turn id, make C# timeout > LLM timeout.
5. Initialize `surroundings` at the top of each fallback function; wrap the decision step so an action is always written.
6. Treat damage-over-time separately from attacks for `is_in_combat`.
7. Lock the build template at character creation.
8. Export engine skill eligibility (`requirements_met`, `affordable`) and delete `SKILL_DATABASE`.
9. Movement arbiter with committed intents; multi-turn simulator tests; structured post-mortems for the Chronicler.
10. Bring `ENGINE_INTERNALS.md` in line with the code; run `tools/check_docs.py` in CI or as a pre-commit hook.

## Needs a human

- Retrieve `Player.log` right after a level 5 hang. Check for `HarmonyException`, `Parameter`, `Ambiguous`, `[QudAI`.
- Confirm which mod folder is loaded (the log said `QUDAITEST`; the repo calls it `QudAIBrain`). Check for duplicate copies in `...\CavesOfQud\Mods`.
- Check whether a stale `death.json` is in the QudAI folder.
- Decide what to do with the untracked-but-present `test_*.dll` files: move them into `scratch/` (silences the checker) or delete them. Not done because the task said to keep them on disk.
- Check `ancestral_wisdom.json`: confirm it contains the Gen 6 and Gen 7 lessons. The Gen 6/7 chronicles were lost and restored from the Recycle Bin, and the wisdom file may have been written without them. Confirm the restored chronicles are complete and, if lessons are missing, regenerate them from the chronicles.
- Confirm in Antigravity's Rules panel that `.agents/rules/read_project_docs.md` is active and set to always apply, and that the `@../../AGENTS.md` reference resolves. [unverified: based on third-party docs]

## Session log (newest first)

### 2026-10-04 (T-1.11): occluded threats (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.11-occluded-threats` (from `task/1.10-companion-name-cache`, so it contains T-1.10). Added `get_close_threats` in `brain.py`, used by `query_decision` and `main()` (the block was duplicated). Test 52 (6 turns, enemy behind a wall): fails on old code ("Maneuvering W ... to establish line of sight"), passes now. All 52 tests pass with the LLM forced offline. [verified in code]
- In-game observation (human-pasted console): T-1.10 worked (fought several mobs, reached level 4, pet correctly recognized). Earlier "no brain.py process" was a paused/closed console, not a crash; my crash guess was wrong.
- **Unverified in game:** T-1.11. Watch for a creature attacking from the dark being ignored.
- **Next:** merge T-1.10 + T-1.11 after an in-game run; then the popup diagnostic (`task/1.9-popup-diagnostics`) if level 5 is still unresolved.

### 2026-10-04 (T-1.10): companion name cache (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.10-companion-name-cache` (from `main` @1699d0f). C#: removed `RegisteredCompanionNames`, the name early-return in `IsCompanion`, and the registration on Proselytize attempts (IDs are now only cached after a real engine check). Python: removed `CHARMED_COMPANION_NAMES` and `is_companion_name`; companions are matched by `is_companion`, `[COMPANION:]` tags and coordinates (`drop_companion_cells`); removed instant registration after Proselytize/Beguile; `get_adjacent_threats` takes `cur_pos`. Initialized `surroundings` at the top of the four `fallback_*` functions (issue 11).
- Tests: replaced Scenario 44.4 (asserted name memory) and the stale-tag part of Test 16; added Test 51 (multi-turn, hostile baboon adjacent, never REST/AUTOEXPLORE). Test 51 fails on the old code with the name cache poisoned and passes on the new code. [verified in code]
- **Test caveat:** `dry_run.py` calls the live LLM when LM Studio is running, so some results (e.g. Test 45) vary by run. Deterministic run: point `brain.LM_STUDIO_URL` at a dead port (`python -c "import brain; brain.LM_STUDIO_URL='http://127.0.0.1:9/x'; exec(open('dry_run.py',encoding='utf-8').read())"`). All 51 pass that way. Before the issue 11 fix, `main` crashed in that mode (Test 44 area).
- **Unverified:** behavior in game; only IDs after a real engine check are cached now, so a creature that stops being a companion stays flagged until restart. Python `[COMPANION:]` handling not exercised against a live engine.
- The popup diagnostic is a separate WIP commit on `task/1.9-popup-diagnostics` (not merged). The deployed game copy now contains T-1.10 only; restart Qud to load it.
- **Next:** run in game, check `last_state.json` that wild baboons are `is_companion: false` after a Proselytize; then merge T-1.9 diagnostics if the level-5 question is still open.

### 2026-10-04 (T-1.8): Harmony startup self-check (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.8-patch-self-check`. Added `RunPatchSelfCheck()` to `AIBrainPart.cs`, called once from `Prefix`. Expected patches come from reflection over `[HarmonyPatch]` classes; applied ones from `Harmony.GetPatchInfo`.
- Verified in game 2026-10-04: mod compiled, log shows 10/10 patches applied, including `Popup.PickOption` and `Popup.ShowYesNo`. This weakens level 5 hypothesis 1 (patch never applied) for this launch; patches could still misbehave at runtime. [verified in game 2026-10-04]
- **Unverified:** negative test skipped by the human; a broken patch reporting `PATCH MISSING` is unproven.
- Noticed: `Mods\QudAI` (Sep 19) and `Mods\QudAIBrain` (Sep 28) both exist and both appear in the load order. Not investigated (still in *Needs a human*).
- **Next:** hypothesis 2 (log-only prefix on all `Popup` methods, Next steps 2), then Next steps 3-4.

### 2026-10-04 (T-1.1): central energy guarantee (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.1-energy-guard` (from `main` @7bb06cc), code in `1e61a29`. Changed `Prefix` in `AIBrainPart.cs` only, plus the card's Result and this file. No Python, `memory/` or `chronicles/` touched. Merged into local `main`; not pushed.
- Verified: braces check, py_compile, `dry_run.py` (50/50), `check_docs.py` (4 pre-existing warnings), `sync_mod.py deploy` (file copy only). [verified in code @1e61a29]
- Verified in game 2026-10-04 (human-reported): COOK_MEAL while swimming gave one `[QudAI EnergyGuard]` line; 499-turn normal run ended in character death with no new guard lines.
- **Unverified:** border crossings and stairs individually. New issues 23-26 added from the run; none traced in code.
- Usage (human-reported): about 4% hourly, under 1% weekly, Sonnet 5.5.
- **Next:** T-1.8 (Harmony self-check), then Next steps 3-4.

### 2026-10-04 (hygiene commits): docs warnings cleanup (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Three separate commits on `main`, staged by explicit path, pushed to `origin/main` together with the HANDOFF update (`ff45a99`):
  - `3e3c105`: `.gitignore` now ignores `*.dll` and `*.exe`; `git rm --cached` on `test_compile.dll`, `test_edge.dll`, `test_smart_edge.dll`, `scratch/find_declaring.exe`. Files remain on disk. [verified in code @3e3c105]
  - `c861489`: added `<!-- tests-max: 50 -->` to `docs/ARCHITECTURE.md`. `dry_run.py` has Tests 1-50 (contiguous; Tests 5 and 6 each appear twice). [verified in code @c861489]
  - `8dd3548`: README "24-scenario" changed to "50-scenario".
- `tools/check_docs.py`: 6 warnings down to 4. Remaining: hard-coded user path in `brain.py`, `twitch_bot.py`, `AIBrainPart.cs`; and "Build artifacts in repo root" for the three `test_*.dll` (the check looks at disk, so it keeps warning even though git no longer tracks them).
- Also seen, not a warning: `actions: 24 in code, 28 documented`. Four documented commands are not matched in code by the checker. Not investigated. [unverified]
- Not touched: `memory/`, `chronicles/`. Usage was not measured.

### 2026-10-04 (latest): docs merge and git safety (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Docs merged to `main` as `ab4f87d`. The GitHub PR for `docs/workflow` was not merged on GitHub; the branch was already merged locally (`b98648c`), so that merge was pushed directly. The PR may still show as open. [verified in code @ab4f87d]
- Added `tools/git_report.py` (read-only git state report) and the git safety rules in `AGENTS.md` section 5. Replaced `docs/CODEMAP.md` with the updated version.
- Data-loss incident (human-reported, not observed in this session): the Gen 6/7 chronicles were temporarily lost by a discard and were restored from the Windows Recycle Bin. The restore is not re-verified here. [unverified]
- `ancestral_wisdom.json` may be missing the Gen 6 and Gen 7 lessons (see *Needs a human*). [unverified]
- `tools/check_docs.py` passed with 6 warnings (tests-max marker, README "24-scenario" count, 3 hard-coded user paths, 3 `.dll` files in repo root). None were fixed.
- Usage: this session's token/plan usage was **not measured**, so it cannot serve as a benchmark.
- Untouched: `memory/` and `chronicles/` (two untracked `memory/runs/run_20261004_*.json` files remain uncommitted).

### 2026-10-04 (later): workflow setup (Claude, chat)
- Human subscribed to the Claude Pro plan to run Claude Code in the repo. Added `CLAUDE.md` (imports `@AGENTS.md`), `docs/WORKFLOW.md`, `docs/CODEMAP.md`, `docs/tasks/TEMPLATE.md`, and first task cards `T-1.1` (energy guarantee) and `T-1.8` (Harmony self-check).
- Plan: use T-1.1 and T-1.8 as usage benchmarks (record meter before/after in each card). Phase 1 continues from there.
- Not verified: that `CLAUDE.md` loads in the human's Claude Code install (check with `/memory`), or that Antigravity picks up `.agents/rules/read_project_docs.md`.

### 2026-10-04: review session (Claude, chat)
- Read: `brain.py`, `AIBrainPart.cs`, `build_templates.py`, `skill_database.py`, `chronicler.py`, `ENGINE_INTERNALS.md`, `GEMINI.md`, `PROJECT_HISTORY.md` (as pasted), README.
- Not read: `dry_run.py`, `item_evaluator.py`, `twitch_bot.py`, `sync_mod.py`, `scratch/`.
- `.agents/rules/` contains only `three_strikes.md`, which restates AGENTS.md R1 (no conflict). Added `.agents/rules/read_project_docs.md` to load AGENTS.md and this file.
- Output: this documentation set (AGENTS.md, docs/, tools/check_docs.py) and the issue list above.
- No code was changed. Nothing here was reproduced in game.
