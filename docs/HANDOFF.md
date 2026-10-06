# QudAI: Handoff

<!-- handoff-updated: 2026-10-05 -->

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
17. **fixed in T-1.15 (merged to `main` as `2d8dce0`; verified in game 2026-10-04, human-reported; the one exception is Joppa, a town, where the brain still leaves instead of exploring, and the human is fine with that).** Original description: `zone_fully_explored` is overridden by Python in several places (see ARCHITECTURE 6b). Iterations 38 and 40 reverted each other.
18. Chronicler: lessons use only the last 6 action names (no state), only the last 4 are injected, LLM-timeout fallbacks are stored as wisdom,
    paths hard-coded to `D:\QudAI`.
19. `SKILL_DATABASE` is a static copy of engine data. C# exports only *affordable* skills, which is why Python needs the copy.

**Hygiene**
20. Hard-coded user paths in `brain.py` and `AIBrainPart.cs`; `D:\QudAI` in docs vs `C:\Users\...` in code.
21. `test_*.dll` and probe scripts are still on disk in the repo root (no longer tracked or committable since 3e3c105, but `check_docs.py` still warns because it checks disk, not git). README/ARCHITECTURE test counts fixed (50) in 8dd3548 / c861489.
22. `ENGINE_INTERNALS.md` is stale in places: says `isCycling` sets `isZoneFullyExplored = true` (code sets `false` + stuck flag), buffer size 10 (code 24),
    claims `Popup.Show`/`ShowOptionList` patches that do not exist, names `PlayerTurn.Prefix` and `bSuppressPopups` (code: `XRLCore.PlayerTurn`, `Popup.Suppress`).
    Section numbering repeats (11.4, 12.2).

41. **Partly superseded by issue 42.** The human console (2026-10-05) showed the swap with the pet **works**; the burrow loop I saw in `Player.log` was a different symptom. `guard_companion_blocked_burrow` (T-1.17) stays as a harmless safety net for pet-sealed dead ends but was not the cause. Human report (2026-10-05): after entering a dungeon (z=11, "workshop of Mehruwer", level-5 character, so the delve gates were fine) he looped in a hallway. `[verified in code/log]`: he stood at the dead end (27,4) of a one-tile corridor, solid rock N/E/W, his recruited horned chameleon in the only exit (27,5); `Player.log` shows 17 `ATTACK_WALL` burrow attempts at (27,4) interleaved with other turns. Python's decision was correct (`MOVE_S`, "Water Traversal ... sector (40,11)") but `player.Move("S")` into the companion apparently did not swap places, `autoexplore_stuck` stayed true and `reachable_edges` was empty (the engine pathfinder treats the pet as a wall), so the loop breaker kept burrowing at rock. Engine swap rules in ENGINE_INTERNALS 12.1f. `[unverified]` why the swap was refused. Options: (a) C# forced swap when `MOVE_` hits a companion (`DirectMoveTo`/`ForceSwap`, signatures unchecked, cannot compile locally), (b) Python: never burrow when the "pocket" is caused by a companion, wait a turn so the pet moves, (c) both.
47. **fixed in T-1.21 (branch `task/1.21-frontier-trees`; C# changed, needs a Qud restart and "Success :)"; not verified in game).** Human report: "still working through the area but does not want to hit the one area he needs; a tree could be blocking the one exit". `decision_trace.jsonl` t519-537 `[verified in data]`: 20 consecutive "[Loop Breaker] Oscillation trapped in cycle" moves between (16,16) and (16,17) while `last_state.json` still offered SW frontier targets (19,17), (20,17). Two causes: (1) the oscillation breaker overrides Phase A's decision whenever positions repeat, and its own frontier option is disabled in dungeons (z>10 with autoexplore stuck), so it only shoves him back and forth; a committed frontier walk now bypasses it (`is_frontier_walk`; the 3-failure and 60-turn limits still apply). (2) C# `NAVIGATE_TO_CELL` refused any step into an occluding cell, but the engine routes through trees, so those paths always failed and the target was written off after 3 tries (T-1.20) and the exit never taken; C# now attacks a solid, ownerless, non-creature blocker with hit points (`TryBreakPathObstacle`, logs `[QudAI PATH_OBSTACLE]`, reports in `last_burrow`), and an unbreakable one writes the frontier target off. Test 65. `[unverified]` that the blocker at (9,16)/(19,17) is a tree: the trace does not record surroundings.
46. **fixed in T-1.20 (branch `task/1.20-frontier-failure`, Python only, stacked on T-1.19; not verified in game).** Human report: "he paced around a section and the process stalled; one unexplored path he has not taken" (SW cave region). `decision_trace.jsonl` t783-812 `[verified in data]`: 30 turns on `NAVIGATE_TO_CELL:11,7` (a NW frontier target beside a door and chest) with `last_move_failed` true on almost every approach, kept alive by the T-1.18 commitment (`FRONTIER_COMMIT`), which had no failure feedback, while the loop breakers pushed him around. The engine pathfinder listed the target as reachable but the step failed (cause unknown `[unverified]`: possibly a locked or stuck door; `TryOpenDoorInDirection` only fires an `Open` event). Fix: 3 failed approaches or 60 turns without arriving write the target off in `UNREACHABLE_SECTORS`, along with neighbours within 2 tiles (`FRONTIER_BAD`), so he moves on to the next frontier (the SW area). Test 64. The "stall" was the AI being **paused** (`active.flag` removed; only an Enter keypress in the brain console toggles it: `input_listener`), not a hang; `brain.py` was idle at 0% CPU. A second `brain.py` PID I saw was my own PowerShell query matching the string.
45. **fixed in T-1.19 (branch `task/1.19-burrow-hp`, C#, needs a compile; not verified in game).** Human report: he cut a number of trees, then "hit a roadblock and stopped everything". `[verified in data]`: the trace shows 8 consecutive `ATTACK_WALL:N` at (13,12) on a shimscale mangrove tree, then the AI was **paused** (`active.flag` missing, `brain.py` idle), not crashed. `[verified in game blueprints]`: that tree inherits `SolidTree` > `Tree` > `Plant` > `PhysicalObject`, which supplies 25 hit points, so it is breakable; with a staff doing about 1-2 damage that is roughly 15-20 swings. The engine pathfinder routes through such trees (`frontier_targets` and `NAVIGATE_TO_CELL` treat them as reachable). Fix: C# reports each swing in `last_burrow` (HP before/after, destroyed); Python tracks progress (`note_burrow_progress`) and never gives up on a tree that is losing HP, writes off targets with no HP or 3 swings of no damage, and `guard_blocked_burrow` picks another obstacle / free move / pass. Test 63. Chests added to the backlog as B6 (not started, needs promotion).
44. **fixed in T-1.18 (branch `task/1.18-reachable-frontier`, not verified in game; C# needs a compile).** `decision_trace.jsonl` (307 turns) `[verified in data]`: (a) the original "Corridor blocked by companion: swapping" breaker toggled him in and out of the dead end (t263-271: MOVE_S, MOVE_N, ...) because it fired whenever every valid move had been visited twice, even with a free move away; now it fires only when `not valid_m`. (b) He flip-flopped between "Water Traversal toward unexplored sector (40,11)" (a greedy one-step walk to the centroid of ALL unrevealed cells, mostly rock) and "Autoexplore stuck ... scouting zone frontier" (a local least-visited step), 9-turn cycle around (32,11); AGENTS R6 bans greedy one-step movement. (c) `nearest_unexplored` pointed at rock behind walls, so the real unexplored regions (the human's southwest corner) were never targets. Fix: C# `BuildFrontierJson` exports engine-reachable frontier targets (ENGINE_INTERNALS 14.5); Python `pick_frontier_target` navigates to the nearest with `NAVIGATE_TO_CELL`, committed (`FRONTIER_COMMIT`), blacklisting via `UNREACHABLE_SECTORS`; no reachable target with exits reachable is engine-confirmed explored; pet-sealed corridor (no edges) is not remembered. Test 62. `[unverified]`: that `TryFindPathStep` routes through deep water (if not, water-separated regions would be reported unreachable and he would leave early: watch for "Zone fully explored" with a visibly unexplored lake shore).
43. **superseded by 44; kept for history. open, instrumented (T-1.17).** Human report after testing the issue-42 fix: he left the hallway eastward (console: "Water Traversal ... toward unexplored sector at (40,11) (1704 unrevealed cells)", y=11, x=30..33 `[verified in console]`), then "hit explored territory and moved right back into the hallway and loops". The exit log shows the blacklist now persists (`failed` grows `['N']`, `['N','W']`, `['N','S','W']`). `[unverified]` suspicion: the unrevealed cells behind the dead end's rock count as "unexplored" (C# `nearest_unexplored` was (25,2) while standing at (27,4)), so the frontier/sector logic keeps targeting cells it can never reach. Added `memory/decision_trace.jsonl` (one line per turn) so the next loop can be read from the file.
42. **fixed in T-1.17 (not verified in game).** The real hallway loop, from the human console plus `memory/exit_choices.jsonl` `[verified in code/data]`: at (27,5) the engine reports all four exits reachable, the picker chooses N, the engine's step takes him north into a one-tile dead end, the pet follows and seals him in, the engine reports **no** reachable exits, `check_exit_direction_failure` blacklists the exit, and with no candidates the "all failed" branch **wiped every blacklisted exit for the zone** (`reachable_set` empty is falsy). He swaps out, the same N/W exits are picked again, forever (`failed_here` was `[]` on every N pick). Fix: an empty `reachable_edges` returns "No Reachable Exit" without touching the blacklist; all exit failures go through `note_exit_failure`; 4 failures in a zone suppress exit selection for 60 turns so Phase A explores (e.g. the water traversal it had chosen) instead. Test 60 replays the cycle (old code: S,S,E,W,N,N,W,E; new: N,W,E,S, then stands down). **Still open:** why the engine's edge step leads into the dead end while it reports the exits reachable `[unverified]`.
40. **fixed in T-1.16 branch (C#, not verified in game; check `build_log.txt`).** Human report: when HP falls below 40% a prompt appears and stops automation. Cause `[verified in code]`: `XRLCore.PlayerTurn` calls `Popup.ShowSpace("Your health has dropped below N%!")` using `Globals.HPWarningThreshold`, default `"40%"` from the option `OptionDisplayHPWarning`; `Popup.Suppress` does not stop it and no mod patch covers `ShowSpace`. Fix: the mod zeroes the threshold while the AI is engaged and restores the player's value when paused (ENGINE_INTERNALS 12.1e). If a different low-HP prompt still appears, enable the popup diagnostic (`task/1.9-popup-diagnostics`) to log its method and stack.
39. **fixed in T-1.16 (not verified in game).** "Dance on the zone line": `ZONE_HOPPING_DETECTED` is set by a single A->B->A return and stays true for the whole stay in the next zone; step 6 (inward border steer) fired on any border cell while it was set, so he walked to the line, stepped back inward, and could never cross. Reproduced: same position and chosen exit, flag off => `MOVE_W` across; flag on => `MOVE_NE` inward. The log also showed zones alternating (`11.20.1.0` <-> `11.19.1.2`) with E/W chosen but N/S taken. Fix: step 6 depends only on `ZONE_STEP_COUNT <= 4`; the flag still steers exit choice. Test 58 (approach x=6..0). `[verified in code]`
38. **open, instrumented in T-1.16 (branch `task/1.16-exit-choice-log`).** Human report: after a zone is done he "only wants to head north"; the intent was random exit choice for viewer variety, later replaced by learning from past runs (not built). Findings: it is **not** autoexplore (C# calls `FindAutoexploreStep(false, ...)`, which excludes zone exits). `get_zone_exit_target` is a fair `random.choice` among reachable, non-reverse, non-failed, non-explored exits: simulation gave E/N/W 104/105/91 of 300 mid-zone `[verified in code]`. Live zone IDs went from `11.22.1.1` to `11.20.1.0` (7 zones, same sub-grid column), about 0.05% by chance if each hop were a 3-way coin flip, so the *inputs* are narrowing it. Candidates `[unverified]`: (a) `reachable_edges` often lists only N (canyon corridors) and the reverse exit is excluded, (b) neighbours in `EXPLORED_ZONE_SET`, (c) adjacent-exit shortcuts that take `forward_exits[0]`. Next: play a few zones, then read `memory/exit_choices.jsonl` (added in T-1.16) to see which input forces N.
**New (from the fire death, 2026-10-05 UTC; human-reported: hungry, made camp, walked into the fire, burned, died. The run record had not been archived when written, so the exact sequence is `[unverified]`)**
30. **fixed in T-1.12 (branch `task/1.12-fire-safety`, not yet verified in game).** `MAKE_CAMP` had no check of its surroundings; a campfire among dogthorn trees ignites them. Now `can_make_camp` is false (and `MAKE_CAMP` is refused with a turn spent) when a plant (`Physics.Category == "Plants"`) or anything aflame is within 2 cells. Python then falls back to EAT.
31. **fixed in T-1.12.** Fire was not a hazard: `[HAZARD:]` only matched acid/lava/magma/convalessence by name. Now any object where `IsAflame()` / `Burning` / a `Campfire` part is tagged `[HAZARD: fire]`; Python already refuses `[HAZARD` cells. Probable cause of the empty `reachable_edges` and the two-cell ping-pong seen while the fire burned (engine pathfinder routes around flames). `[unverified]`
32. **open.** No reaction to being on fire. C# now exports `is_on_fire`, but Python does not use it. Needs: leave the flames, step into water if adjacent. Do not guess at Qud's extinguish rules; inspect first (`Campfire.FindExtinguishingPool` exists).
34. **A and B done in T-1.13 (branch `task/1.13-earn-dinner`, stacked on the fire branch; not verified in game); C open.** **Design decision (human, 2026-10-04): make him earn his dinner.** No free meals. Findings `[verified in code]`: (a) `COOK_MEAL` calls `ClearHunger()` even when no ingredient was consumed, so camping with an empty pack cures hunger for free; Python tries `MAKE_CAMP` before `EAT`. (b) Corpses are only counted in the 3x3 around the player and nothing walks him to one. (c) The character at level 4 had no `CookingAndGathering`/`Butchery` skills (only `Survival_Camp`), so `can_butcher` was false; 34 SP unspent, Butchery chain costs 100 + 50 SP. (d) Lase kills take the Fire/Light corpse path (see ENGINE_INTERNALS 12.1b); corpses are also probabilistic (Baboon 40%). He still held 5 food items and was Satisfied, so starvation was not imminent. Proposed split: **A** remove the free meal and eat-before-camp; **B** export butcherable corpses/plants with coordinates and have Python walk to them (needs the skills, so also a skill-priority check); **C** a "don't Lase food animals when hungry and out of food" policy. Not started.
35. **fixed in T-1.13.** `corpses_nearby` and the `BUTCHER` handler used `HasPart("Corpse")`, which living creatures (and the pet) also carry, so with the Butchery skill an adjacent pet would have triggered a `BUTCHER` no-op every turn. Now only objects with a `Butcherable` part and no `Brain` count. `[verified in code]`
36. **fixed in T-1.14 (branch `task/1.14-food-skills`, stacked on T-1.13; not verified in game).** Findings `[verified in code]`: the templates already listed Cooking/Butchery, but rifle and pistol builds had them at position 5-8 (400-450 SP before Butchery), **no template listed Harvestry**, and Butchery/Harvestry need Intelligence 15 while only the two pistol builds ever raised Int. The level-4 Esper simply had not accumulated the ~200 SP yet (Tactics 50 + Cooking 100 + Butchery 50; he had 34 SP unspent). Now every template places the block Cooking, Butchery, Harvestry, MealPreparation at index min(old position, 3), and 12 of 14 templates gained an Intelligence 15 stat target in third place (the two pistol builds keep Int 19). Butchery is bought after 200-350 SP spent in the simulation (Test 55). **Not changed:** the Esper still needs ~200 SP; SP income per level was not measured. Original description: to forage he needs `CookingAndGathering` (100 SP) then `Butchery` (50 SP), plus `Harvestry` for plants. The level-4 character had none (34 SP unspent). Check the skill-priority order in `build_templates.py` actually buys them before expensive combat skills.
37. `[unverified]` `EAT` fires the engine `Eat` event and then also calls `Stomach.ClearHunger()`, so one jerky serving may clear all hunger. Needs an in-game test (does the event alone feed him?).
33. `[unverified]` Plants-only flammability is a narrow rule; wooden furniture, grass-like objects with other categories, and oil/honey puddles (`FlameTemperature` 350) are not counted.

**New (from the 2026-10-05 UTC baboon death, level 2; `[verified in code @T-1.10]`, in-game confirmation pending)**
27. **fixed in T-1.10 (branch `task/1.10-companion-name-cache`, not yet verified in game).** A name-based companion cache (C# `RegisteredCompanionNames`, Python `CHARMED_COMPANION_NAMES`, filled on every Proselytize *attempt*) made every baboon a "companion" after one recruit attempt. `last_state.json` showed 13 baboons with `is_companion: true`. Effects: hostile baboon had `is_enemy: false`, `is_in_combat` was false, Phase A chose `REST` at 6 and 2 HP with a baboon adjacent, offensive abilities aborted (`Lase (4 charges)` unused), the LLM only repositioned. Probably the cause of earlier "tried to disengage" runs. Also fixed in the same branch: issue 11 (`surroundings` unbound in all four fallbacks).

28. **fixed in T-1.11 (branch `task/1.11-occluded-threats`, not yet verified in game).** Enemies 2-4 tiles away behind an impassable wall (no line of sight) forced combat mode; the LLM spent ~14 turns "maneuvering to establish line of sight" while swimming in a lake, and Phase A never ran. New `get_close_threats` ignores non-adjacent enemies with `has_los: false`. Risk `[unverified]`: an unseen creature approaching in the dark is ignored until it is visible, adjacent, or damages us.
29. **fixed in T-1.15.** Original: `[unverified]` Console shows "Zone fully explored: navigating ... exit S" while `unexplored_cells` was 1251 and `zone_fully_explored` false: Python overriding the engine flag (issue 17).

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

### 2026-10-05 (T-1.21): frontier walks vs the breaker, and trees (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.21-frontier-trees` (from `task/1.20-frontier-failure`; T-1.19/1.20 are also unmerged). Python: `is_frontier_walk` exempts frontier walks from the oscillation breaker; an unbreakable obstacle (`note_burrow_progress`) writes off the committed frontier target. C#: `TryBreakPathObstacle` in `NAVIGATE_TO_CELL`. Test 65. All 65 pass with the LLM forced offline. [verified in code]
- **Needs:** Qud restart + `build_log.txt` "Success :)" (T-1.19 and T-1.21 C# are both uncompiled), then `python brain.py`. Look for `[QudAI PATH_OBSTACLE]` in `Player.log`.

### 2026-10-05 (T-1.20): frontier failure feedback (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.20-frontier-failure` (from `task/1.19-burrow-hp`; both unmerged, and the T-1.19 C# still needs a Qud restart + compile). `brain.py`: `pick_frontier_target` learns from `last_move_failed` after `NAVIGATE_TO_CELL`, caps pursuit at 60 turns, writes targets off with their neighbours (radius 2). Test 64 (replay of the 30-turn trace pattern: after 3 failures he heads for the SW target; neighbour skipped; pursuit cap; sub-limit failures forgiven). All 64 pass with the LLM forced offline. [verified in code]
- **Open:** why the step to (11,7) failed (door state?); chests and doors are in the backlog area (B6). Console should show `[FRONTIER] Writing off target ...`.

### 2026-10-05 (T-1.19): burrow progress (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.19-burrow-hp` (from `main` @d8e3082). C#: `last_burrow` in `state.json`, set after each `ATTACK_WALL` swing (`HasStat("Hitpoints")`, `hitpoints`, `baseHitpoints`, destroyed test). Python: `note_burrow_progress`, `blocked_burrow_dirs`, `guard_blocked_burrow`, `find_burrow_direction(exclude=...)`. Test 63; all 63 pass with the LLM forced offline. `docs/BACKLOG.md` B6 (chests) added. [verified in code]
- **Needs:** Qud restart + `build_log.txt` "Success :)" (cannot compile locally), then `python brain.py`; `Player.log` shows `[QudAI ATTACK_WALL] <target>: HP a -> b/max` per swing, and the console shows `[BURROW]` lines.

### 2026-10-05 (T-1.18): reachable frontier (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.18-reachable-frontier` (from `task/1.17-companion-blocked-corridor`, so it carries T-1.16/T-1.17 too; none merged). C#: `BuildFrontierJson` (+ `frontierVisited`), called from the state export while stuck/engine-explored; deployed after this entry. Python: `pick_frontier_target`, sector selection prefers frontier targets, `engine_confirms_explored` accepts "no reachable frontier and exits reachable", swap breaker only when no free move. Tests: Test 62 (SW target chosen over the centroid, 5-step commitment, arrival, blacklist, nothing reachable, sealed corridor). All 62 pass with the LLM forced offline. [verified in code]
- **Compile verified in game 2026-10-05 (human-reported: `build_log.txt` "Success"); merged to `main` at the human's request.** Behaviour of `frontier_targets` (SW corner, water routing) still to be confirmed from `last_state.json` and `memory/decision_trace.jsonl`.

### 2026-10-05 (T-1.17): companion blocking a dead-end corridor (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.17-companion-blocked-corridor` (from `task/1.16-exit-choice-log`, so it also carries the exit log, the zone-line fix and the low-health popup fix, none merged yet). Added `guard_companion_blocked_burrow` + `COMPANION_BLOCK`, called in `main()` after all loop breakers, before the action is recorded: a burrow decision with no non-companion open move and an adjacent companion becomes `MOVE_<companion dir>` twice then `WAIT`, repeating; real pockets and other actions untouched. Test 59 (9 turns at the same cell, plus untouched cases) and a check against his real saved state. All 59 pass with the LLM forced offline. [verified in code]
- **Later the same day:** human test of issue 42 fix: left the hallway, then turned back (issue 43). Added `decision_trace.jsonl` + Test 61; no fix for 43 yet.
- **Unverified in game.** **Correction:** the human console later showed the pet swap works, so the C# forced-swap option is dropped; the real loop was the exit-blacklist wipe (issue 42, same branch, Test 60).
- **Next:** one test run of this branch covers: zone-line dance, low-health popup, exit log, this hallway guard. If it works, merge to `main`.

### 2026-10-04 (T-1.16): exit-choice log (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.16-exit-choice-log` (from `main` @3e064ed). `brain.py`: `log_exit_choice` + one JSON line per exit decision (see ARCHITECTURE IPC table). `dry_run.py`: the suite writes to a temp log, never the real one; new Test 57 (record contents, cached choice not re-logged, unwritable path never raises). All 57 pass with the LLM forced offline. [verified in code]
- Simulation (`scratch`-style, not committed): mid-zone choice is uniform over N/E/W; on arrival at a border the first step is "Border Navigation" inward. So no code bias toward north was found; the data must come from `reachable_edges` or the explored sets (HANDOFF issue 38).
- **Also on this branch (C#):** low-health popup removal (issue 40). Deployed to the game folder; needs a Qud restart.
- **Update (same branch):** the first log lines (5 decisions) were varied (E, N, W, E, E, not north-only) but showed `hopping: true` and bouncing between vertical neighbours. Found and fixed the zone-line dance (issue 39, Test 58). The "only north" report may largely have been this bounce; still check the log over a longer run.
- **Next:** play several zone hops with this fix, then read `memory/exit_choices.jsonl` and decide what "learn from previous runs" should mean.

### 2026-10-04 (T-1.15): "zone fully explored" is only the engine's claim (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.15-explored-flag` (from `main` @8ca794c). `[verified in code]` Findings: Python had **five** writers into `EXPLORED_ZONE_SET` (zone-leave, decision block, stuck-forced, oscillation breaker, failed `NAVIGATE_TO_CELL` incl. food foraging); `stuck_autoexplore_zones` never expired, so "stuck once" meant "stuck forever"; the leave-zone code tested the *new* zone's flag. Reproduced on old code: stuck + no frontier + 1251 unexplored => "Zone fully explored", remembered permanently.
- Fix: new `engine_confirms_explored` (engine flag, minus the surface >35-cells water rule); the set is written in exactly two places (top of `query_decision`, and on zone change from `ENGINE_EXPLORED_LAST`); a successful autoexplore step with no engine "stuck" clears the stuck mark; a fresh visit clears it too; the stuck give-up still leaves the zone but is labelled "Autoexplore stuck, leaving zone" (`zone_label`) and is not remembered. Tests: new Test 56 (incl. the real bug path), Scenario 25.4 and Test 11 fixtures isolated (they reused one zone ID with contradictory engine data). All 56 pass with the LLM forced offline.
- `ENGINE_INTERNALS.md` corrected (`isCycling` sets `false` + stuck; meaning of `zone_fully_explored`).
- **Verified in game (human-reported):** works as intended; towns such as Joppa are still left rather than explored, by choice. **Not changed:** the surface ">35 cells => not explored" rule, which deliberately overrides the engine for regions across water; `UNREACHABLE_SECTORS` (still session-persistent).
- **Next:** play and watch for the label "Autoexplore stuck, leaving zone": if it appears with a reachable frontier, send me the console lines.

### 2026-10-04 (T-1.14): food skills in the build templates (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.14-food-skills` (from `task/1.13-earn-dinner`). `build_templates.py`: Cooking/Butchery/Harvestry/MealPreparation block at index `min(old, 3)` in all 14 templates (9 defined directly, 5 derived from them); Intelligence 15 target inserted third where absent. `dry_run.py`: Scenario 22.3 fixture now includes Harvestry (the new order buys it next); new Test 55 simulates every template buying skills as SP trickles in (Butchery position <= 6, Int steering for a low-Int character). All 55 pass with the LLM forced offline. [verified in code]
- **Unverified:** in game; SP income per level; that the engine's Intelligence minimum for Butchery/Harvestry is 15 (`skill_database.py` is a static copy of engine data, see HANDOFF issue 19 and AGENTS R3).
- **Next:** launch both food branches and the fire branch together, check `build_log.txt`; then part C (Lase policy) and issue 37.

### 2026-10-04 (T-1.13): earn dinner, A + B (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.13-earn-dinner` (from `task/1.12-fire-safety`, so it contains T-1.12 and the docs commit; neither is merged). **A:** `COOK_MEAL` no longer clears hunger without consuming an ingredient; Python hunger relief is `EAT` only (no `MAKE_CAMP`/`COOK_MEAL`); scenarios 24.3/24.4 changed to expect `EAT`. **B:** C# exports `food_sources`; `corpses_nearby`/`BUTCHER` now use `Butcherable` objects only (issue 35); Python `choose_food_source` (committed `NAVIGATE_TO_CELL`, 40-turn pursuit cap, blacklist on `PATH_BLOCKED`, skill gates) and a `BUTCHER` cool-down after 3 in a row.
- Tests: Test 54 (skill gates, corpse before plant, blocked-target blacklist over 6 turns, pursuit time-out, no free meal, butcher no-loop over 12 turns). All 54 pass with the LLM forced offline. [verified in code]
- **Unverified:** C# compile (read `build_log.txt` after launching); that corpses/plants actually appear in `food_sources` in game; that `NAVIGATE_TO_CELL` reaches corpse cells; `AttemptButcher` result.
- **Open:** issues 36 (skills never bought) and 37, and part C (Lase policy). Without Butchery he cannot forage corpses at all.
- **Next:** launch, check `build_log.txt`, watch `food_sources` in `last_state.json` after a kill; then issue 36.

### 2026-10-04 (T-1.12): fire safety (Claude Code, Sonnet 5.5 `claude-sonnet-5-5`)
- Branch `task/1.12-fire-safety` (from `main` @7a32c8c, which now contains T-1.10 and T-1.11, merged and pushed). C#: `IsCampSpotSafe`, `IsObjectAflame`, `IsOnFire`; `[HAZARD: fire]` tag in `GetCellSummary`; `is_on_fire` in `state.json`; `MAKE_CAMP` refuses an unsafe spot. Engine facts from the game DLL and blueprints: `GameObject.IsAflame()`, `Physics.Category` / `FlameTemperature` exist; Dogthorn Tree inherits Tree > Plant (Category "Plants"); Campfire part has `FlameTemperature=10000`. [verified in code]
- Python: no code change needed (it already refuses `[HAZARD` cells). Test 53 pins that contract and the EAT fallback; it would also pass on the old Python, so it does **not** prove the C# fix.
- **Unverified (needs a game launch):** C# compile (check `build_log.txt` for "Success :)"), that burning trees and a lit campfire report `IsAflame()`/get the tag, that `Physics.Category` is "Plants" for dogthorn trees at runtime, and that unsafe camp spots are not too common (false refusals just mean he eats instead).
- Dead end recorded: local Roslyn compile from PowerShell (see DECISIONS).
- **Next:** launch the game, check `build_log.txt`, then an in-game camp near trees; then issue 32 (react to being on fire).

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
