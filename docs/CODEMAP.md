# QudAI: Code map

> Purpose: let an agent read only the functions a task touches. Function names, not line numbers (line numbers drift).
> Baseline: names verified by reading the code at commit `c50b3c2`. Files marked `[not reviewed]` are described from their names only.
> Update this file when you add, rename, or move a function. Use `grep -n "<name>"` to find it.

## `mod/QudAIBrain/AIBrainPart.cs` (C#, ~3,800 lines, namespace `QudAIBrain`)

### Class `AIPlayerTurnPatch` (Harmony patch on `XRLCore.PlayerTurn`, plus all helpers)

| Area | Functions |
|---|---|
| Turn entry | `Prefix` (flag check, popup suppression, export, read action, execute, skip vanilla turn), `EnsureLightSource` |
| State export | `ExportState` (builds all of `state.json`), `GetEquippedSummary`, `GetCellSummary` (5x5 tile tags), `GetApproximateDirection`, `StripQudFormatting`, `EscapeJson` |
| IPC | `ReadAction` (polls `action.json`, 6000 ms), `ExportDeath` (writes `death.json`) |
| Command dispatch | `ExecuteCommand` (one big if-chain: see ARCHITECTURE section 5 for the command list) |
| Movement | `ExecuteAutoexplore` (native autoexplore + cycle detection + stuck flags), `TryOpenDoorInDirection`; `NAVIGATE_TO_CELL` and `NAVIGATE_ZONE_EXIT` live inside `ExecuteCommand` |
| Leveling | `ExecuteAutolevel`, `AllocateStat`, `AllocateMutation`, `BuyNewMutation`, `AllocateSkill` |
| Combat | `ExecuteMissileFire` (reflection call with sweep/rapid forced to 0), `ExecuteReload`, `GetLineBetween` (Bresenham), `GetBestEnemyDirection`, `GetBestAdjacentEnemyDirection` |
| Entity classification | `IsCompanion`, `CheckIsEnemy`, `CanBeProselytized`, `CanSafelyLoot`, `GetSafeZoneObjects`, `IsDownPassage`, `IsUpPassage`, `IsSettlementZone` |
| Static state | `lastMoveFailed`, `lastFailedDir`, `isZoneFullyExplored`, `isAutoexploreStuck`, `autoexplorePosHistory`, `PreferredDirection/TargetCell/TargetObj/Mutation`, `RegisteredCompanionIds/Names` |

### Other Harmony patch classes (all gated on `active.flag` existing)

`AIDiePatch` (`GameObject.Die`), `AIPickDirectionPatch`, `AIPickItemPatch`, `AIPickGameObjectPatch`, `AIPickTargetPatch`,
`AIPickFieldTargetPatch`, `AIPopupShowYesNoPatch`, `AIPopupShowYesNoCancelPatch`, `AIPickOptionPatch` (mutation/advancement picker).

### If you are touching...
- a command that "does nothing" or loops -> `ExecuteCommand` branch for that command, and `Prefix` (energy accounting)
- level-up or a modal that blocks -> `AIPickOptionPatch`, `AIPopupShow*` patches, `ExecuteAutolevel`, `BuyNewMutation`
- exploration state fields -> `ExecuteAutoexplore` and the exploration block inside `ExportState`
- companions -> `IsCompanion` first, then the ray-trace checks in the `FIRE_MISSILE` and `USE_ABILITY:` branches

## `brain.py` (Python driver)

| Area | Functions / globals |
|---|---|
| Constants/helpers | `CARDINAL_OFFSETS`, `DIRECTIONAL_ABILITIES`, `PROSELYTIZE_EXCLUSIONS`, `min_level_for_depth`, `is_swim_move`, `get_best_move_towards`, `get_step_direction` |
| Zone tracking | `update_zone_records` (zone cycles, entry border), `find_zone_unexplored_frontier`, `_compute_adjacent_zone_id`, `check_exit_direction_failure`, `get_zone_exit_target`, `CURRENT_ZONE_CHOSEN_EXIT`, `FAILED_ZONE_EXITS`, `EXPLORED_ZONE_SET`, `UNREACHABLE_SECTORS`, `sector_target_ok`/`SECTOR_GIVEUP` (water-sector progress), `claws_toggle_action` (claws policy), `fire_reaction` (on-fire response), `withhold_corpse_burners`/`filter_corpse_burners` (Lase vs food), `STAIRS_GIVEUP` (delve fallback), `AutolevelBreaker` (autolevel circuit breaker), `choose_loot_action`/`note_loot` (loot walking),  `must_stand_and_fight`/`enforce_stand_and_fight`/`STAND_CONTEXT` (no fleeing from weak adjacent attackers) |
| Stairs | `is_valid_stair_down`, `get_stair_priority`, `update_stair_records`, `KNOWN_STAIRS_DOWN/UP` |
| Entities | `is_companion_name`, `register_companion`, `is_proselytizable`, `is_peaceful_npc`, `is_town_zone`, `filter_hostile_enemies`, `get_adjacent_threats`, `is_ignorable_stationary_enemy`, `find_burrow_direction` |
| Geometry | `get_valid_moves`, `render_5x5_grid`, `bresenham_line`, `is_line_of_fire_clear` |
| Abilities | `is_ability_ready`, `find_ready_ability` |
| Phase B (LLM) | `query_llm_decision` (builds prompt + valid-action list, calls LM Studio, safety overrides), `detect_lm_studio_model` |
| Phase C (fallbacks) | `fallback_melee`, `fallback_esper`, `fallback_gunslinger`, `fallback_nomad` |
| Decision core | `query_decision` (pre-checks, Phase A steps 1-12, then B, then C) |
| Main loop | `main` (state parse, companion memory, `took_damage`, autolevel breaker, loop breakers, write `action.json`), `input_listener` |

### If you are touching...
- hangs / "no action written" -> `main` (the `try/except` that prints `[Loop Error]`) and the fallback functions
- combat mode flags -> `query_decision` (`is_in_combat`) and the matching block in `main`
- loops/oscillation -> `main` (loop breakers), `update_zone_records`, `get_zone_exit_target`
- leveling choices -> `query_decision` Phase A step 1, then `build_templates.py`

## Other files

| File | Contents |
|---|---|
| `build_templates.py` | 9 archetype templates, `detect_build`, stat/mutation recommendations, skill selection (imports from `skill_database.py`) |
| `skill_database.py` | `SKILL_DATABASE` (static copy of costs/requirements) and skill-learnability logic |
| `chronicler.py` | Death processing, aphorism generation, `format_ancestral_memory_for_prompt` |
| `dry_run.py` | Snapshot tests (`Test N` sections) [not reviewed] |
| `twitch_bot.py` | IRC voting manager [not reviewed] |
| `item_evaluator.py` | Item scoring [not reviewed] |
| `sync_mod.py` | Deploys the mod into Qud's mod folder [not reviewed] |
| `ENGINE_INTERNALS.md` | Verified engine facts (stale in places, see HANDOFF issue 22) |
| `tools/check_docs.py` | Compares the patch list, command list, test count, and paths in the docs against the code; run before every commit |
| `tools/git_report.py` | Read-only git health report (branch, ahead/behind, unmerged branches, untracked game data, repo health) with suggested next steps |
