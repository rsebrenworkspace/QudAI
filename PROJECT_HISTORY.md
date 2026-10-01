# Caves of Qud Autonomous Agent (QudAI)
## Project History, System Architecture & Future Roadmap

**Document Version:** 1.2.0  
**Current Date:** September 2026  
**Primary Language Stack:** Python 3.10+, C# (.NET Framework 4.8 / Unity / Harmony), Local LLM (OpenAI-compatible / LM Studio)

---

## Table of Contents
1. [Executive Summary & Vision](#1-executive-summary--vision)
2. [Hierarchical System Architecture](#2-hierarchical-system-architecture)
3. [Chronological Iteration History](#3-chronological-iteration-history)
   - [Iteration 0: The Architectural Blueprint](#iteration-0-the-architectural-blueprint)
   - [Iteration 1: Screen Scraping & Input Simulation Pitfalls](#iteration-1-screen-scraping--input-simulation-pitfalls)
   - [Iteration 2: Harmony Engine Hooks & Headless JSON IPC](#iteration-2-harmony-engine-hooks--headless-json-ipc)
   - [Iteration 3: Ranged Engine Interrogation & Ammo Loader Fixes](#iteration-3-ranged-engine-interrogation--ammo-loader-fixes)
   - [Iteration 4: Ancestral Memory & Death Chronicler](#iteration-4-ancestral-memory--death-chronicler)
   - [Iteration 5: Decompiling Leveling & Headless Point Allocation](#iteration-5-decompiling-leveling--headless-point-allocation)
   - [Iteration 6: Interactive Twitch Chat Voting Integration](#iteration-6-interactive-twitch-chat-voting-integration)
   - [Iteration 7: Multi-Class Archetypes & Tactical Fallback Matrix](#iteration-7-multi-class-archetypes--tactical-fallback-matrix)
   - [Iteration 8: Pet Recruitment & Companion Absolute Immunity](#iteration-8-pet-recruitment--companion-absolute-immunity)
   - [Iteration 9: Conversational NPC & Settlement Townsfolk Immunity](#iteration-9-conversational-npc--settlement-townsfolk-immunity)
   - [Iteration 10: Multi-Tile Oscillation Loop Breaker & Door Navigation](#iteration-10-multi-tile-oscillation-loop-breaker--door-navigation)
   - [Iteration 11: Shoreline Two-Tile Oscillation, Autolevel Casing & Circuit Breaker](#iteration-11-shoreline-two-tile-oscillation-autolevel-casing--circuit-breaker)
   - [Iteration 12: Staircase Navigation, Stratum Delving & Tactical Retreat](#iteration-12-staircase-navigation-stratum-delving--tactical-retreat)
   - [Iteration 13: Class Skill Trees, Prerequisite Gating & SP Savings Doctrine](#iteration-13-class-skill-trees-prerequisite-gating--sp-savings-doctrine)
   - [Iteration 14: Zone Hopping Prevention & Sustenance / Survival Routines](#iteration-14-zone-hopping-prevention--sustenance--survival-routines)
4. [Current Codebase Specification (v1.2.0)](#4-current-codebase-specification-v120)
   - [Directory Structure](#directory-structure)
   - [Telemetry & IPC Protocol](#telemetry--ipc-protocol)
   - [Decision Pipeline (Phases A, B, C)](#decision-pipeline-phases-a-b-c)
5. [Future Roadmap & Milestones](#5-future-roadmap--milestones)
   - [Milestone 8: Autonomous Inventory & Barter Engine](#milestone-8-autonomous-inventory--barter-engine)
   - [Milestone 9: World Map Exploration & Quest Pathfinding](#milestone-9-world-map-exploration--quest-pathfinding)
   - [Milestone 10: Companion & Temporal Fugue Clone Coordination](#milestone-10-companion--temporal-fugue-clone-coordination)
   - [Milestone 11: Real-Time Stream Overlay (OBS Web Widget)](#milestone-11-real-time-stream-overlay-obs-web-widget)
6. [Onboarding Guide for Future AI Instances](#6-onboarding-guide-for-future-ai-instances)

---

## 1. Executive Summary & Vision

*Caves of Qud* is one of the most complex, emergent, and unforgiving permadeath roguelikes ever developed. With thousands of interacting physics entities, fluid dynamics, limb dismemberment, psychic glimmer, mutation trees, and intricate faction diplomacy, standard reinforcement learning or raw heuristic scripts struggle to make meaningful progress.

**QudAI** is an autonomous, streaming-ready artificial intelligence agent that plays *Caves of Qud* live without human intervention. It leverages a **Hierarchical Decision Engine**:
- **Phase A (Zero-Latency Deterministic Safe Mode)**: Instant response for out-of-combat exploration, survival/sustenance, resting, ammo top-offs, staircase delving, and safe autoleveling.
- **Phase B (Conversational LLM Reasoning)**: High-level tactical reasoning powered by local vision/reasoning models (LM Studio, e.g. Qwen 2.5 / Qwen 3 VL / Llama 3) that analyze spatial grids, status effects, and character doctrines.
- **Phase C (Class-Specific Deterministic Fallback)**: A zero-latency tactical safety net that ensures survival even when the local LLM is slow, offline, or returns invalid outputs.

---

## 2. Hierarchical System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CAVES OF QUD (Unity Engine Runtime)                  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                QudAIBrain.AIBrainPart (Harmony Mod)              │  │
│  │  - Patches XRL.Core.PlayerTurn.Prefix                            │  │
│  │  - Suppresses all blocking UI dialogs & popups                   │  │
│  │  - Intercepts PickDirection, PickTarget, PickItem                │  │
│  │  - Telemetry: HP, grid, radar, hunger, food, stairs, skills, pet │  │
│  │  - Headless actions: move, missiles, powers, camping, eating, lvl │  │
│  └───────────────────▲──────────────────────────────┬───────────────┘  │
└──────────────────────┼──────────────────────────────┼──────────────────┘
                       │ JSON IPC (action.json)       │ JSON IPC (state.json,
                       │                              │           death.json)
┌──────────────────────┴──────────────────────────────▼──────────────────┐
│                          QudAI PYTHON DRIVER                           │
│                               (brain.py)                               │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │            Archetype Detection (build_templates.py)              │  │
│  │  (Rifle Nomad, Axe Berserker, Akimbo Gunslinger, Esper, Tank)    │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│         ┌───────────────────────────┼──────────────────────────┐       │
│         ▼                           ▼                          ▼       │
│  ┌──────────────┐          ┌────────────────┐         ┌──────────────┐ │
│  │   PHASE A    │          │    PHASE B     │         │   PHASE C    │ │
│  │ Safe Rest,   │          │ Tactical LLM   │         │ Deterministic│ │
│  │ Delve, Camp, │◄──Combat?│ (LM Studio API)│◄─Fail/──│ Multi-Class  │ │
│  │ Eat & Level  │    No    │ Injects Lore,  │  Timeout│ Fallback     │ │
│  │              │          │ Doctrine, Grid │         │ Safety Net   │ │
│  └──────────────┘          └────────────────┘         └──────────────┘ │
│         ▲                                                              │
│         │ (Stat/Skill Votes)                                           │
│  ┌──────┴───────────────────────────────────────────────────────────┐  │
│  │                   TWITCH BOT (twitch_bot.py)                     │  │
│  │  - Thread-safe IRC listener for live viewer voting                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                CHRONICLER (chronicler.py)                        │  │
│  │  - Post-mortem death event parser & aphorism generator           │  │
│  │  - Injects Ancestral Wisdom into future character prompts         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Chronological Iteration History

### Iteration 0: The Architectural Blueprint
- **Problem:** Full autonomy in *Caves of Qud* cannot be solved with pure LLM prompting due to token latency (2–4 seconds per turn in exploration is painfully slow), nor with pure heuristics (tactics in permadeath combat require deep contextual reasoning).
- **Solution:** Conceived the **Hybrid Hierarchical Architecture**: split turns into deterministic safe-mode operations (0ms cost) and tactical combat operations (LLM reasoning with deterministic safety nets).

### Iteration 1: Screen Scraping & Input Simulation Pitfalls
- **Attempted Approach:** Direct OS window capture with OpenCV/pytesseract and Win32 keypress simulation (`pyautogui` / `SendInput`).
- **Failures Identified:**
  1. OCR latency was >600ms per frame and failed to accurately distinguish tile glyphs under atmospheric lighting or liquid pools.
  2. Modal popups (level-up screens, trade confirmations, death prompts) permanently stole input focus and hung the driver.
  3. Keypress dropping led to characters walking into walls or failing to execute critical reloads.

### Iteration 2: Harmony Engine Hooks & Headless JSON IPC
- **Implementation:** Created the C# Harmony mod `QudAIBrain` targeting `Assembly-CSharp.dll`.
- **Breakthrough:**
  - Patched `XRL.Core.PlayerTurn.Prefix`.
  - Suppressed all engine modal popups (`Popup.bSuppressPopups = true`, `Popup.Suppress = true`).
  - Switched `GameManager.runPlayerTurnOnUIThread = false` to prevent engine deadlocks.
  - Implemented headless turn execution via `player.UseEnergy(1000)` and file-based JSON IPC (`state.json` and `action.json`).

### Iteration 3: Ranged Engine Interrogation & Ammo Loader Fixes
- **The Bug:** Characters equipped with rifles would fire once, enter a 90-degree fan spray sweep, and empty magazines into harmless dirt or companions.
- **Decompilation Discovery:** Mono.Cecil and runtime reflection revealed `XRL.World.Parts.Combat.FireMissileWeapon` had 10 parameters, including `sweepwidth` which defaulted to `90`!
- **Fix:** Hooked directly into `FireMissileWeapon`, overridden `sweepwidth = 0` and `rapid = 0` for pinpoint single-shot accuracy, and created headless `MagazineAmmoLoader` auto-reload routines.

### Iteration 4: Ancestral Memory & Death Chronicler
- **Concept:** When a character dies in permadeath, their lessons must survive into future generations.
- **Implementation:**
  - `AIBrainPart.cs` exports `death.json` upon player death with killer blueprint, cause of death, last 40 actions, and damage logs.
  - `chronicler.py` passes the tombstone to LM Studio to extract a max-20-word tactical aphorism.
  - Aphorisms are stored in `memory/ancestral_wisdom.json` and prepended to future characters' LLM system prompts ("Ancestral Wisdom from Fallen Predecessors").

### Iteration 5: Decompiling Leveling & Headless Point Allocation
- **The Challenge:** Leveling up in Qud produces modal UI menus (`LevelUp` / `SpendAP` / `Skills`). Suppressing popups prevented human interaction, but the character never spent AP/SP/MP.
- **Decompilation Findings:** Inspected Qud's internal leveling mechanics:
  - **AP (Attribute Points):** `targetStat.BaseValue += 1; player.GetStat("AP").Penalty += 1;`
  - **MP (Mutation Points):** `mutations.LevelMutation(mut, mut.BaseLevel + 1); player.UseMP(1, "default");`
  - **SP (Skill Points):** `skills.AddSkill(skillClass); player.GetStat("SP").Penalty += cost;`
- **Implementation:** Added `ExecuteAutolevel`, `AllocateStat`, `AllocateMutation`, and `AllocateSkill` to `AIBrainPart.cs`. Supported direct command dispatches: `AUTOLEVEL_STAT:<stat>`, `AUTOLEVEL_SKILL:<skill>`, and `AUTOLEVEL`.

### Iteration 6: Interactive Twitch Chat Voting Integration
- **Concept:** Allow live stream viewers to control character progression via Twitch chat voting.
- **Implementation:**
  - Built `twitch_bot.py`: a thread-safe, native Python IRC socket listener.
  - Commands: `!vote <stat>`, `!vote <skill>`, `!votes`, `!status`.
  - In `brain.py` Phase A, when unspent points are available, the agent queries the Twitch manager for vote winners before defaulting to archetype templates.

### Iteration 7: Multi-Class Archetypes & Tactical Fallback Matrix
- **The Problem:** The combat engine originally assumed all characters were rifle snipers. Marauders armed with battle axes would run away when snapjaws approached, while Espers would bump-attack albino apes.
- **Solution:**
  - Built `build_templates.py` containing 5 core archetypes: `rifle_nomad`, `axe_berserker`, `akimbo_gunslinger`, `esper_mindflayer`, `praetorian_tank`.
  - Added `player.GetGenotype()` and `player.GetSubtype()` export in `AIBrainPart.cs` for exact calling matching.
  - Patched `XRL.UI.PickDirection`, `XRL.UI.PickTarget`, and `XRL.UI.PickFieldTarget` so directional abilities (`Charge`, `Dismember`, `Freezing Ray`, `Cryokinesis`) execute headlessly without UI stalls.
  - Replaced the single rifle fallback in `brain.py` with 4 dedicated fallback routines (`fallback_melee`, `fallback_esper`, `fallback_gunslinger`, `fallback_nomad`).

### Iteration 8: Pet Recruitment & Companion Absolute Immunity
- **Problem**: When the Apostle / Esper Mindflayer charmed wild creatures (e.g. giant dragonflies, goats, seahorses) using `CommandProselytize`:
  1. The C# mod only checked `brain.PartyLeader == player`, which failed because charmed creatures in Caves of Qud receive effects (`Proselytized`, `Beguiled`, `Rebuked`) and AI parts (`AllyProselytize`). Furthermore, `zone.GetObjects()` was throwing `InvalidOperationException: Collection was modified` during turn processing, silently wiping `companions` to `[]`.
  2. Because `companions: []`, the charmed creature was exported as `is_enemy: true` and appeared in `surroundings` as `[ENEMY: giant dragonfly]`.
  3. The Python Esper fallback policy saw an adjacent threat and backpedaled to escape melee range. The charmed pet followed its master, repeating turn after turn.
  4. Once distance reached 2-3 tiles or cooldowns reset, the AI fired `CommandStunningForce` or `CommandLase` directly at its own pet, killing it.
- **Solution**:
  1. **Comprehensive C# `IsCompanion` Hook**: Added `IsCompanion(GameObject obj, GameObject player)` checking active effects (`Proselytized`, `Beguiled`, `Rebuked`, `Lovesick`), parts (`AllyProselytize`, `AllyBeguile`), and leader relationships (`IsLedBy(player)`, `PartyLeader == player`).
  2. **Safe Zone Traversal (`GetSafeZoneObjects`)**: Replaced all throwing `ParentZone.GetObjects()` enumerations with safe cell-by-cell `zone.GetCell(x, y)?.Objects` traversal.
  3. **Zero-Latency In-Memory Companion Whitelist (`brain.py`)**: Added global sets `CHARMED_COMPANION_NAMES` and `CHARMED_COMPANION_COORDS`. As soon as `USE_ABILITY:CommandProselytize:<DIR>` is dispatched, the target tile's entity is registered with 0 latency, instantly immunizing it across `filter_hostile_enemies`, `get_adjacent_threats`, `is_line_of_fire_clear`, and tactical fallbacks.
  4. **Offensive Target Interception Guardrails**: Updated `AIPickGameObjectPatch`, `AIPickTargetPatch`, and `AIPickFieldTargetPatch` to never auto-select or target friendly companions.
  5. **Bresenham Raytraced LOF**: Added ray-tracing to verify no friendly companions are in the line of projectile or beam fire.

### Iteration 9: Conversational NPC & Settlement Townsfolk Immunity
- **Problem**: When exploring Joppa or other settlements, peaceful NPCs, quest givers, and merchants were occasionally flagged by generic hostile filters or bumped into during autoexplore.
- **Solution**:
  - Implemented `is_peaceful_npc(name, blueprint)` checking peaceful keywords (`farmer`, `warden`, `elder`, `convert`, `zealot`, `merchant`, `trader`, `dromad`, `pariah`, `villager`, `citizen`, `settler`, `irudad`, `yrame`, `mehmet`, `argyve`, `tam`, `priest`).
  - Added hostile overrides to ensure aggressive factions (`snapjaw`, `raider`, `cannibal`, `goatfolk`, `putus`) are always engaged.
  - Immunized peaceful NPCs across combat detection, radar, and line-of-fire targeting.

### Iteration 10: Multi-Tile Oscillation Loop Breaker & Door Navigation
- **The Problem:** The character occasionally entered tight ping-pong loops inside buildings (e.g. oscillating between a sign and a table or doorway).
- **Solution:**
  - Implemented spatial memory tracking (`recent_positions` deque and `pos_frequency`).
  - When the agent detects it has visited a coordinate 3+ times in the last 10 turns, the oscillation breaker engages:
    - If stuck in `AUTOEXPLORE`, marks the zone's autoexplore as exhausted in `stuck_autoexplore_zones`.
    - Gathers valid open escapes that avoid recently visited coordinates.
    - Selects the least-visited frontier tile (`visit_counts`) to break out of the room or obstacle enclosure.

### Iteration 11: Shoreline Two-Tile Oscillation, Autolevel Casing & Circuit Breaker
- **The Problem:**
  - Characters moving along bodies of water or marshlands could get trapped oscillating between two shore tiles when a companion was blocking one path and deep water blocked the others.
  - A runtime compilation error occurred in `AIBrainPart.cs` where `GameObject.SetProperty` was called (which does not exist on `GameObject` in modern Caves of Qud).
  - When autolevel failed to allocate points (e.g. prerequisites unmet), the character could enter an infinite loop trying to spend points every turn.
- **Solution:**
  - **Companion Pathing & Swapping:** In `get_valid_moves()`, added companion awareness: companions occupying adjacent tiles are deferred to `companion_moves`, allowing tactical repositioning into open tiles first, but allowing companion tile swapping if completely trapped.
  - **C# Engine Property Fix:** Replaced invalid `SetProperty` calls in `AIBrainPart.cs` with proper Caves of Qud API methods (`stat.BaseValue += 1`, `stat.Penalty += 1`, `skills.AddSkill()`).
  - **Autolevel Circuit Breaker:** In `main()`, tracked `autolevel_failed_attempts`. If the same unspent points fail to allocate across 2 consecutive attempts, `suppress_autolevel=True` is engaged, safely falling through to exploration.

### Iteration 12: Staircase Navigation, Stratum Delving & Tactical Retreat
- **The Problem:** The character had no deliberate concept of vertical dungeon delving, did not seek stairs, entered stairs at Level 1 before being strong enough, and could not tactically retreat when overwhelmed underground.
- **Solution:**
  - **Staircase Telemetry & Ingestion:** Exported `stairs_down`, `stairs_up`, `standing_on_stairs_down`, and `standing_on_stairs_up` in `AIBrainPart.cs`. Added `update_stair_records()` in `brain.py` to maintain persistent spatial memory of stairs across zones (`KNOWN_STAIRS_DOWN`, `KNOWN_STAIRS_UP`).
  - **Depth-Gated Delving (`min_level_for_depth`):**
    - Surface ($z \le 10$): Level 1
    - Stratum 1 ($z = 11$): Level 3
    - Stratum 2+ ($z \ge 12$): Level $3 + (z - 11) \times 2$
  - **Surface Level-Up & Re-Delving:** If standing on stairs down below the required level, delves are held until sufficient levels are attained. When a zone is cleared, the agent navigates directly to known stairs down to delve.
  - **Tactical Retreat Protocol:** When overwhelmed underground ($z > 10$) with critical HP ($< 35\%$), heavy damage, or Impossible hostiles:
    - Flees towards known stairs up.
    - Ascends stairs (`USE_STAIRS_UP`) back to safety.
    - Sets `RETREAT_TARGET_LEVEL = cur_level + 1`.
    - Explores the surface or higher strata to heal and level up, then returns to re-delve once recovered.

### Iteration 13: Class Skill Trees, Prerequisite Gating & SP Savings Doctrine
- **The Problem:** Autoleveling spent Attribute Points and Mutation Points, but failed to intelligently spend Skill Points (SP) according to class doctrine, occasionally stalling or spending points on suboptimal filler.
- **Solution:**
  - **Skill Hierarchy & Prerequisites:** Decompiled Qud's `SkillFactory` and `SkillEntry` architecture. Built `build_templates.get_best_skill_to_learn()` to inspect `learnable_skills` from engine telemetry and class priority trees.
  - **Parent Skill Gating:** Ensures parent skills (e.g. `Axe`, `Shield`, `Tactics`) are unlocked before attempting to purchase subskills (e.g. `Dismember`, `Shield_Slam`).
  - **Free 0-Cost Subskills:** Immediately claims 0-cost baseline powers (e.g. `Axe_Expertise`, `Shield_Block`) upon parent acquisition.
  - **SP Savings Doctrine:** If a character needs 150 SP for their next priority milestone (e.g. `Customs`), the agent deliberately saves its 75 SP rather than wasting it on filler skills.

### Iteration 14: Zone Hopping Prevention & Sustenance / Survival Routines
- **The Problem:**
  - When transitioning between adjacent zones, characters landing on border edges ($x=0$ or $x=79$) would immediately detect the reverse zone exit and step back, causing a rapid ping-pong oscillation loop ("zone hoping event").
  - Characters were starving and becoming famished with no automated butchering, cooking, camping, or eating.
- **Solution:**
  - **Zone Hopping Breaker & Inward Steering:**
    - Added `update_zone_records()` tracking `RECENT_ZONES` and `LAST_ZONE_ENTRY`.
    - Detects 2-cycle $A \leftrightarrow B$ oscillation (`ZONE_HOPPING_DETECTED`).
    - Enforces inward steering towards zone interior $(40, 12)$ whenever the character is on a boundary tile within the first 4 turns or during oscillation.
    - Suppresses immediate reverse exit backtracking (`rev_exit`).
  - **Survival & Sustenance System:**
    - Decompiled `Stomach`, `Campfire`, `Food`, `Butcherable`, `Harvestable`, and `Survival_Camp` in `Assembly-CSharp.dll`.
    - Exported comprehensive engine telemetry: `hunger_level`, `is_hungry`, `is_famished`, `has_food`, `food_count`, `campfire_nearby`, `corpses_nearby`, `harvestable_nearby`, `can_make_camp`, `can_cook`, `can_butcher`, `can_harvest`.
    - Implemented C# action handlers: `EAT`, `MAKE_CAMP`, `COOK_MEAL`, `BUTCHER`, `HARVEST`.
    - Integrated Sustenance as Step 2 of Phase A in `brain.py` (strictly before resting at Step 3, because resting while famished causes starvation damage/death).
### Iteration 15: 5-Tile Shoreline Loop Detection, Centroid Steering & Sustenance Refinement
- **The Problem:**
  - The character became Hungry, hit a large body of water, and entered an infinite cycle oscillating between 5 shoreline tiles on repeat.
  - Decompiler and mathematical analysis revealed that in an $N=5$ tile cycle, any sliding window of length 10 contains at most $\lfloor 10 / 5 \rfloor = 2$ visits per tile. Therefore, a threshold of `count >= 3` was mathematically unreachable, blinding both C# and Python loop detection.
  - In C#, `pStomach?.ClearHunger()` failed to compile (`CS1061`) because `GameObject` does not have `pStomach` in modern Qud, and `BaseMutation.DisplayName` was obsolete (`CS0618`).
  - Packaged rations like jerky, dried fruit, and wafers have `PreparedCookingIngredient` rather than `Food`, causing food detection to miss preserved ingredients.
- **Solution:**
  - **Fixed C# Compilation:** Replaced `player.pStomach?.ClearHunger()` with `player.GetPart<Stomach>()?.ClearHunger()`. Replaced `m.DisplayName` with `m.GetDisplayName()`.
  - **Expanded Sustenance Telemetry:** Added `item.HasPart<PreparedCookingIngredient>()` check to recognize preserved jerky, dried fruit, and rations as food. Added `ActivatedAbilities` check for `CommandSurvivalCamp`.
  - **Early Cooking in All 9 Archetypes:** Positioned `CookingAndGathering` and `CookingAndGathering_Butchery` early (right after core starter weapon masteries or after `Discipline` for Apostle) so characters can butcher meat and camp early in their runs.
  - **Dual-Layer Oscillation Detection:**
    - Expanded sliding window from 10 to 24 steps in both C# and Python.
    - Added spatial entropy check: `(window_len >= 10 and unique_positions <= 5)`. This trips in exactly 10 steps on any 5-tile cycle regardless of frequency or visit sequence.
    - In C# `AIBrainPart.cs`, when `isCycling` trips, it sets `isZoneFullyExplored = true` and yields, avoiding local lockup.
  - **Centroid Steer Breakout Fallback:**
    - When all local moves lie within recently visited tiles along a curved shoreline, calculates the geometric centroid of recent positions $(\bar{x}, \bar{y})$ and maximizes Euclidean distance away from it, steering outward onto open dry land.
  - **Headless Cooking & Camping (Zero-UI Prompts):**
    - Identified that `Campfire.Cook()` explicitly invokes `ShowInventoryActionMenu`, displaying the interactive modal `[m] Whip up a meal / [i] Choose ingredients / [r] Recipe / [f] Preserve`.
    - Identified that `Survival_Camp.AttemptCamp()` calls `PickDirectionS("Make Camp")` and `ShowYesNoCancel()`.
    - Refactored both actions in `AIBrainPart.cs` to execute programmatically: `Cell.AddObject("Campfire")` places the fire directly without directional prompts; `COOK_MEAL` consumes 1 ingredient from inventory (via `ingredient.Count` manipulation, resolving CS1501 with `SplitFromStack`), clears stomach hunger via `stomach.ClearHunger()`, resets cooking counter, and calls `campPart.AfterCooked()` silently without ever opening UI modals.
  - **Expanded Verification Suite (Test 25):** Added Test 25 to `dry_run.py`, verifying 5-tile entropy check, open frontier escape, centroid steer fallback, and zone exploration exhaustion. All 25 tests pass.

### Iteration 16: Safe Swimming Dynamics, Liquid Hazard Classification & Water Traversal
- **The Problem:**
  - The AI treated deep water as an impassable barrier (`[BLOCKED: deep water]`), completely preventing it from entering swimming depth liquid.
  - When rivers, subterranean lakes, or marsh ponds divided a zone or isolated objectives (stairs, quests, exits), the agent was constrained exclusively to the shoreline rim, entering oscillation loops or starving instead of swimming across.
- **Solution:**
  - **In-Engine Liquid Hazard Discrimination:**
    - Decompiled `XRL.World.Cell` in `Assembly-CSharp.dll` and verified `cell.GetDangerousOpenLiquidVolume()`, `cell.GetSwimmingDepthLiquid()`, and `cell.HasSwimmingDepthLiquid()`.
    - Refactored `AIBrainPart.cs` to classify liquid danger:
      - Lethal liquids (acid, lava, magma) are tagged as `[HAZARD: <name>]`.
      - Solid obstructions / walls are tagged as `[BLOCKED: impassable terrain]`.
      - Safe deep swimming liquids (fresh water, salty water, slime, honey) are tagged as `[SWIM: <name>]` rather than `[BLOCKED: deep water]`.
  - **Driver Traversal & Pathfinding Weights:**
    - In `brain.py`, updated `get_valid_moves()` to allow `[SWIM: ...]` moves while strictly blocking `[hazard`, `acid`, `lava`, and `magma`.
    - Updated `render_5x5_grid()` so swimming water tiles render as `'~'` rather than `'#'` (walls), accurately visualizing lakes and rivers in ASCII.
    - Updated move ranking with a dry-land preference tiebreaker: `(visit_count, 1 if is_swimming else 0)`. The agent prefers walking on dry land when available to avoid the swimming movement penalty, but freely steps into water and swims across rivers/lakes when dry land is explored or blocked.
    - Updated `get_best_move_towards()` so the agent swims across bodies of water directly toward stairs, zone transitions, or target objectives.
  - **In-Water Invariants (Zero Campfire Drowning):**
    - Exported `"is_swimming"` in state telemetry.
    - Disabled `can_make_camp`, `can_cook`, `can_butcher`, `can_harvest`, and `can_rest` while actively in deep water (`is_swimming: true`).
    - Added guards in `PerformMakeCamp` and `PerformCookMeal` in `AIBrainPart.cs` to reject camping/cooking while swimming.
    - Preserved direct inventory eating (`EAT`) so hungry characters can eat rations while swimming.
  - **Expanded Verification Suite (Test 26):**
    - Added Test 26 to `dry_run.py`, verifying liquid hazard classification (blocking acid/lava, allowing deep water), 5x5 ASCII rendering (`~` vs `!`), river navigation across water towards stairs and unexplored frontiers, and in-water camping suppression. All 26 tests pass.

---

## 4. Current Codebase Specification (v1.2.0)

### Directory Structure
```
D:\QudAI\
├── brain.py                    # Master autonomous AI driver & hierarchical decision loop
├── build_templates.py          # 9 build archetypes, combat doctrines, stat/skill priority trees
├── item_evaluator.py           # Item scoring rubric & hard overrides (light, ranged, recoilers)
├── chronicler.py               # Post-mortem death analyzer & ancestral memory generator
├── dry_run.py                  # 26-scenario multi-class verification test suite
├── twitch_bot.py               # IRC Twitch chat listener for live viewer voting
├── twitch_config.example.json  # Twitch bot configuration template
├── sync_mod.py                 # Sync utility between repo and Qud's LocalLow mod folder
├── .gitignore                  # Git ignore rules for exchange files and temp state
├── PROJECT_HISTORY.md          # Comprehensive project history & architectural specification
├── README.md                   # Repository overview, installation, and user quickstart
│
├── mod\
│   └── QudAIBrain\
│       ├── AIBrainPart.cs      # Harmony mod C# engine patches & headless action execution
│       └── workshop.json       # Mod metadata manifest for Caves of Qud
│
├── chronicles\                 # Stored historical post-mortem tombstone analyses
└── memory\
    └── ancestral_wisdom.json   # Accumulated survival lore injected into LLM prompts
```

### Telemetry & IPC Protocol
All communication occurs via files in `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI`:

| File | Direction | Format | Purpose |
|---|---|---|---|
| `state.json` | Game $\rightarrow$ Python | JSON (UTF-8) | Full turn state: HP, position, 5x5 grid, radar entities, attributes, skills, mutations, calling, ammo, hunger, food, stairs |
| `action.json` | Python $\rightarrow$ Game | JSON (UTF-8) | Dispatched action command (`MOVE_N`, `FIRE_MISSILE@x,y`, `USE_ABILITY:cmd:dir`, `EAT`, `MAKE_CAMP`, `COOK_MEAL`, `BUTCHER`, `HARVEST`, `USE_STAIRS_DOWN`, `USE_STAIRS_UP`, `AUTOLEVEL`, etc.) |
| `active.flag` | Python $\leftrightarrow$ Game | Text | Presence indicates autonomous AI is engaged; deletion pauses AI and restores manual control |
| `death.json` | Game $\rightarrow$ Python | JSON (UTF-8) | Exported upon player death containing cause, killer, killer level, recent damage, and recent actions |

### Decision Pipeline (Phases A, B, C)
1. **Phase A (Safe Mode)**: Runs when no enemies are visible within 20 tiles, no damage was taken, and no adjacent hostiles exist.
   - **Step 1: Autolevel**: Spends unspent AP/SP/MP according to class doctrine or Twitch chat vote winner.
   - **Step 2: Sustenance**: Opportunistically butchers corpses / harvests plants; cooks at campfire, pitches camp, or eats food when hungry/famished.
   - **Step 3: Rest**: Rests until HP $\ge 75\%$ (only if not famished).
   - **Step 4: Ammo Top-Off**: Reloads missile magazines from spare inventory ammo.
   - **Step 5: Stratum Delving**: Navigates to known stairs down when the zone is cleared, gated by depth level requirements.
   - **Step 6: Inward Border Steer**: Steers toward zone center $(40, 12)$ if on border tiles during the first 4 turns or during oscillation.
   - **Step 7: Autoexplore**: Autonomous exploration via native Caves of Qud autoexplore pathfinder.
   - **Step 8: Zone Exits / Frontier**: Transitions to adjacent zones via forward exits (suppressing immediate backtracks).
2. **Phase B (Tactical LLM Reasoning)**: Runs when hostiles are detected or damage is sustained.
   - Formats a 5x5 ASCII grid, active threat radar, ready abilities, and valid action choices.
   - Passes the character's exact class doctrine and ancestral wisdom to LM Studio (`http://localhost:1234/v1/chat/completions`).
   - Parses the JSON response with strict timeout safeguards (6.0s).
   - Validates directional abilities and checks raytraced line-of-fire to eliminate companion friendly fire.
3. **Phase C (Deterministic Fallback Matrix - 9 Guide Archetypes)**:
   - **Melee (`auspicious_beginnings`, `limb_off`, `axe_berserker`, `classic_punchkin`)**: Charges enemies at dist 2–4; executes Dismember / Cleave / Cudgel Slam / Flurry or bump-attacks adjacent threats; only retreats if surrounded by $\ge 3$ hostiles and HP $< 35\%$.
   - **Mental (`esper_ited_away`, `esper_mindflayer`, `uncle_iroh`, `gas_giant`)**: Recruits pet tanks with Proselytize; pops Force Bubble / Force Wall; channels Sunder Mind (pure mental, 100% safe over allies); fires Lase / rays only when raytraced LOF is clear; manifests gas clouds safely.
   - **Gunslinger (`gunkin`, `bullet_specter`, `akimbo_gunslinger`)**: Holds 3–6 tiles; fires Chain Fire and Disarming Shot; verifies LOF before bursting; tactical reloads when disengaged.
   - **Sniper (`praetorian_generalist`, `rifle_nomad`)**: Freezes pursuers with Freezing Ray; snipes with desert rifle at distance $\ge 2$ along clear LOF; sprint-kites when dry.

---

## 5. Future Roadmap & Milestones

### Milestone 8: Autonomous Inventory & Barter Engine
- **Weight Management**: Auto-scrap heavy metal objects, butcher corpses, and preserve fresh food.
- **Liquid Economics**: Understand water drams as both currency and hydration; prevent dehydration.
- **Merchant Interaction**: Recognize dromad merchants, Joppa apothecaries, and grit gate tinkers; automatically trade trade-goods for lead slugs, high-AV armor, and energy cells.
- **Cybernetics Wedge**: For True Kin characters (Praetorian), locate Becoming Nooks and install cybernetics implants.

### Milestone 9: World Map Exploration & Quest Pathfinding
- **World Map Navigation**: Traverse parasangs on the world map without starving or wandering into high-tier death zones (e.g. Moon Stair / Death Dells early).
- **Core Quest Pipeline**:
  - What's Eating the Watervine? (Red Rock quest)
  - A Canticle for Barathrum (Rustwells wire retrieval)
  - Golgotha descent (sewer diving and repair)

### Milestone 10: Companion & Temporal Fugue Clone Coordination
- **Companion Orders**: For Espers with Beguile/Proselytize, command followers to tank or hold ground.
- **Temporal Fugue Safety**: When mental clones spawn, prevent friendly-fire missile discharges and crossfire traps.
- **Clairvoyance Targeting**: Fire missiles through walls when using phasing or clairvoyance.

### Milestone 11: Real-Time Stream Overlay (OBS Web Widget)
- **Local WebSocket Server**: Stream telemetry in real-time to an HTML5/CSS canvas.
- **On-Screen Display (HUD)**:
  - Live character portrait with calling and active doctrine.
  - HP bar, ammo gauge, hunger state, and surrounding 5x5 ASCII minimap.
  - Twitch chat voting progress bar with timer countdown.
  - LLM "Thought Bubble" displaying the model's tactical rationale in real time.

---

## 6. Onboarding Guide for Future AI Instances

When resuming development in a new chat or instance, follow this checklist:

1. **Verify Files & Syntax**:
   ```powershell
   python -m py_compile D:\QudAI\brain.py
   python -m py_compile D:\QudAI\build_templates.py
   python D:\QudAI\dry_run.py
   ```
2. **Verify Mod Sync**:
   If editing `AIBrainPart.cs` inside `D:\QudAI\mod\QudAIBrain\`, deploy it to Qud:
   ```powershell
   python D:\QudAI\sync_mod.py deploy
   ```
   Always verify that opening and closing braces in `AIBrainPart.cs` match:
   ```powershell
   python -c "t = open(r'D:\QudAI\mod\QudAIBrain\AIBrainPart.cs', encoding='utf-8').read(); assert t.count('{') == t.count('}'), 'Braces unbalanced!'"
   ```
3. **Verify Local LLM**:
   Ensure LM Studio is running on `http://localhost:1234` with an active model loaded (`detect_lm_studio_model()` in `brain.py`).
4. **Autonomous Hotkey**:
   Pressing **Enter** in the console window where `brain.py` is running toggles AI on/off at any time.
