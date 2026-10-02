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
   - [Iteration 15: 5-Tile Shoreline Loop Detection, Centroid Steering & Sustenance Refinement](#iteration-15-5-tile-shoreline-loop-detection-centroid-steering--sustenance-refinement)
   - [Iteration 16: Safe Swimming Dynamics, Liquid Hazard Classification & Water Traversal](#iteration-16-safe-swimming-dynamics-liquid-hazard-classification--water-traversal)
   - [Iteration 17: Macro-Frontier Water Traversal & River Exploration Decoupling](#iteration-17-macro-frontier-water-traversal--river-exploration-decoupling)
   - [Iteration 18: Native Autoexplore Exit Decoupling & Active Water Interception](#iteration-18-native-autoexplore-exit-decoupling--active-water-interception)
   - [Iteration 19: Unexplored Sector Telemetry & Elimination of Micro-Tile Touching](#iteration-19-unexplored-sector-telemetry--elimination-of-micro-tile-touching)
   - [Iteration 20: Mutation Cap Safeguards, Fog-of-War Grid Frontier Breakout & Shoreline Water Crossing](#iteration-20-mutation-cap-safeguards-fog-of-war-grid-frontier-breakout--shoreline-water-crossing)
   - [Iteration 21: Forensic Elimination of the 2-Tile Post-Levelup Stall Cycle & Combat Radius Physics](#iteration-21-forensic-elimination-of-the-2-tile-post-levelup-stall-cycle--combat-radius-physics)
   - [Iteration 22: Skill System Architecture, Telemetry Export & Class Archetype SP Allocation](#iteration-22-skill-system-architecture-telemetry-export--class-archetype-sp-allocation)
   - [Iteration 23: N-Cycle Zone Hopping Breaker & Death Chronicler Hook](#iteration-23-n-cycle-zone-hopping-breaker--death-chronicler-hook)
   - [Iteration 24: Engine Native Pathfinding Integration (`AutoAct.TryFindEdgeStep`) & The Three Strikes Rule](#iteration-24-engine-native-pathfinding-integration-autoacttryfindedgestep--the-three-strikes-rule)
   - [Iteration 25: Line-of-Sight Ray Occlusion, Narrow Hallway Autoexplore Fallback & Stat Point Deduction](#iteration-25-line-of-sight-ray-occlusion-narrow-hallway-autoexplore-fallback--stat-point-deduction)
   - [Iteration 26: Subterranean Stratum Zone Exit & Reachable Edge Prioritization](#iteration-26-subterranean-stratum-zone-exit--reachable-edge-prioritization)
   - [Iteration 27: Subterranean Dead-End Exit Invalidation, Wall-Bump Prevention & Corridor Alignment](#iteration-27-subterranean-dead-end-exit-invalidation-wall-bump-prevention--corridor-alignment)
   - [Iteration 28: Autonomous Enclosed Pocket Burrowing & Vegetative Wall Destruction (`ATTACK_WALL`)](#iteration-28-autonomous-enclosed-pocket-burrowing--vegetative-wall-destruction-attack_wall)
4. [Current Codebase Specification (v1.3.2)](#4-current-codebase-specification-v132)
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

### Iteration 17: Macro-Frontier Water Traversal & River Exploration Decoupling
- **The Problem:**
  - In a live game session in the Salt Marshes, the player was confronted with a wide river cutting across the center of the zone ($y = 9$).
  - Even with swimming moves enabled in `get_valid_moves()`, the agent paced back and forth across the southern shore, never crossing the water to explore the northern bank.
  - Decompilation of telemetry (`last_state.json`) revealed the root causes:
    1. Vanilla Caves of Qud's native pathfinder (`FasterDMapAutoexplore.FindAutoexploreStep`) does not path through deep water. Once all reachable dry land on the southern shore was visited, it returned `null`, marking `isZoneFullyExplored = true` in `AIBrainPart.cs`.
    2. In `brain.py`, the fallback was a purely local 1-tile frontier search that sorted valid moves by `(visit_count, 1 if is_swimming else 0)`. Because swimming moves were penalized $(N, 1)$ vs dry-land moves $(N, 0)$, the player chose visited dry land over unvisited water, pacing the 80-tile southern shore indefinitely.
    3. The agent lacked a macro-level frontier targeting mechanism across water obstacles.
- **Solution:**
  - **Macro-Frontier Detector (`find_zone_unexplored_frontier`):**
    - Scans `visible_entities` in telemetry for unvisited entities and cluster centers across the water obstacle ($\ge 3$ tiles away).
    - When detected (e.g. 195 unvisited northern entities at $y \le 8$ while player was at $y = 18$), sets a macro-frontier target.
  - **Cross-River Step Execution:**
    - When a macro-frontier target is identified across water, `get_best_move_towards(cur_pos, frontier_target, valid_moves, surroundings)` prioritizes geometric convergence towards the unvisited territory over swim penalties, commanding direct entry into the water (`MOVE_NE` / `MOVE_N`).
  - **State Reset on Water Entry:**
    - In `AIBrainPart.cs`, cleared `autoexplorePosHistory` upon executing manual moves (`MOVE_...`), ensuring cross-river steps do not trip the multi-tile oscillation detector.
    - Added automatic reset `isZoneFullyExplored = false` whenever `FindAutoexploreStep` finds a valid step, ensuring that once the character touches the far shore, native autoexploration immediately resumes to explore the new landmass.
  - **Hierarchical Phase A Exploration Ordering:**
    1. Native `AUTOEXPLORE` (when zone is unexplored and not stuck).
    2. Macro-frontier navigation (`find_zone_unexplored_frontier`) across water/obstacles.
    3. Local unvisited frontier tiles (`unvisited_local`, `visit_count == 0`).
    4. Zone exit border transition (when standing directly on exit tile).
    5. Global zone exit navigation (`get_zone_exit_target`) once the entire zone is verified fully explored.
    6. Least-visited fallback.
  - **Verification:** Verified with live `last_state.json` producing immediate `MOVE_NE` water crossing; verified all 26 tests in `dry_run.py` pass without regression.

### Iteration 18: Native Autoexplore Exit Decoupling & Active Water Interception
- **The Problem:**
  - In a live game session, after clearing the southern landmass, the character walked along the coastline and exited the map to the West rather than swimming across the river. In the next zone (`JoppaWorld.9.21.1.1.10`), the player killed a crocodile, waded shallow puddles, but again paced the shoreline of a giant 360-tile salt lake instead of swimming across to 60 unvisited brinestalks/entities on the western shore.
  - Root Cause Analysis:
    1. **Native Autoexplore Zone Exiting:** `AIBrainPart.cs` called `AutoAct.FindAutoexploreStep(true, ...)`. The boolean argument `bCanExploreZoneExits = true` instructed native autoexplore to path to adjacent zone exits when reachable dry land ran out, completely bypassing `brain.py`'s water traversal logic!
    2. **Coastline Pacing Window:** Pacing a 6-12 tile coastline created $> 5$ unique positions, preventing the 5-tile entropy loop detector from tripping quickly.
    3. **Unchecked Native Delegation:** In `brain.py`, Step 7 unconditionally called `AUTOEXPLORE` as long as `zone_fully_explored` was false, even when the only remaining unvisited territory lay across deep water. Native autoexplore refused to enter deep water, causing it to endlessly walk back and forth along the dry shore.
- **Solution:**
  - **Decoupled Zone Exits:** Changed `AutoAct.FindAutoexploreStep(false, out step, out blackout)` in `AIBrainPart.cs`. Native autoexplore now returns null when dry land is exhausted, properly setting `isZoneFullyExplored = true` rather than fleeing the zone.
  - **Extended Coastline Pacing Detector:** Updated `isCycling` in `AIBrainPart.cs` to detect back-and-forth oscillation along extended shorelines:
    `(autoexplorePosHistory.Count >= 16 && uniquePositions <= autoexplorePosHistory.Count / 2)`.
  - **Active Water Interception in Driver:** In `brain.py`, `can_use_native_autoexplore` is dynamically computed:
    If the step toward the frontier requires swimming (`is_swim_move(best_frontier_m)`) and no unvisited dry-land tiles are adjacent, native autoexplore is bypassed and the driver commands the water crossing step directly (`MOVE_NW`, `MOVE_W`, etc.).
  - **Loop Breaker Frontier Escape:** When an oscillation loop trips along a shoreline, the loop breaker checks `find_zone_unexplored_frontier` first, escaping the cycle directly across the water toward the frontier.
  - **Verification:** Verified with live `last_state.json` producing immediate `MOVE_NW` water crossing into the lake; all 26 tests in `dry_run.py` pass.

### Iteration 19: Unexplored Sector Telemetry & Elimination of Micro-Tile Touching
- **The Problem:**
  - In a live game session, movement became erratic and took over 800 turns to leave a single zone. The player appeared obsessed with stepping on every individual tile, and anti-oscillation was constantly being triggered.
  - Root Cause Analysis:
    1. **Entity-Level Micro-Targeting:** The driver attempted to find unexplored frontiers by iterating over `visible_entities` and checking `visit_counts[(tx, ty)] == 0`.
    2. Because `visible_entities` contains every single object visible on screen (every watervine, brinestalk, puddle of salt, rock, and tree), and `visit_counts` only tracks coordinates the player's avatar has physically stepped on, 95% of entities had 0 visits.
    3. Once native autoexplore finished the zone, the driver took over and attempted to path to and physically step on all 160–400 visible objects on the map.
    4. When an entity was on an impassable tile (a wall, rock, or tree), the player bumped against it repeatedly, constantly tripping anti-oscillation.
    5. Step 10 and 11 (zone exit navigation) were completely starved, trapping the character in the zone for 800+ turns.
- **Solution:**
  - **In-Engine Fog-of-War Grid Telemetry:** In `AIBrainPart.cs`, added a high-performance $80 \times 25$ grid scan in `ExportTurnState` (~0.02ms) using `Cell.Explored`. Exports `unexplored_cells` (count of unrevealed cells) and `(unexplored_centroid_x, unexplored_centroid_y)`.
  - **Macro-Sector Water Traversal vs. Instant Exit:**
    - If `unexplored_cells >= 35`: A massive unvisited landmass exists across water (e.g. northern river bank, lake islands). The driver navigates directly to the unexplored sector centroid across the water.
    - If `unexplored_cells < 35`: The zone is fully revealed. The driver **immediately navigates to the forward zone exit border** (`get_zone_exit_target`) and transitions out of the zone in ~10 turns.
  - **Removed Micro-Targeting of Visible Entities:** In real game telemetry, the driver never uses `visible_entities` to force the player to step on harmless objects.
  - **Verification:** Verified with live `last_state.json`: with `unexplored_cells = 0`, the driver immediately chooses `MOVE_E` towards the zone exit border; with `unexplored_cells = 400`, it swims across the water towards the unexplored centroid. All 26 tests in `dry_run.py` pass.

### Iteration 20: Mutation Cap Safeguards, Fog-of-War Grid Frontier Breakout & Shoreline Water Crossing
- **The Problem:**
  - The character traversed multiple maps successfully, but in zone `JoppaWorld.9.20.0.1.10` at position `(42, 17)`, the character hit another oscillation loop.
  - Two interconnected bugs caused this loop:
    1. **Mutation Cap Freeze:** The character leveled up to Level 2 and gained 1 MP. In Caves of Qud, mutation level cannot exceed character level (mutation cap = 2). All current mutations (Clairvoyance, Light Manipulation, Stunning Force, Teleport Other) were already at level 2. However, `AIBrainPart.cs` exported `can_level: true` using Qud's `m.CanLevel()`, which only tests if the mutation is a levelable class (ignoring the cap). In `brain.py`, the driver saw `mp > 0` and issued `AUTOLEVEL_MUTATION:LightManipulation`. In C#, `AllocateMutation` checked `Level < GetMutationCap()` and rejected it, spending no MP and passing the turn. This created an infinite loop of passing turns and re-issuing autolevel commands.
    2. **Loop Breaker Disconnect from Fog-of-War Telemetry:** When native autoexplore hit the shoreline at `(42, 17)` (facing a large salt pool to the East towards 217 unexplored cells at centroid `(44, 16)`), native autoexplore ping-ponged between `(41, 17)` and `(42, 17)`. When the loop breaker tripped in `brain.py`, it called legacy `find_zone_unexplored_frontier`, which ignored `unexplored_centroid` and targeted a visible puddle at `(42, 15)`. Then `open_escapes` chose dry-land moves away from the water, continually bouncing the agent back onto the shoreline.
- **Solution:**
  - **In-Engine Mutation Cap Check:** In `AIBrainPart.cs`, updated line 780:
    `bool canLvl = m.CanLevel() && (mLevel < mCap);`
    Ensures `can_level` is only exported as `true` when a mutation is strictly below its cap.
  - **Driver MP Spendability Guard:** In `brain.py`, updated autoleveling:
    `can_spend_mp = (mp >= 4) or (mp > 0 and any(m.get("can_level") and m.get("level") < m.get("cap") for m in muts))`
    Only enters autolevel if mutations can actually be leveled or if 4+ MP is available to buy a new mutation. If all mutations are capped, MP is safely preserved until future level-ups.
  - **Grid-Centroid Loop Breakout:** Upgraded `find_zone_unexplored_frontier` and the oscillation loop breaker in `brain.py` to prioritize `(unexplored_centroid_x, unexplored_centroid_y)` when `unexplored_cells >= 35`.
  - **Escape Towards Sector Target:** In `is_oscillating`, `frontier_escape` towards the unexplored sector is always prioritized over dry-land `open_escapes`.
  - **Verification (Test 27):** Added Test 27 to `dry_run.py`, verifying mutation cap suppression, grid-centroid frontier detection, and direct breakout move `MOVE_NE` into water towards `(44, 16)`. All 27 verification tests pass.

### Iteration 21: Forensic Elimination of the 2-Tile Post-Levelup Stall Cycle & Combat Radius Physics
- **The Problem:**
  - In a live game run in `JoppaWorld.8.20.1.0.10`, the character engaged a scorpiock, killed it, and leveled to Level 3 (`hp: 27/27, ap: 1, sp: 106, mp: 2`).
  - Immediately post-levelup, the character froze, pacing back and forth on two tiles (`(44, 11)` $\leftrightarrow$ `(44, 10)`). The character refused to allocate points and refused to explore.
  - **Root Cause Analysis:**
    1. **The Phantom Combat Lock (`dist <= 20`):** In `brain.py`, `close_threats` looked up to 20 tiles away. Another scorpiock existed in the zone at $(62, 19)$, 18 tiles away across open dunes. Even though `player.AreHostilesNearby()` returned `false`, `is_in_combat` was set to `True`.
    2. **Autolevel Starvation:** Autoleveling was strictly gated behind `if not is_in_combat:`. Because `is_in_combat` was stuck `True`, Phase A autoleveling was never reached. The unspent points (`ap: 1, sp: 106, mp: 2`) sat permanently frozen.
    3. **Out-of-Range Combat Spam:** The LLM and fallback logic were invoked in combat mode against the enemy at distance 18. Abilities like `CommandStunningForce` (range 8) and `CommandLase` (range 10) were fired at distance 18, failing in engine. When abilities went on cooldown, the LLM spammed `WAIT`, and the fallback matrix sorted moves by visit counts (`Maneuver`), bouncing between `(44, 11)` and `(44, 10)`.
    4. **The 4-MP Mutation Cap Loop:** When `mp >= 4`, buying a new mutation in Qud requires an interactive popup modal (`"Are you sure you want to spend 4 mutation points..."`), which is unsupported headlessly. `AllocateMutation` only levels existing mutations. When mutations were capped, `mp >= 4` triggered infinite `AUTOLEVEL` calls.
- **Solution:**
  - **Bounded Combat Engagement Radius:** Redefined `close_threats` in `brain.py`:
    `close_threats = [e for e in enemies if not is_ignorable_stationary_enemy(e) and (e.get("dist", 999) <= 6 or (e.get("dist", 999) <= 10 and game_state.get("hostiles_nearby", False)))]`
    Distant enemies ($> 10$ tiles, or $> 6$ tiles when engine reports `hostiles_nearby == False`) never trigger combat mode.
  - **Priority Attribute Allocation:** If `ap > 0` and the player has no adjacent melee threats (`not adj_threats`) and took no damage (`not took_damage`), AP is allocated immediately (`AUTOLEVEL_STAT:<Stat>`) even if combat is pending.
  - **Mutation Spendability Guard:** Updated `can_spend_mp = mp > 0 and can_level_any_mut`. MP is strictly held when all mutations are capped until level-up raises the cap.
  - **Ability Range Gating in LLM Choices & Fallbacks:** Bounded `Stunning Force` (range 8), `Lase` (range 10), `Sunder Mind` (range 12), and `Syphon Vim` (range 4).
  - **Fallback Pursuit Navigation:** When an enemy is beyond ability range, all fallbacks (`fallback_melee`, `fallback_esper`, `fallback_gunslinger`, `fallback_nomad`) actively advance toward the target via `get_best_move_towards(cur_pos, target_pos, valid_moves, surroundings)` rather than pacing on neighbor tiles.
  - **Verification (Test 28):** Added Test 28 to `dry_run.py`, verifying disengagement at dist 18, 4-step autoleveling cascade (`AUTOLEVEL_STAT:Ego` $\to$ `AUTOLEVEL_SKILL:Tactics` $\to$ `AUTOLEVEL_SKILL:Tactics_Hurdle` $\to$ `AUTOEXPLORE`), priority combat AP spending at dist 7, and fallback target pursuit. All 28 verification tests pass.

### Iteration 22: Skill System Architecture, Telemetry Export & Class Archetype SP Allocation
- **The Problem:**
  - In a live game session with an Apostle character who reached Level 3 with 106 unspent SP, the character never spent any Skill Points.
  - Telemetry examination of `last_state.json` revealed:
    `"calling": "Apostle", "skills": [], "sp": 106, "learnable_skills": [...]`
    1. **Empty Telemetry Export (`skills: []`):** `AIBrainPart.cs` exported learned skills by iterating `player.GetPart<Skills>().SkillList`. In Caves of Qud, starting skills and powers granted by callings (e.g. `Tactics`, `Persuasion`, `Proselytize`, `Axe`, `Pistol`) are attached directly as part components on the player `GameObject`, leaving `SkillList` empty.
    2. **The SP Hoarding Trap in `is_skill_learnable`:** When Python evaluated `esper_ited_away` progression, it checked `Tactics` (rejected because not in `learnable_skills` since player already owned it), then `Tactics_Hurdle` (rejected because parent `Tactics` was believed unlearned), and then `Tactics_Juke` (cost 200 SP). In `is_skill_learnable`, `sp < cost` was evaluated **before** attribute requirements (`Agi >= 21`). Because 106 < 200, it returned `"Insufficient SP"`, which triggered `is_saving = True`! The AI hoarded points indefinitely for a skill requiring Agility 21 that an Apostle (Agility 16) could not even learn!
    3. **Suboptimal Archetype Progression:** `esper_ited_away` placed `Tactics_Juke` (200 SP, Agi 21) ahead of crucial survival and sustain skills (`CookingAndGathering`, `Butchery`, `MealPreparation`, and `Discipline`).
    4. **The Circuit Breaker 0-SP Trap:** `AllocateSkill` in `AIBrainPart.cs` previously had `if (sp <= 0) return false;`, blocking 0-cost subpowers from being claimed at 0 SP. Furthermore, the autolevel circuit breaker in `brain.py` tracked `cur_points = (ap, sp, mp)`. Learning a 0-cost skill didn't reduce SP, so `cur_points == last_autolevel_points` falsely incremented `autolevel_failed_attempts` and suppressed autoleveling.
- **Solution:**
  - **In-Engine SkillFactory Telemetry Export:** Unified `AIBrainPart.cs` to iterate `SkillFactory.GetSkills()`, checking `player.HasSkill(s.Class)` and `player.HasSkill(p.Class)`. Now exports both `Class` and `Name` into `state.json["skills"]` accurately on every turn.
  - **Strict Requirement Order in `is_skill_learnable`:** Parents, prerequisites, and attribute thresholds (`min_stat`) are now strictly evaluated **before** `sp < cost`. Skills whose stat requirements are unmet are never flagged as `Insufficient SP`, preventing spurious SP hoarding freezes.
  - **Archetype Survival Prioritization:** All 9 archetypes in `build_templates.py` prioritize `CookingAndGathering` (100 SP), `CookingAndGathering_Butchery` (50 SP, Int 15), and `CookingAndGathering_MealPreparation` (0 SP) right after starting weapon proficiencies, followed by class core attributes.
  - **Zero-Cost Power Engine & Breaker Fix:**
    - Allowed 0-SP powers in `AllocateSkill` (`if (sp < 0) return false;`).
    - Updated `cur_points = (ap, sp, mp, len(skills))` in `brain.py`. Learning a 0-SP skill changes the tuple signature, resetting failed attempts to 0.
  - **Multi-Class Regression Verification (Test 29):** Added Test 29 to `dry_run.py`, testing starting skills ingestion and SP spending across Apostle (`CookingAndGathering`), free 0-SP `MealPreparation`, Marauder free `Axe_Expertise`, Gunslinger `Pistol_SteadyHands`, and 0-SP breaker preservation. All 29 verification tests pass cleanly.

### Iteration 23: N-Cycle Zone Hopping Breaker & Death Chronicler Hook
- **The Problem:**
  - The AI character was caught in a 3-zone oscillation loop ($A \to B \to C \to A$), but the old zone-hopping breaker only detected 2-cycle ping-pongs ($A \leftrightarrow B$).
  - When the player died to a scorpiock in the salt desert, the Chronicler never fired because the death hook was inside the player turn handler, which is never called after death in Caves of Qud.
- **Solution:**
  - **N-Cycle Oscillation Detection:** Upgraded `update_zone_records()` in `brain.py` to detect 2-, 3-, and 4-zone cycle patterns.
  - **Novel Exit Direction Routing:** Implemented `_compute_adjacent_zone_id()` to calculate world-grid topology and pick exit directions leading strictly to unvisited/novel zones.
  - **Harmony Hook on `GameObject.Die`:** Added `AIDiePatch` on `XRL.World.GameObject.Die` in `AIBrainPart.cs` to capture player deaths instantly with the killer's name, reason, and coordinates.
  - **Gen 1 Chronicling & Ancestral Memory:** Verified the Chronicler, generating `Chronicle_Gen1_Apostle_of_the_Salt_1790838662.md` and adding the first ancestral rule to `ancestral_wisdom.json`.

### Iteration 24: Engine Native Pathfinding Integration (`AutoAct.TryFindEdgeStep`) & The Three Strikes Rule
- **The Problem:**
  - The new character got trapped in the starting Joppa hut, and upon leaving the room, stalled in the hallway.
  - Movement was "losing cohesion" because local heuristics were fighting each other:
    1. A greedy 1-step Euclidean vector pointed straight at the East border `(78, y)`, walking directly into walls and furniture.
    2. Furniture (cushions, chairs, tables, beds) was not marked `[BLOCKED]` because it lacked `Physics.Solid == true`.
    3. In Joppa, all cells start revealed (`unexplored_cells == 0`), causing native `AUTOEXPLORE` to return empty and pass the turn indefinitely.
    4. The loop breaker shoved the character away from the wall, only for the exit vector to shove it right back into the wall next turn.
- **Solution:**
  - **Native Engine Pathfinding via `AutoAct.TryFindEdgeStep`:** In `AIBrainPart.cs`, when a `MOVE` command cannot advance into an adjacent cell, the engine automatically delegates to `AutoAct.TryFindEdgeStep(edgeChar, out string pathStep)`. Qud's built-in A* pathfinder charts the exact route around walls, corridors, and doorways toward that zone border.
  - **Furniture Obstacle Classification:** Flagged `Chair`, `Bed`, `Table`, `Floor Cushion`, and `Bedroll` as `[BLOCKED]` in both C# telemetry and Python `get_valid_moves`.
  - **Actual Coordinate Change Tracking:** Verified that `(pxBefore, pyBefore) != (pxAfter, pyAfter)` in `ExecuteCommand`; if a move does not change coordinates, it is flagged as failed.
  - **Autoexplore Zero-Cell Gate:** In `brain.py`, `can_use_native_autoexplore` now strictly requires `unexp_cells > 0`, immediately transitioning to zone exit navigation in pre-revealed towns like Joppa.
### Iteration 25: Native Engine Zone Exit Pathfinding (`NAVIGATE_ZONE_EXIT`) & Obstacle Loop Resolution
- **The Problem:**
  - In `outskirts, Joppa` (`JoppaWorld.11.22.1.0.10`), the Apostle character became trapped ping-ponging along a brinestalk fence in the graveyard between `(47, 10)` and `(47, 11)`.
  - The East exit target was `(78, 11)`. The fence blocked East, NE, and SE.
  - The 1-step Euclidean vector in `get_best_move_towards` evaluated open adjacent moves `MOVE_N` and `MOVE_S`. At `(47, 11)` it picked `MOVE_N` to `(47, 10)`, and at `(47, 10)` it picked `MOVE_S` back to `(47, 11)`. Both tiles were open dirt, so `player.Move()` succeeded every turn, meaning the engine saw valid moves while the character ping-ponged indefinitely along the fence.
  - Because `unexplored_cells == 0` in pre-revealed Joppa outskirts, `AutoAct.FindAutoexploreStep` had no targets, and the Python loop breaker repeatedly fell back to `get_best_move_towards(cur_pos, exit_target)`, producing the exact same 2 oscillating moves.
- **Solution (Executing The Three Strikes Rule):**
  - **Decompiled `XRL.World.Capabilities.AutoAct` in `Assembly-CSharp.dll`:** Identified the native Caves of Qud edge-pathfinding API `AutoAct.TryFindEdgeStep(char Direction, out string Step)`.
  - **Implemented `NAVIGATE_ZONE_EXIT:<DIR>` in `AIBrainPart.cs`:**
    - Directly calls `AutoAct.TryFindEdgeStep(edgeChar, out step)` to run Qud's full-map A* pathfinder through gates, doors, and around obstacles toward the requested border.
    - If the target border is completely unreachable, automatically falls back through other cardinal edges (`'E', 'N', 'S', 'W'`).
    - Added automated door opening (`TryOpenDoorInDirection`) and energy consumption safeguards.
  - **Updated `brain.py` Step 11 & Loop Breaker:**
    - Step 11 now dispatches `NAVIGATE_ZONE_EXIT:{exit_dir}` instead of computing 1-step straight lines.
    - The oscillation breaker now immediately triggers `NAVIGATE_ZONE_EXIT:{exit_dir}` whenever oscillation occurs in a fully explored or zero-unexplored-cell zone (`unexplored_cells == 0`).
    - Updated `get_zone_exit_target` to return `(target_coord, exit_tag, exit_dir)`.
  - **Test Suite Expansion (Test 30):** Added Test 30 to `dry_run.py` to verify graveyard fence breakout telemetry and cardinal edge targeting. All 30 verification tests pass cleanly.

### Iteration 26: Zone Bailing Prevention & Native Target Cell Pathfinding (`NAVIGATE_TO_CELL`)
- **The Problem:**
  - After navigating past Joppa outskirts, the Apostle character beelined East across 4 consecutive zones (`11.22.1` -> `11.22.2` -> `12.22.0` -> `12.22.1` -> `12.22.2`) without stopping to explore any of them.
  - In zone `12.22.2.0.10`, the character hit an oscillation loop next to some watervine at `(43, 14)` with 1439 unexplored cells remaining.
- **Root Cause Analysis (Applying The Three Strikes Rule):**
  - **Decompiled `AutoAct.FindAutoexploreStep` & `FasterDMapAutoexplore.FindAutoexploreStep` in `Assembly-CSharp.dll`:** Discovered that whenever the player enters a new zone or stands on a border tile, the engine's internal DMap distance map has not yet been seeded for that zone, so `FindAutoexploreStep` returns `"."` or `null` on turn 1.
  - In `AIBrainPart.cs` (lines ~2220-2226), `ExecuteAutoexplore` unconditionally executed `isZoneFullyExplored = true;` whenever `FindAutoexploreStep` paused on a single turn!
  - In `brain.py`, Step 11 saw `zone_fully_explored: True` and immediately commanded `NAVIGATE_ZONE_EXIT:E`, marching straight out of the zone before exploring anything.
  - At `(43, 14)`, the frontier target was `(44, 12)` across watervine plants. The Python loop breaker used 1-step Euclidean vectors (`get_best_move_towards`) which ping-ponged between `(43, 14)` and `(44, 14)` because direct diagonals were blocked by plants.
- **Solution:**
  - **Ground-Truth Zone Explored Guard:**
    - In `AIBrainPart.cs`, removed the premature `isZoneFullyExplored = true;`. Counted actual unrevealed cells in `parentZone`; `isZoneFullyExplored` can only be set to `true` if `unexpCount <= 0`.
    - In `brain.py`, added a strict guard: `if unexp_cells is not None and unexp_cells > 0: zone_fully_explored = False`. A zone with hundreds of unrevealed cells can never be treated as explored.
    - Gated Step 11 (Zone Exit Navigation) strictly behind `unexplored_cells == 0`.
  - **Implemented `NAVIGATE_TO_CELL:X,Y` Command:**
    - Decompiled and integrated `AutoAct.TryFindPathStep(Cell Target, out string Step)` into `AIBrainPart.cs`. Runs Qud's native A* pathfinder directly to any coordinate in the zone, routing smoothly around watervine, trees, and obstacles.
    - Updated `brain.py` loop breaker to dispatch `NAVIGATE_TO_CELL:{tx},{ty}` to pathfind cleanly around watervine instead of 1-step Euclidean vector ping-pongs.
  - **Test Suite Expansion (Test 31):** Added Test 31 to `dry_run.py` verifying that a zone with 1439 unrevealed cells commands `AUTOEXPLORE` even if `zone_fully_explored: True` was erroneously asserted. All 31 verification tests pass cleanly.

### Iteration 27: Centroid Distance-1 Gravitational Bounce Elimination & Nearest Unexplored Telemetry
- **The Problem:**
  - In zone `JoppaWorld.12.22.2.0.10` while swimming in salty water, the character entered an oscillation loop between two tiles: `(62, 10)` and `(62, 11)`.
  - The loop breaker repeatedly tripped, but immediately routed the player back into the same 2-tile ping-pong cycle.
- **Root Cause Analysis (Applying The Three Strikes Rule):**
  - **The Distance-1 Mathematical Deadzone:**
    - The unexplored centroid of the remaining 551 cells was at `(62, 12)`.
    - In `brain.py` (both in `find_zone_unexplored_frontier` line 245 and `query_decision` line 1984), the target selection required:
      `max(abs(cx - px), abs(cy - py)) > 1`
    - When the player was at `(62, 10)`, distance to `(62, 12)` was `2 > 1` (True). The AI correctly moved South to `(62, 11)`.
    - Once at `(62, 11)`, distance to `(62, 12)` was `1 > 1` (False!).
    - Because `1 > 1` failed, the AI abandoned `(62, 12)`. In Step 9, it found an unvisited tile at `(61, 10)` (NW) and moved `MOVE_NW` back to `(62, 10)`.
    - At `(62, 10)`, distance was 2 again, so it moved South.
    - Result: A perpetual 2-tile gravitational bounce at distance 1 from the target centroid.
  - **Loop Breaker Infection:** The Loop Breaker also called `find_zone_unexplored_frontier`, which hit the same `> 1` failure at `(62, 11)`, fell through to distant `visible_entities`, and routed to `(60, 11)` (NW), reinforcing the oscillation instead of breaking it.
- **Solution:**
  - **Pinpoint `nearest_unexplored` Engine Telemetry:**
    - In `AIBrainPart.cs`, during the zone fog-of-war scan, added tracking for `nearest_unexplored_x`, `nearest_unexplored_y`, and `nearest_unexplored_dist`.
    - Unlike the centroid (which is an arithmetic average that can be explored or inside a wall), `nearest_unexplored` is an *actual unrevealed fog-of-war cell* (`c.Explored == false`). The player is never standing on it, eliminating dead-zones.
  - **Distance-1 Target Resolution:**
    - Replaced `max(abs(cx - px), abs(cy - py)) > 1` with `(cx != px or cy != py)`. If the target is 1 tile away, the AI directly steps onto it.
    - If the player is standing directly on the centroid `(cx == px and cy == py)`, targeting falls through seamlessly to `(nearest_unexplored_x, nearest_unexplored_y)`.
  - **Geometric Direction Fallback in `NAVIGATE_TO_CELL`:**
    - In `AIBrainPart.cs`, if `AutoAct.TryFindPathStep` returns null or `.` (e.g. across water), it falls back to `player.CurrentCell.GetDirectionFromCell(targetCell)` to take the direct physical step.
  - **Test Suite Expansion (Test 32):** Added Test 32 to `dry_run.py` verifying distance-1 centroid movement (`MOVE_S` from `(62, 11)` to `(62, 12)`) and standing-on-centroid nearest unexplored targeting. All 32 verification tests pass cleanly.

### Iteration 28: Organic Random Exploration & Per-Zone Exit Caching
- **The Problem:**
  - Characters were locked into an artificial, rigid Eastward trans-continental march because `get_zone_exit_target` hardcoded `# Default: East` when starting in Joppa. Once entered from the West, forward momentum locked East indefinitely.
  - Runs felt on-rails rather than organic and emergent for viewers and ancestral learning.
- **Solution:**
  - **Organic Exit Selection:**
    - Filter out immediate backtracking (`d != rev_dir`).
    - Query world topology (`_compute_adjacent_zone_id`) to find novel/unexplored adjacent zones (`novel_candidates`).
    - Randomly select among novel exits (`random.choice(novel_candidates)`) to dynamically explore new biomes in any cardinal direction (North, East, South, West).
    - If all adjacent zones have been visited, randomly choose among non-reverse candidate borders.
  - **Per-Zone Exit Decision Caching:**
    - Cached `CURRENT_ZONE_CHOSEN_EXIT` per zone so that once an organic exit is chosen for a cleared zone, the agent navigates steadily toward that border without turn-by-turn direction jitter. Resets cleanly upon transitioning into the next zone (`update_zone_records`).
  - **Test Suite Verification:** Updated Test 30 in `dry_run.py` to verify organic cardinal exits; all 32 verification tests pass cleanly.

### Iteration 29: Companion Memory Clearance & Opportunistic Pet Recruitment
- **The Problem:**
  - `CHARMED_COMPANION_NAMES` in `brain.py` acted as a sticky latch: once any pet was registered, the set was never cleared.
  - `has_companion` evaluated permanently to `True`, so `fallback_esper` never attempted to cast `CommandProselytize`.
  - `is_proselytizable` permanently barred any creature of that species from ever being recruited again, and wild hostiles of that species were treated as companions.
  - Zero recruitment logic existed in Phase A exploration.
- **Solution:**
  - Synchronized companion memory every turn with live telemetry (`has_active_companion`); cleared `CHARMED_COMPANION_NAMES` and `CHARMED_COMPANION_COORDS` when petless and on player death.
  - Added Phase A opportunistic recruitment at distance 1 and distance 2 approach.
  - Added distance-2 recruitment approach in `fallback_esper`.
  - Added Test 33 to `dry_run.py` (33/33 pass).

### Iteration 30: Combat Loop Breaker Immunity & Living Creature Corpse Part Rejection Fix
- **The Problem:**
  - During battle with a giant dragonfly, the character hit a 2-tile loop and refused to cast ready charges of Lase or Stunning Force.
  - `last_action_executed.txt` revealed `NAVIGATE_TO_CELL:55,13` was being dispatched every single turn in combat!
  - **Root Cause 1 (Navigation Loop Breaker Hijacking Combat):**
    - In `main()` (`brain.py`), `elif is_oscillating:` checked `pos_frequency >= 3` or cycle length, but had NO check for `is_in_combat` or `is_combat_action`.
    - Exploration visit history accumulated in `recent_positions` triggered `is_oscillating = True` on turn 1 of combat.
    - The loop breaker intercepted the LLM / fallback decision (`USE_ABILITY:CommandStunningForce:N` or `CommandLase`) and overwrote it with `NAVIGATE_TO_CELL:55,13` (routing to an unexplored frontier tile 15 tiles away while adjacent to the enemy!).
  - **Root Cause 2 (`CanBeProselytized` Rejection of Living Creatures):**
    - In `AIBrainPart.cs`, `CanBeProselytized` checked `if (obj.HasPart("Corpse")) return false;`.
    - In Caves of Qud, virtually all living biological creatures (dragonflies, snapjaws, crocs, baboons) possess a `<part Name="Corpse" ... />` component defining their corpse drop blueprint upon death.
    - As a result, living dragonflies were flagged with `can_proselytize: false`, causing Proselytize targeting to evaluate `targetObj = none` and Python to reject subsequent recruitment attempts.
- **Solution:**
  - **Combat Loop Breaker Immunity (`brain.py`):**
    - Defined `is_combat_action = action.startswith("USE_ABILITY") or action.startswith("FIRE_MISSILE") or is_attacking`.
    - Defined `is_oscillating = not is_in_combat and not is_combat_action and (...)`.
    - Added `elif is_oscillating and not is_in_combat:`.
    - Tactical abilities (`USE_ABILITY`), missile fire (`FIRE_MISSILE`), and melee counter-attacks are strictly protected and will never be hijacked by exploration frontier pathfinding.
  - **Living Creature Corpse Part Rejection Fix (`AIBrainPart.cs`):**
    - Removed `obj.HasPart("Corpse")` from `CanBeProselytized`.
    - Dead corpses are already completely excluded by `!obj.IsAlive`. Living biological creatures with corpse drop definitions are now correctly identified as valid recruitment candidates.
  - **Test Suite Expansion (Test 34):**
    - Added Test 34 in `dry_run.py` verifying combat loop breaker immunity (tactical abilities preserved despite high position frequency) and dragonfly proselytization.
    - All 34 tests pass cleanly. Mod deployed via `sync_mod.py`.

### Iteration 25: Line-of-Sight Ray Occlusion, Narrow Hallway Autoexplore Fallback & Stat Point Deduction
- **Observed Failure Modes:**
  1. *Lase through Wall*: Character engaged a mob across a corridor and fired Lase directly into a solid wall because line of sight was not evaluated along the projectile ray, wasting laser charges.
  2. *Single-Tile Hallway Stall*: In subterranean stratum 11, after banishing an enemy with Teleport Other, the native autoexplore pathfinder (`AutoAct.FindAutoexploreStep` / `FasterDMapAutoexplore`) returned null in the narrow corridor. The engine pass-turn was executed without setting `isZoneFullyExplored`, triggering an infinite 1-tile lock of repeated `AUTOEXPLORE` calls.
  3. *AP/SP Telemetry Desync*: In `AllocateStat` and `AllocateSkill`, adjusting `Penalty` didn't immediately decrement `BaseValue`, occasionally causing the Python brain to re-request allocations before the engine cleared the pending pool.
- **Solution:**
  - **In-Engine Line-of-Sight Filtering (`AIBrainPart.cs`):**
    - Exported `has_los: player.HasLOSTo(obj)` for all visible entities in `state.json`.
    - Enforced `player.HasLOSTo(target)` and `player.HasLOSTo(targetCell)` in `FIRE_MISSILE`, `USE_ABILITY` (for physical rays, lase, spit, breath, and missile abilities), and `AIPickTargetPatch`.
    - Preserved mental mutation bypass (`Sunder Mind`) through solid rock as designed by Qud mechanics.
  - **Subterranean Narrow Corridor Autoexplore Fallback (`AIBrainPart.cs`):**
    - When native autoexplore returns null/no step, the engine automatically attempts `AutoAct.TryFindPathStep(nearestUnexplored, out step)`.
    - If no reachable unexplored cell exists anywhere in the subterranean zone, immediately sets `isZoneFullyExplored = true` so the agent smoothly transitions to staircase delving or exit navigation rather than freezing on a single tile.
  - **Attribute & Skill Point Direct BaseValue Decrement (`AIBrainPart.cs`):**
    - Decrements `apStat.BaseValue -= 1` and `spStat.BaseValue -= cost` alongside `Penalty` updates to guarantee immediate telemetry synchronization.
  - **Python Ray Occlusion & Corridor Maneuvering (`brain.py`):**
    - Updated `is_line_of_fire_clear` with `target_entity` (verifying `has_los is not False`) and `surroundings` (checking for `[BLOCKED:` wall tiles intersecting the Bresenham line).
    - Updated `fallback_esper`: Direct rays (`Lase`, `Stunning Force`, `Cryokinesis`, missiles) require `c_lof_clear and c_has_los`. If occluded, the agent maneuvers around corridor corners towards the target rather than blindly waiting.
  - **Test Suite Expansion (Test 35):**
    - Added Test 35 in `dry_run.py` verifying line-of-sight ray occlusion, wall blocking in surroundings, corridor maneuvering, and Sunder Mind wall penetration.
    - All 35 tests pass cleanly. Mod deployed via `sync_mod.py`.

### Iteration 26: Subterranean Stratum Zone Exit & Reachable Edge Prioritization
- **Observed Failure Modes:**
  1. *Subterranean Infinite Autoexplore Loop*: In subterranean strata (`z > 10`), hundreds of cells (e.g. 605) are solid rock walls. Even when the C# engine confirmed all reachable corridor tiles were visited and exported `zone_fully_explored: True`, Python had a surface-oriented override `if unexp_cells > 0: zone_fully_explored = False`. This forced repeated `AUTOEXPLORE` calls, which passed the turn and froze the agent.
  2. *Rock Wall Navigational Oscillation*: When loop breaker triggered, it unconditionally prioritized `NAVIGATE_TO_CELL:{centroid}` into unreachable solid rock behind walls, while the exit escape branch was unreachable dead code.
  3. *Zone Exit Blindness in Corridors*: Subterranean zones often only have one reachable zone exit (e.g. North). Randomly picking an exit border (e.g. East or South) without verifying corridor connectivity could cause navigation to path into solid rock dead ends.
- **Solution:**
  - **In-Engine Reachable Edges Telemetry (`AIBrainPart.cs`):**
    - When `isZoneFullyExplored` is true or in dungeons (`z > 10`), evaluates `AutoAct.TryFindEdgeStep` across all 4 cardinal directions and exports `"reachable_edges": "N"` in `state.json`.
    - In `NAVIGATE_ZONE_EXIT`, updates `edgeChar` to the fallback direction that succeeded and logs the route.
  - **Stratum Completion & Exit Selection (`brain.py`):**
    - Preserved `zone_fully_explored = True` in subterranean strata (`cur_z > 10`), preventing solid rock occlusion from overriding completed exploration.
    - Updated Step 8 (macro sector navigation) to only trigger when `not zone_fully_explored`.
    - Removed arbitrary `unexp_cells == 0` constraint on Step 11 (`NAVIGATE_ZONE_EXIT`), allowing the agent to exit completed dungeon strata immediately.
    - In `get_zone_exit_target`, prioritizes verified `reachable_edges` from telemetry, instantly choosing the open corridor exit (North) without dead-end guessing.
    - In Loop Breaker, prioritized `NAVIGATE_ZONE_EXIT` whenever the zone is fully explored or autoexplore is stuck.
  - **Test Suite Expansion (Test 36):**
    - Added Test 36 in `dry_run.py` verifying subterranean stratum zone completion with 605 rock cells, `reachable_edges` prioritization, and loop breaker exit navigation.
    - All 36 tests pass cleanly. Mod deployed via `sync_mod.py`.

### Iteration 27: Subterranean Dead-End Exit Invalidation, Wall-Bump Prevention & Corridor Alignment
- **Observed Failure Modes:**
  1. *Subterranean Dead-End East Exit Trap*: In stratum 11 (`JoppaWorld.10.23.0.1.11`), the character explored the zone and decided to exit. `get_zone_exit_target` selected `"E"` (East) and cached `CURRENT_ZONE_CHOSEN_EXIT = "E"`. However, the eastern corridor dead-ended into solid rock at `(74, 11)`. The only viable exit was the second North corridor (`nearest_unexplored_y: 9 < py: 11`).
  2. *Unbreakable Exit Cache*: Once `CURRENT_ZONE_CHOSEN_EXIT = "E"` was set, there was no mechanism to invalidate or blacklist it upon failure. Even the loop breaker called `get_zone_exit_target`, which returned the cached `"E"`, locking the character into repeatedly bumping into the dead-end wall.
  3. *Engine Blind Wall-Bumping*: In C# `NAVIGATE_ZONE_EXIT`, when `AutoAct.TryFindEdgeStep` failed to find a step, the engine fell back to blind `MOVE_E`, repeatedly walking into the rock wall and passing turn.
- **Solution:**
  - **In-Engine Border Cell Fallback & Wall-Bump Suppression (`AIBrainPart.cs`):**
    - Added border-cell pathfinding fallback: iterates over open, non-occluding border cells on the target edge and uses `AutoAct.TryFindPathStep(bc, out step)` if direct edge stepping fails.
    - Suppressed blind wall bumping: verifies the adjacent cell in the target direction is not occluding/wall before falling back to `MOVE_<dir>`; otherwise logs movement failure (`lastMoveFailed = true`, `lastFailedDir = edgeChar.ToString()`) and passes turn.
  - **Exit Failure Detection & Dynamic Blacklisting (`brain.py`):**
    - Implemented `FAILED_ZONE_EXITS = set()` tracking `(zone_id, exit_dir)`.
    - Implemented `check_exit_direction_failure(game_state, cur_pos, chosen_exit)`: checks both engine telemetry failure (`last_move_failed`) and dead-end stone walls facing the border (e.g. `px >= 70` with East, NE, SE blocked).
    - In `get_zone_exit_target`: pre-emptively filters candidate directions to exclude known dead ends and blacklists them.
    - In subterranean strata (`cur_z > 10`), inspects `nearest_unexplored_y` and `nearest_unexplored_x` to prioritize open corridor directions (`"N"` when `ny < py`).
    - In Loop Breaker: if oscillation occurs while an exit is chosen, immediately blacklists `CURRENT_ZONE_CHOSEN_EXIT` and selects an alternative exit.
  - **Test Suite Expansion (Test 37):**
    - Added Test 37 in `dry_run.py` verifying dead-end East exit invalidation at `(74, 11)` into solid rock, corridor-based North exit prioritization, and loop breaker exit blacklisting.
    - All 37 tests pass cleanly. Mod deployed via `sync_mod.py` and committed to Git.

### Iteration 28: Autonomous Enclosed Pocket Burrowing & Vegetative Wall Destruction (`ATTACK_WALL`)
- **Observed Failure Modes:**
  1. *Procedural Enclosed Cavern Trap*: In subterranean stratum 11 (`JoppaWorld.9.23.2.1.11`), the character arrived inside a completely enclosed 3x3 pocket at `(70, 6)` surrounded by `plant matter` (`PlantWall`) and `tangled mudroot`.
  2. *Autoexplore & Macro Navigation Lock*: Native `AUTOEXPLORE` immediately passed turn because no open tiles connected to the rest of the zone. Macro-sector navigation attempted `MOVE_W`, but with `(68, 6)` blocked by mudroot and `(69, 5)` occupied by a neutral Sprouting Orb, the character bounced indefinitely between `(70, 6)` and `(69, 6)`.
  3. *Unaware of Wall Destructibility*: In *Caves of Qud*, vegetative obstacles (`PlantWall`, `Mudroot`, webs, fences) have low HP and AV, and can be destroyed by attacking them. However, neither `brain.py` nor `AIBrainPart.cs` had a mechanism to force-attack or burrow through walls to escape enclosed rooms.
- **Solution:**
  - **In-Engine Melee Strike Dispatch (`AIBrainPart.cs`):**
    - Added `ATTACK_WALL:<dir>` (and `FORCE_ATTACK:<dir>`, `ATTACK_CELL:<dir>`) action handling.
    - Inspects adjacent cell in target direction, retrieves the blocking wall/plant `GameObject` via `o.HasPart("Wall") || o.HasPart("Plant") || o.HasPart("Combat") || o.HasPart("Physics")`, and directly invokes `player.PerformMeleeAttack(targetWall)`.
  - **Autonomous Burrowing & Destructible Terrain Prioritization (`brain.py`):**
    - Implemented `DESTRUCTIBLE_OBSTACLE_KEYWORDS` covering vegetative and breakable barriers (`plant matter`, `plantwall`, `mudroot`, `tangled mudroot`, `fence`, `wood`, `web`, `bramble`).
    - Implemented `find_burrow_direction(surroundings, cur_pos, target_pos)`: detects adjacent destructible obstacles, prioritizes soft vegetative matter over solid rock, and chooses the direction that advances closest toward the unexplored sector centroid (`(36, 12)`).
    - In `query_decision` (Step 8): if `visit_counts[cur_pos] >= 2` and all open moves lead to visited tiles, automatically issues `ATTACK_WALL:<dir>` to breach the pocket.
    - In `get_valid_moves`: excluded `[npc:` when `not is_in_combat`, preventing the AI from falsely assuming neutral NPCs are open walkable corridors.
    - In `Loop Breaker`: if trapped in a small cycle (`unique_positions <= 6`) with unrevealed cells remaining, prioritizes burrowing through adjacent obstacles before falling back to zone exit.
  - **Test Suite Expansion (Test 38):**
    - Added Test 38 in `dry_run.py` verifying autonomous burrowing in the 3x3 pocket at `(70, 6)` toward sector `(36, 12)`, `find_burrow_direction` soft-material prioritization, and loop breaker pocket burrowing.
    - All 38 tests pass cleanly. Mod deployed via `sync_mod.py` and committed to Git.

---

## 4. Current Codebase Specification (v1.3.2)

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
   - **Step 4B: Pet Recruitment**: If petless and possesses Proselytize or Beguile, opportunistically recruits adjacent beasts/humanoids or approaches candidates at distance 2.
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
