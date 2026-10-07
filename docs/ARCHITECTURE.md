# QudAI: Architecture (current state)

> **This file describes the system as it is now.** Overwrite sections when behavior changes; do not append history
> here (history goes in `PROJECT_HISTORY.md`).
> Baseline: written from a review of `AIBrainPart.cs` and `brain.py` at commit `c50b3c2`. Items marked
> `[unverified]` were inferred from reading code, not observed in game.
> `tools/check_docs.py` checks the marked lists below against the code.

## 1. Components

| Component | File | Role |
|---|---|---|
| C# Harmony mod | `mod/QudAIBrain/AIBrainPart.cs` | Runs inside Qud. Exports state, executes actions headlessly, suppresses UI modals. |
| Python driver | `brain.py` | Reads state, decides an action, writes it back. Phases A/B/C below. |
| Mutation policy | `mutation_policy.py` | Ranking of all 59 mutations in the human-approved tier order: survival, safe control/ranged, traversal (Burrowing Claws, Wings), physical, situational, hazardous, defects plus the build's own priorities; published to `mutation_ranking.txt` for the mod's picker; copy of the picker rule for tests. Policy, not engine rules. |
| Build templates | `build_templates.py` | 9 archetypes: detection, stat/skill/mutation priorities, combat doctrine. |
| Skill data | `skill_database.py` | Static copy of skill costs/requirements. Engine telemetry takes priority. See Known Issues. |
| Chronicler | `chronicler.py` | Post-mortem on death; stores aphorisms in `memory/ancestral_wisdom.json`. |
| Twitch bot | `twitch_bot.py` | Optional. Viewer votes for stats/skills/mutations. |
| Item scoring | `item_evaluator.py` | Item scoring rubric. [unverified: not reviewed] |
| Tests | `dry_run.py` | Single-decision snapshot tests. Cannot see C# behavior or multi-turn loops. |
| Deploy | `sync_mod.py` | Copies the mod into Qud's mod folder. |

<!-- tests-max: 83 -->
`dry_run.py` currently holds Tests 1-83. [verified in code @3e3c105] Update the marker above when a test is added; `tools/check_docs.py` compares it to the highest `Test N` in `dry_run.py`.

## 2. IPC protocol

Exchange directory: `...\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI` (hard-coded in both files). `brain.py` and `twitch_bot.py` honor the environment variable `QUDAI_EXCHANGE_DIR` instead (the test suite points it at a temp folder so tests can never touch the real game files), and `QUDAI_LM_URL` replaces the LM Studio endpoint (tests use a dead port for deterministic, offline runs). `active.flag` is removed only when the brain is **launched** (`remove_stale_flag()` in `main()`), never at import.

| File | Direction | Notes |
|---|---|---|
| `state.json` | game -> Python | Written once per player turn (temp file + move). Python deletes it after a successful parse. |
| `action.json` | Python -> game | `{"action": "...", "reason": "..."}`. C# polls up to 6000 ms, then passes a turn. |
| `active.flag` | both | Existence = AI engaged. Deleting it restores manual control. |
| `death.json` | game -> Python | Written once on player death; consumed by the Chronicler. |
| `last_state.json` | Python | Debug copy of the last state. |
| `last_action_executed.txt` | C# | UTC timestamp + action. Useful to tell "hung" from "looping". |
| `mutation_ranking.txt` | Python -> game | Mutation names, best first (class or display names; `#` comments). Rewritten when the detected build changes; read (cached by file time) by the mutation picker. |
| `memory/decision_trace.jsonl` | Python | One JSON line per turn: turn clock, zone, position, action, reason (160 chars), combat flag, engine flags (`autoexplore_stuck`, `zone_fully_explored`, `unexplored_cells`, nearest unexplored, `reachable_edges`), chosen exit, whether exits are suppressed, last-move-failed. Rotates at 3 MB to `.1`. For diagnosing loops without pasted console output; not committed. |
| `memory/exit_choices.jsonl` | Python | One JSON line per zone-exit decision (zone, position, `reachable_edges`, reverse direction, failed/explored/cycle neighbours, candidates, novel candidates, chosen, mode). Diagnostic and future training data; not committed. |

Known protocol weaknesses (see HANDOFF): non-atomic `action.json` write, no turn id, timeouts that can race.

## 3. Turn flow

1. `XRLCore.PlayerTurn` prefix runs. If `active.flag` is absent, vanilla turn runs.
2. C# exports `state.json`, blocks waiting for `action.json`, executes it via `ExecuteCommand`.
3. Python (`main()`): parse state, update zone/stair/companion memory, compute `took_damage`, run `query_decision`,
   then the loop breakers, then write `action.json`.

### Decision pipeline (`query_decision`)

Combat mode (`is_in_combat`) = damage taken, an adjacent threat, or `get_close_threats` (enemy within 6 tiles, or 10 with `hostiles_nearby`; a non-adjacent enemy with `has_los: false` does not count, T-1.11).

Pre-checks: zone/stair records, stuck-autoexplore ingestion, template detection (every turn, see Known Issues),
emergency retreat to stairs up (underground, low HP), priority AP spend.

**Phase A: safe mode** (`not is_in_combat`), in order:
1. Autolevel (Twitch winner, else template doctrine)
2. Sustenance: butcher/harvest adjacent sources (with a 3-in-a-row cool-down), then hunger: `EAT` if he has food (no camp/cook detour, no free meal), then 2C foraging: when hungry or carrying fewer than 3 food items, `choose_food_source` walks to the nearest `food_sources` corpse (needs Butchery) or plant (needs Harvestry) with `NAVIGATE_TO_CELL`, with a pursuit time-out and a blacklist for unreachable targets (T-1.13)
3. Rest (HP < 75%, not swimming)
4. Ammo top-off; 4B. companion recruitment
5. Stairs/delving (surface needs level gate; underground is bold if HP >= 70%). After an emergency retreat from underground (low HP, or an "Impossible" creature in view even at full HP) `RETREAT_TARGET_LEVEL = level + 1` locks out further descent until that level is reached, regardless of HP (T-1.22)
6. Inward border steer (arrival grace only: first ~4 `ZONE_STEP_COUNT` on a border tile; the zone-hopping flag no longer extends it, T-1.16)
7. Native `AUTOEXPLORE` (unless stuck/explored/swimming). When autoexplore is stuck and C# reports `frontier_checked`, step 8 navigates (`NAVIGATE_TO_CELL`, committed via `FRONTIER_COMMIT`) to the nearest engine-reachable `frontier_targets` entry instead of the centroid of all unrevealed cells; none reachable with exits reachable means the engine says only rock is left (zone remembered as explored). A frontier target is written off (with neighbours within 2 tiles) after 3 failed approaches or 60 turns without arriving (`FRONTIER_FAILS`, `FRONTIER_PURSUIT`, `FRONTIER_BAD`, T-1.20), because the engine can list a target as reachable while the real step keeps failing
8. Macro-sector navigation across water/obstacles (not in towns)
9. Local unvisited frontier
10. Zone-exit transition (committed exit)
11. `NAVIGATE_ZONE_EXIT` via engine pathfinder
12. Least-visited fallback

**Phase B: tactical LLM** (combat only): LM Studio at `localhost:1234`, 6 s timeout, strict JSON, choices from a labeled
VALID ACTIONS list, ancestral wisdom prepended to the system prompt.

**Phase C: deterministic fallback** by archetype: melee, esper, gunslinger, nomad.

### Loop breakers (`main()`)

Exit-thrash breaker (`note_exit_failure`, T-1.17): every exit failure is blacklisted and counted; 4 failures in a zone suppress exit selection for 60 turns (`TURN_CLOCK`) so Phase A explores instead; an empty `reachable_edges` never wipes the blacklist. A committed frontier walk (`is_frontier_walk`: `NAVIGATE_TO_CELL` with a "Frontier:" reason) is exempt from the oscillation breaker (T-1.21). Companion-block guard (`guard_companion_blocked_burrow`, applied to the final action in `main()`): a burrow (`ATTACK_WALL`) is replaced by swap, swap, wait cycles when the only exit is occupied by a companion (T-1.17). Stationary-repeat breaker; oscillation breaker (positions window of 24, entropy rule: >=10 samples with <=5 unique);
combat actions are exempt. Zone-hopping breaker (2-, 3-, 4-cycles) in `update_zone_records`.
Autolevel circuit breaker keyed on `(ap, sp, mp, len(skills))`.

## 4. Harmony patches (C#)

<!-- patches:start -->
| Patch | Target | Purpose |
|---|---|---|
| `AIPlayerTurnPatch` | `XRLCore.PlayerTurn` | Main hook: export state, read action, execute, skip vanilla turn. |
| `AIDiePatch` | `GameObject.Die` | Export `death.json` on player death. |
| `AIPickDirectionPatch` | `PickDirection.ShowPicker` | Auto-select direction. |
| `AIPickItemPatch` | `PickItem.ShowPickerInternal` | Auto-select a safe item. |
| `AIPickGameObjectPatch` | `Popup.PickGameObject` | Auto-select a target object. |
| `AIPickTargetPatch` | `PickTarget.ShowPicker` | Auto-select target cell (ray-trace checked). |
| `AIPickFieldTargetPatch` | `PickTarget.ShowFieldPicker` | Auto-select field target cells. |
| `AIPopupShowYesNoPatch` | `Popup.ShowYesNo` | Auto-confirm Yes. |
| `AIPopupShowYesNoCancelPatch` | `Popup.ShowYesNoCancel` | Auto-confirm Yes. |
| `AIPickOptionPatch` | `Popup.PickOption` | Mutation/advancement/option picker. Normalized-name match of the option against `PreferredMutation`, then the ranking in `mutation_ranking.txt` (published by Python for the detected build), then a built-in list, then the first entry. Logs every option and the reason (`[QudAI MutationChoice]`). |
<!-- patches:end -->

Also set while AI is active: `Popup.Suppress = true`, `GameManager.runPlayerTurnOnUIThread = false`, `XRL.Core.Globals.HPWarningThreshold = 0` (kills the "Your health has dropped below N%!" press-space popup; the player's value is restored when paused).
**[unverified]** that every patch actually applied at runtime. Harmony skips a patch silently if parameter names or
overloads do not match. Add the startup self-check (HANDOFF, Next steps).

## 5. Commands (`action.json`)

<!-- actions:start -->
- `WAIT`: pass a turn
- `AUTOEXPLORE`: native autoexplore step (also picks up safe loot)
- `RELOAD`
- `FIRE_MISSILE@x,y`: single shot, sweep/rapid forced to 0, LOS + companion ray-trace checked
- `ATTACK_WALL:<dir>` (aliases `FORCE_ATTACK:`, `ATTACK_CELL:`): melee a destructible obstacle; refused in settlements
- `USE_STAIRS_DOWN`, `USE_STAIRS_UP`
- `GET_ITEM`
- `LOOT`: takes one unowned ground item, or empties one unowned chest, on his cell or an adjacent one (`TryLootNearby`); never in a settlement, never with hostiles nearby, at most 80 actions per zone; the same step also runs at the start of every `AUTOEXPLORE` turn
- `EAT`, `MAKE_CAMP`, `COOK_MEAL`, `BUTCHER`, `HARVEST`: programmatic, no UI modals
- `AUTOLEVEL`, `AUTOLEVEL_STAT:<stat>`, `AUTOLEVEL_SKILL:<class>`, `AUTOLEVEL_MUTATION:<name>`, `AUTOLEVEL_BUY_MUTATION[:<name>]`
- `REST`, `PASS`: pass a turn; they no longer spend AP/SP/MP (the old hard-coded C# autolevel ignored the template, T-1.24)
- `USE_ABILITY:<command>[:<dir>]`: alias-resolved against the player's ActivatedAbilities
- `ACTIVATE_SPRINT`, `SPRINT_<dir>`
- `NAVIGATE_TO_CELL:x,y`: engine A* (`AutoAct.TryFindPathStep`); if the next step is blocked by a solid, ownerless, non-creature object with hit points (a tree, a plant wall) it is attacked (`TryBreakPathObstacle`, reported in `last_burrow`), because the engine routes through such obstacles
- `NAVIGATE_ZONE_EXIT:<N|S|E|W>`: engine edge pathfinding (`AutoAct.TryFindEdgeStep`)
- `MOVE_<dir>`
<!-- actions:end -->

## 6. `state.json` fields (grouped)

- **Vitals/progress:** `hp`, `max_hp`, `level`, `xp`, `ap`, `sp`, `mp`, `attributes`, `skills` (class and display name),
  `learnable_skills` (only affordable ones), `mutations` (`level`, `cap`, `can_level`)
- **Position:** `x`, `y`, `z`, `zone_id`, `zone_name`, `is_settlement`, `zone_tier`
- **Ability use:** `last_ability_use` (result of the last `USE_ABILITY`: `seq`, `command`, `dir`, `known`, `cd_before`, `cd_after`, `fired` = the cooldown rose, or the ability label changed ("Lase (5 charges)" count, toggle on/off), `refused` + `reason` when the C# pre-check found the ability disabled, unusable or on cooldown, or `null`). Python `note_ability_use` counts it per command in `memory/ability_stats.json` (`attempts`, `fired`, `refused`), kept across characters. Abilities are matched by exact engine command through `data/ability_families.json` (loader `ability_registry.py`); an ability in no wired family is never used automatically (T-1.25).
- **Stationary hostiles (T-1.31):** `is_ignorable_stationary_enemy` ignores a stationary Easy-or-weaker hostile at distance 2 or more (it was 4 or more); adjacent, Tough+, turrets and damage taken still force combat.
- **Autolevel breaker (T-1.30):** `AutolevelBreaker` (used by `main`): two AUTOLEVEL decisions in a row with unchanged `(AP, SP, MP, skills)` suppress autolevel; it retries after `AUTOLEVEL_RETRY_TURNS` (100) instead of waiting for a level-up.
- **Post-mortem (T-1.38):** `chronicler.process_death_event` also calls `postmortem.write_postmortem`, which writes `chronicles/Postmortem_Gen<n>_<name>_<ts>.md` from the decision trace (`postmortem.load_trace_run`: the newest run only) and `last_state.json`: the hostiles in view with the engine rating, level and line of sight, the companions, ability cooldowns, the last 25 turns of HP and decisions with reasons, the decision mix, and rule-based observations (largest HP loss, damage right after fleeing, REST in combat, a position flip, one ability repeated). No language model is involved. The brain passes `last_state` and the trace path.
- **Ancestral lessons (T-1.37):** `chronicler.process_death_event` still saves a one-line model-written lesson per death in `memory/ancestral_wisdom.json`, but it starts `approved: false`. Only `approved: true` lessons (most recent 4) are injected into the combat prompt by `format_ancestral_memory_for_prompt`. `python tools/wisdom.py` lists them, `approve <gen>` and `reject <gen>` change the flag (nothing is ever deleted).
- **Danger retreat (T-1.36):** `border_retreat_decision` (right after the stairs-up retreat): an Impossible hostile in line of sight within 10 tiles while he is within `BORDER_RETREAT_RADIUS` (6) of the border he arrived by (`LAST_ZONE_ENTRY`) sends him back through it (`MOVE_<rev>` on the border, else `NAVIGATE_ZONE_EXIT:<rev>`), and the exit that leads into that zone goes into `FAILED_ZONE_EXITS`. The decision carries `flee_ok`, which `enforce_stand_and_fight` respects. Logged as `[DANGER RETREAT]`.
- **Stand and fight (T-1.33):** `query_decision` wraps `_query_decision` and runs `enforce_stand_and_fight` on the result. When every adjacent hostile is below Tough and no known stairs are within `STAND_STAIRS_RADIUS` (4), a flee decision (`SPRINT_*`, `ACTIVATE_SPRINT`, `NAVIGATE_*`, `USE_STAIRS*`, or a `MOVE_` that is not into an adjacent enemy) is replaced by Stunning Force, then Sunder Mind/Lase/other ready offensive abilities, then a melee bump. Applies to the LLM and every class fallback. Logged as `[STAND AND FIGHT]`.
- **Retreat to stairs up (T-1.32):** same rule as delving: `NAVIGATE_TO_CELL` first, guarded greedy fallback after PATH_BLOCKED, `STAIRS_GIVEUP` after `SECTOR_STALL_LIMIT` turns without progress.
- **Delving (T-1.29):** the route to a known stairs down is `NAVIGATE_TO_CELL` (engine pathfinder). Only after a PATH_BLOCKED report (target in `UNREACHABLE_SECTORS`) does a greedy step remain, guarded by `sector_target_ok(..., "stairs")`; 14 turns without a new closest distance puts the stairs in `STAIRS_GIVEUP` and delving to them is skipped.
- **Lase and food (T-1.28):** `filter_corpse_burners` removes the `corpse_burners` family (Lase, Flaming Ray, Pyrokinesis) from the ability list of a decision when `withhold_corpse_burners` says so: he can butcher, is hungry or holds fewer than `FOOD_RESTOCK_THRESHOLD` food items, HP is at least 50%, fewer than 3 hostiles, none Tough or worse, and the nearest hostile has `corpse_chance > 0`. Missing data never withholds. Logged as `[FOOD POLICY]` on change only.
- **On fire (T-1.27):** `fire_reaction` (before the stairs-retreat and Phase A) reads `is_on_fire`: step into adjacent deep water, else move away from `[HAZARD: fire]` cells, else do nothing (let it burn out); at most `FIRE_REACTION_MAX` (10) consecutive turns.
- **Burrowing Claws (T-1.26):** `claws_toggle_action` (Phase A, before autolevel) switches `CommandToggleBurrowingClaws` OFF when `is_town_zone` (R7) and ON elsewhere, at most once per `CLAWS_TOGGLE_GAP` (25) turns. The claws are not in a wired family: the LLM and fallbacks never see the toggle. Water/sector traversal targets are committed intents: `sector_target_ok` writes a target off after `SECTOR_STALL_LIMIT` (14) turns without a new closest distance (the "nearest cell" chase is tracked per zone and ends in `SECTOR_GIVEUP`).
- **Burrowing:** `last_burrow` (result of the last `ATTACK_WALL` swing: `seq`, `dir`, `name`, `x`, `y`, `has_hp`, `hp_before`, `hp_after`, `max_hp`, `destroyed`, or `null`). Python keeps swinging while the target loses HP, writes it off (400 turns) after 3 swings with no damage or at once if it has no HP, and `guard_blocked_burrow` swaps in another breakable obstacle, a free move, or a pass (T-1.19).
- **Exploration:** `frontier_checked`, `frontier_cells`, `frontier_targets` (T-1.18: explored walkable cells touching unexplored cells that the engine pathfinder can route to, up to 3 per quadrant NW/NE/SW/SE, never cells the player already stood on; computed only while autoexplore is stuck or the zone is engine-explored: `q`, `x`, `y`, `ux`, `uy`, `dist`), `zone_fully_explored`, `autoexplore_stuck`, `unexplored_cells`, `unexplored_centroid_x/y`,
  `nearest_unexplored_x/y/dist`, `reachable_edges` (string of N/S/E/W)
- **Move feedback:** `last_move_failed`, `last_failed_dir` (a direction, or `PATH_BLOCKED`)
- **Survival:** `hunger_level`, `is_hungry`, `is_famished`, `has_food`, `food_count`, `food_items`, `corpses_nearby`,
  `harvestable_nearby`, `food_sources` (up to 8 butcherable corpses/harvestable plants within 15 tiles: `kind`, `name`, `tx`, `ty`, `dist`; a corpse is an object with a `Butcherable` part, never a living creature; empty while swimming), `campfire_nearby`, `can_make_camp/cook/butcher/harvest` (`can_make_camp` is false when a plant or fire is within 2 cells, T-1.12), `is_swimming`, `is_on_fire`, `water_drams`
- **Loot (T-1.34):** `loot_sources` (up to 8 within 14 tiles: `kind` `item` or `chest`, `name`, `tx`, `ty`, `dist`; unowned only, empty outside settlements; an item is one the engine would autoget (`CanAutoget`, `ShouldAutoget`), not a corpse, within the weight guard; a chest is `ShouldAutoexploreAsChest` with contents and no `Brain`/`Mimic`) and `last_loot` (`seq`, `kind`, `name`, `count`, `left`). Python `choose_loot_action` (Phase A step 3B, after resting) walks to the nearest source with pursuit and blacklist guards and sends `LOOT` when adjacent; `note_loot` prints `[LOOT] ...`.
- **Combat:** `hostiles_nearby`, `hostiles_adjacent`, `effects`, `abilities`, `is_sprinting`, `has_missile_weapon`,
  `missile_ammo`, `missile_max_ammo`, `inventory_ammo`
- **Identity:** `genotype`, `subtype`, `calling` (same as subtype), `equipped_summary`
- **Entities:** `visible_entities` (`is_enemy`, `is_companion`, `can_proselytize`, `has_los`, `difficulty`, `is_stationary` (plants, fungi, immobile tags, or the engine's `!IsMobile()` for creatures), `corpse_chance` = the engine's `Corpse.CorpseChance` percent, 0 if none),
  `companions`, `has_companion`
- **Vertical travel:** `standing_on_stairs_down/up`, `stairs_down`, `stairs_up`
- **Surroundings:** 5x5 grid keyed `NW`, `N`, ..., `NW2`, `NNW`, ...; tags `[ENEMY:]`, `[COMPANION:]`, `[NPC:]`, `[BLOCKED:]`,
  `[HAZARD:]` (acid, lava, magma, and anything the engine reports aflame: `[HAZARD: fire]`), `[SWIM:]`, `[STAIRS_DOWN:]`, `[STAIRS_UP:]`, `[ITEM:]`, `[ZONE_EXIT:]`

## 6b. State ownership (target; see AGENTS.md R2)

| State | Owner today | Target owner |
|---|---|---|
| `zone_fully_explored` | C# sets it. Python reads it through `engine_confirms_explored` (the engine flag, minus the surface rule that >35 unrevealed cells with autoexplore still working means regions across water). Python only *remembers* engine-confirmed zones in `EXPLORED_ZONE_SET`; "stuck" never becomes "explored", and a stuck give-up is labelled "Autoexplore stuck, leaving zone" (T-1.15) | C# only |
| Mutation/skill eligibility | Python mirrors engine rules | C# exports legal purchases |
| Companion identity | C# `IsCompanion` (engine checks + ID cache). Python reads `is_companion` / `companions` and matches by coordinates only, never by name (T-1.10) | C# |
| Build template | Python, re-detected every turn | Detected once, persisted |

## 7. Failure memory (Chronicler)

On death: C# writes `death.json` (cause, killer, level, zone). Python gives the Chronicler the last few actions and asks
the LLM for a <=20-word aphorism, saved to `memory/ancestral_wisdom.json` and prepended (last 4) to Phase B prompts.
Limits: lessons carry no state context, only 4 are used, and LLM timeouts store a generic placeholder. See HANDOFF.

## 8. Build/run

See AGENTS.md section 3 for the verification commands. Run the agent: start Qud, load a character, `python brain.py`,
press Enter in the console to toggle AI control.
