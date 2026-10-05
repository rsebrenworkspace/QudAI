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
1. Some commands `return` without spending energy (FIRE_MISSILE refusals, swim guards in MAKE_CAMP/COOK_MEAL). Python's loop breaker exempts
   combat actions, so a refused `FIRE_MISSILE` can repeat forever. Fix centrally in `Prefix` (see AGENTS.md R4).
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

## Next steps (suggested order)

1. Add the startup self-check: log every method in `Harmony.GetAllPatchedMethods()` and one `[QudAI] PlayerTurn patch ACTIVE` line. Expected: **10 patches** (see ARCHITECTURE section 4).
2. Add a logging-only prefix on every `Popup` method while `active.flag` exists (name + stack trace) to catch unpatched modals.
3. C# `Prefix`: central energy guarantee after `ExecuteCommand`; on exception with the flag present, spend a turn and `return false`.
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
