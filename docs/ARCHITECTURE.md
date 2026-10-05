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
| Build templates | `build_templates.py` | 9 archetypes: detection, stat/skill/mutation priorities, combat doctrine. |
| Skill data | `skill_database.py` | Static copy of skill costs/requirements. Engine telemetry takes priority. See Known Issues. |
| Chronicler | `chronicler.py` | Post-mortem on death; stores aphorisms in `memory/ancestral_wisdom.json`. |
| Twitch bot | `twitch_bot.py` | Optional. Viewer votes for stats/skills/mutations. |
| Item scoring | `item_evaluator.py` | Item scoring rubric. [unverified: not reviewed] |
| Tests | `dry_run.py` | Single-decision snapshot tests. Cannot see C# behavior or multi-turn loops. |
| Deploy | `sync_mod.py` | Copies the mod into Qud's mod folder. |

<!-- tests-max: 54 -->
`dry_run.py` currently holds Tests 1-54. [verified in code @3e3c105] Update the marker above when a test is added; `tools/check_docs.py` compares it to the highest `Test N` in `dry_run.py`.

## 2. IPC protocol

Exchange directory: `...\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI` (hard-coded in both files).

| File | Direction | Notes |
|---|---|---|
| `state.json` | game -> Python | Written once per player turn (temp file + move). Python deletes it after a successful parse. |
| `action.json` | Python -> game | `{"action": "...", "reason": "..."}`. C# polls up to 6000 ms, then passes a turn. |
| `active.flag` | both | Existence = AI engaged. Deleting it restores manual control. |
| `death.json` | game -> Python | Written once on player death; consumed by the Chronicler. |
| `last_state.json` | Python | Debug copy of the last state. |
| `last_action_executed.txt` | C# | UTC timestamp + action. Useful to tell "hung" from "looping". |

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
5. Stairs/delving (surface needs level gate; underground is bold if HP >= 70%)
6. Inward border steer (first ~4 turns on a border tile)
7. Native `AUTOEXPLORE` (unless stuck/explored/swimming)
8. Macro-sector navigation across water/obstacles (not in towns)
9. Local unvisited frontier
10. Zone-exit transition (committed exit)
11. `NAVIGATE_ZONE_EXIT` via engine pathfinder
12. Least-visited fallback

**Phase B: tactical LLM** (combat only): LM Studio at `localhost:1234`, 6 s timeout, strict JSON, choices from a labeled
VALID ACTIONS list, ancestral wisdom prepended to the system prompt.

**Phase C: deterministic fallback** by archetype: melee, esper, gunslinger, nomad.

### Loop breakers (`main()`)

Stationary-repeat breaker; oscillation breaker (positions window of 24, entropy rule: >=10 samples with <=5 unique);
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
| `AIPickOptionPatch` | `Popup.PickOption` | Mutation/advancement/option picker. Uses `PreferredMutation`, then a hard-coded priority list. |
<!-- patches:end -->

Also set while AI is active: `Popup.Suppress = true`, `GameManager.runPlayerTurnOnUIThread = false`.
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
- `EAT`, `MAKE_CAMP`, `COOK_MEAL`, `BUTCHER`, `HARVEST`: programmatic, no UI modals
- `AUTOLEVEL`, `AUTOLEVEL_STAT:<stat>`, `AUTOLEVEL_SKILL:<class>`, `AUTOLEVEL_MUTATION:<name>`, `AUTOLEVEL_BUY_MUTATION[:<name>]`
- `REST`, `PASS`
- `USE_ABILITY:<command>[:<dir>]`: alias-resolved against the player's ActivatedAbilities
- `ACTIVATE_SPRINT`, `SPRINT_<dir>`
- `NAVIGATE_TO_CELL:x,y`: engine A* (`AutoAct.TryFindPathStep`)
- `NAVIGATE_ZONE_EXIT:<N|S|E|W>`: engine edge pathfinding (`AutoAct.TryFindEdgeStep`)
- `MOVE_<dir>`
<!-- actions:end -->

## 6. `state.json` fields (grouped)

- **Vitals/progress:** `hp`, `max_hp`, `level`, `xp`, `ap`, `sp`, `mp`, `attributes`, `skills` (class and display name),
  `learnable_skills` (only affordable ones), `mutations` (`level`, `cap`, `can_level`)
- **Position:** `x`, `y`, `z`, `zone_id`, `zone_name`, `is_settlement`, `zone_tier`
- **Exploration:** `zone_fully_explored`, `autoexplore_stuck`, `unexplored_cells`, `unexplored_centroid_x/y`,
  `nearest_unexplored_x/y/dist`, `reachable_edges` (string of N/S/E/W)
- **Move feedback:** `last_move_failed`, `last_failed_dir` (a direction, or `PATH_BLOCKED`)
- **Survival:** `hunger_level`, `is_hungry`, `is_famished`, `has_food`, `food_count`, `food_items`, `corpses_nearby`,
  `harvestable_nearby`, `food_sources` (up to 8 butcherable corpses/harvestable plants within 15 tiles: `kind`, `name`, `tx`, `ty`, `dist`; a corpse is an object with a `Butcherable` part, never a living creature; empty while swimming), `campfire_nearby`, `can_make_camp/cook/butcher/harvest` (`can_make_camp` is false when a plant or fire is within 2 cells, T-1.12), `is_swimming`, `is_on_fire`, `water_drams`
- **Combat:** `hostiles_nearby`, `hostiles_adjacent`, `effects`, `abilities`, `is_sprinting`, `has_missile_weapon`,
  `missile_ammo`, `missile_max_ammo`, `inventory_ammo`
- **Identity:** `genotype`, `subtype`, `calling` (same as subtype), `equipped_summary`
- **Entities:** `visible_entities` (`is_enemy`, `is_companion`, `can_proselytize`, `has_los`, `difficulty`, `is_stationary`),
  `companions`, `has_companion`
- **Vertical travel:** `standing_on_stairs_down/up`, `stairs_down`, `stairs_up`
- **Surroundings:** 5x5 grid keyed `NW`, `N`, ..., `NW2`, `NNW`, ...; tags `[ENEMY:]`, `[COMPANION:]`, `[NPC:]`, `[BLOCKED:]`,
  `[HAZARD:]` (acid, lava, magma, and anything the engine reports aflame: `[HAZARD: fire]`), `[SWIM:]`, `[STAIRS_DOWN:]`, `[STAIRS_UP:]`, `[ITEM:]`, `[ZONE_EXIT:]`

## 6b. State ownership (target; see AGENTS.md R2)

| State | Owner today | Target owner |
|---|---|---|
| `zone_fully_explored` | **Both** (C# sets it, Python overrides it in several places) | C# only |
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
