# Caves of Qud Autonomous Agent (QudAI)
## Project History, System Architecture & Future Roadmap

**Document Version:** 1.0.0  
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
4. [Current Codebase Specification (v1.0.0)](#4-current-codebase-specification-v100)
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
- **Phase A (Zero-Latency Deterministic Safe Mode)**: Instant response for out-of-combat exploration, resting, ammo top-offs, and safe leveling.
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
│  │  - Interrogates player body, inventory, stats, mutations, radar  │  │
│  │  - Headlessly executes movement, missile fire, abilities, leveling│  │
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
│  │ Explore &    │◄──Combat?│ (LM Studio API)│◄─Fail/──│ Multi-Class  │ │
│  │ Class-Based  │    No    │ Injects Lore,  │  Timeout│ Fallback     │ │
│  │ Autoleveling │          │ Doctrine, Grid │         │ Safety Net   │ │
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

### Iteration 8: Native Autoexplore Foundation (Macro-Navigation Engine)
- **The Challenge:** Peaceful exploration previously relied on a rudimentary 1-tile frontier movement heuristic (`visit_counts`). Characters could get wedged in complex corners or water edges, failed to systematically open chests or retrieve floor loot across 80x25 zones, and had no native awareness of when a zone was fully explored.
- **Decompilation Findings:** Decompiled `Assembly-CSharp.dll` with `Trivial.Mono.Cecil` and analyzed Qud's native Autoexplore architecture:
  - `XRL.World.Capabilities.FasterDMapAutoexplore.FindAutoexploreStep(out string step, out bool blackout)`
  - `XRL.World.Capabilities.AutoAct.FindAutoexploreStep(bool Force, out string step, out bool blackout)`
  - `step` returns optimal direction strings (`"N"`, `"S"`, `"E"`, `"W"`, etc.) towards unrevealed tiles, loot, and containers, or returns `"."` / `null` when the zone is completely traversed.
- **Implementation:**
  - Added `ExecuteAutoexplore` in `AIBrainPart.cs`: queries `FasterDMapAutoexplore` / `AutoAct`, executes movement, handles door opening, and auto-loots ground items.
  - Exported `zone_fully_explored` boolean in `state.json` (resets upon zone transition).
  - In `brain.py` Phase A, dispatched `AUTOEXPLORE` as the foundational macro-exploration action when safe. When `zone_fully_explored` is reported, seamlessly transitions to stairs down (`USE_STAIRS_DOWN`) or adjacent zone exits.
  - Instant Combat Suspension: Any incoming damage, nearby hostiles, or active targets immediately halt autoexplore and switch control to LM Studio / class fallback matrix in Phase B/C.

### Iteration 9: Esper Tactical Psychic Overhaul & MinEvent Event Dispatch
- **The Problem:** When playing an Esper (Apostle), the character entered an infinite orbit around stationary hostiles (glowpads) at distance 4–5, never casting offensive psychic powers (`Light Manipulation` / `Lase`, `Stunning Force`, `Sunder Mind`) and refusing to engage.
- **Root Cause Analysis:**
  1. `LightManipulation`'s active beam attack command is `CommandLase` (labeled "Lase" in game), whereas `brain.py` searched for `"light manipulation"`.
  2. Abilities like `Lase` and `Stunning Force` were not classified as directional in `brain.py`, omitting directional vectors (`:SE`).
  3. Non-combat utility powers (`Clairvoyance`, `Ambient Light`) polluted combat choices, causing LM Studio to repeatedly cast Clairvoyance.
  4. **Engine Architecture Discovery:** In `Assembly-CSharp.dll`, modern abilities implement `HandleEvent(CommandEvent)` (`MinEvent`), NOT the legacy `FireEvent(Event)`. In `AIBrainPart.cs`, calling `player.FireEvent(Event.New(cmd, "User", player))` was silently ignored by `LightManipulation.HandleEvent(CommandEvent)`.
  5. Ray-tracing beam abilities (`LightManipulation.Lase`) execute `PickLine(...)` which invokes `PickTarget.ShowPicker(...)`. Without active target cell interception in `AIPickTargetPatch`, `PickLine` returned empty and aborted the attack.
  6. Glowpads and turrets have 0 movement speed. Kiting at distance < 5 and repositioning at distance $\ge$ 5 formed an endless 4 $\leftrightarrow$ 5 tile orbit.
- **Implementation:**
  - In `AIBrainPart.cs`:
    - Updated `USE_ABILITY` to dispatch via `CommandEvent.Send(player, cmd, targetObj, targetCell, 0, false, false, null)` and auto-acquire `PreferredTargetCell`, `PreferredTargetObj`, and `PreferredDirection`.
    - Patched `XRL.UI.PickTarget.ShowPicker` and `ShowFieldPicker` to automatically return `PreferredTargetCell` during ability execution.
    - Patched `XRL.UI.PickDirection.ShowPicker` to infer direction from `PreferredTargetCell` or closest hostile.
  - In `brain.py`:
    - Filtered utility mutations (`clairvoyance`, `ambient light`) from combat prompts.
    - Added `lase`, `stunning force`, `syphon vim`, `cryokinesis`, `pyrokinesis` to `DIRECTIONAL_ABILITIES`.
    - Overhauled `fallback_esper` to prioritize `Sunder Mind` $\rightarrow$ `Lase` $\rightarrow$ `Cryo/Pyro` $\rightarrow$ `Stunning Force` $\rightarrow$ `Syphon Vim`.
    - Added stationary enemy detection (`glowpad`, `turret`, `fungus`) to halt orbit loops and strike decisively.
  - Verified across all 11 multi-class tactical dry run test suites with 100% pass rate.

#### Post-Deployment Telemetry Analysis (Concussive Knockback & Autoexplore Handoff)
- **Observed Behavior:** The Esper successfully engaged the glowpad with concussive blasts (`Stunning Force`) twice, but did not finish the kill and subsequently started wandering away north without re-engaging.
- **Root Causes Discovered:**
  1. **Concussive Knockback Physics:** `Stunning Force` deals bludgeoning concussive damage and physically knocks targets backward. Two blasts pushed the wet glowpad from distance 5 to distance 10.
  2. **Premature Combat Exit:** In `brain.py`, `close_threats` was hardcoded to `dist <= 10`. The moment the enemy was pushed to distance 10+, `is_in_combat` evaluated to `False`, immediately triggering Phase A `AUTOEXPLORE`. Native Autoexplore began pathfinding to unexplored tiles to the north, abandoning the surviving hostile.
  3. **Touch-Range & Non-Combat Abilities Polluting Prompt:** Dialogue and touch abilities (`Proselytize`, `Teleport Other`, `Intimidate`) were presented to LM Studio as valid combat choices at distance 10, causing the model to attempt recruitment rather than firing `Lase`.
- **Refinements Implemented:**
  - Expanded `close_threats` and tactical engagement ceiling from 10 to 20 tiles to maintain combat lock across full screen view distance and prevent zoning or premature autoexplore.
  - Added `proselytize`, `beguile`, and `berate` to `NON_COMBAT_KEYWORDS`.
  - Filtered touch-only abilities (`Teleport Other` restricted to adjacent, `Intimidate` to distance $\le 2$).
  - Reordered `VALID ACTIONS` in `query_llm_decision`: Ranged attacks (`FIRE_MISSILE`, `CommandLase`, `CommandSunderMind`, elemental rays) are now prepended at the very top of the list, before movement options, preventing smaller LLMs from defaulting to movement options.
  - Added strict ATTACK PRIORITY doctrine to LLM system prompt: character must attack when an offensive ability or missile is ready rather than wasting turns repositioning.
  - Updated Esper Mindflayer preferred range to 15 tiles and doctrine to fire Lase immediately at any range up to 25 tiles.
  - Added automatic direction vector injection in `query_llm_decision` if the LLM returns `USE_ABILITY:CommandLase` without direction.
  - Overhauled stationary enemy handling in `fallback_esper` to hold ground and recharge laser charges rather than wandering off, and enabled psychic assault at distance $\ge 1$.

#### Ability Rotation Architecture & Depleted Charge Tracking Resolution
- **Observed Behavior:** The Esper used `Lase` to kill some enemies, but once Lase ran out, it didn't rotate to other abilities (`Stunning Force`, `Teleport Other`, `Intimidate`). During cooldowns, it moved north and zoned off the map. Furthermore, approaching the dragonfly triggered a modal `[A]/[B]` prompt for Proselytize.
- **Root Causes Discovered:**
  1. **Depleted Charge Reporting in Qud:** In Caves of Qud, `Light Manipulation` when out of charges remains marked `IsUsable = true` and `CooldownTurns = 0`, but its name changes to `"Lase (0 charges)"`. Previously, `is_ability_ready()` only verified `usable` and `cooldown <= 0`. As a result, empty Lase was perpetually treated as ready, causing the brain to continually attempt `CommandLase` with 0 charges instead of rotating to `Stunning Force`.
  2. **Loop Breaker Combat Zoning:** When repeated actions failed, the loop breaker in `brain.py` called `get_valid_moves(surroundings, cur_pos, None)` without passing `is_in_combat=is_in_combat`, allowing `MOVE_N` across the zone boundary during active combat.
  3. **Lack of an Explicit Tactical Sequence:** The brain lacked a structured rotation sequence informing the LLM and fallback logic which ability serves as Opener CC, Sustained DPS, Heavy Execution, and Emergency Defense.
- **Implementation & Resolution:**
  - **Depleted Charge Filtering:** Added `is_ability_ready(ab)` in `brain.py` to inspect for `"0 charge"` or `"(0 charges)"`. Depleted abilities are flagged as recharging and removed from valid action choices.
  - **Structured Ability Rotations (`build_templates.py`):** Added explicit `ability_rotation` doctrines to all 5 archetypes:
    - *Esper*: 1. Opener CC (`Stunning Force`) $\rightarrow$ 2. Heavy Execution (`Sunder Mind`) $\rightarrow$ 3. Sustained DPS (`Lase`) $\rightarrow$ 4. Elemental Rays $\rightarrow$ 5. Secondary CC $\rightarrow$ 6. Emergency Close Defense (`Force Bubble`, `Teleport Other`, `Intimidate`).
    - *Axe Berserker*: Charge opener $\rightarrow$ Dismember $\rightarrow$ Cleave $\rightarrow$ Decapitate.
    - *Akimbo Gunslinger*: Disarming Shot $\rightarrow$ Chain Fire $\rightarrow$ Sustained dual missile fire.
  - **LLM Prompt Integration:** Injected `ABILITY ROTATION & COMBO DOCTRINE` into the LLM system prompt and tagged valid actions with explicit tactical roles (`OPENER CC`, `SUSTAINED BEAM DPS`, `HEAVY MENTAL EXECUTION`, `EMERGENCY BANISH`, `EMERGENCY FEAR`).
  - **Deterministic Fallback Synchronization:** Updated `fallback_esper` to execute the full rotation in priority order, including `Intimidate` and `Stunning Force` CC openers on approaching mobile targets.
  - **Combat Zoning Protection:** Fixed the loop breaker in `brain.py` to enforce `is_in_combat=is_in_combat` so the AI never flees across zone borders while fighting.
  - **Modal Interception Patch (`AIBrainPart.cs`):** Added Harmony patch `AIPickGameObjectPatch` for `XRL.UI.Popup.PickGameObject` to automatically select hostile targets and suppress modal target dialogs.
  - Verified with live state: with `Lase (0 charges)`, LM Studio immediately and correctly chose `USE_ABILITY:CommandStunningForce:SW` as the opener. All 11 tactical test suites pass with 100% success rate.

#### Pet Recruitment & Thrall Vanguard Architecture (`Proselytize`)
- **Objective:** Enable the Esper/Apostle to recruit living beasts and humanoids as loyal combat thralls using `Proselytize` and fight tactically alongside companions without friendly fire.
- **Engine Mechanics:**
  - `AIBrainPart.cs` scans `The.Player.CurrentCell.ParentZone.GetObjects()` for living objects with `brain.PartyLeader == player`, exporting `has_companion` and `companions` array (name, HP, max HP, distance, direction).
  - Individual entities in `visible_entities` are tagged with `is_companion: true/false`.
  - In `ExecuteCommand`, when `USE_ABILITY:CommandProselytize:DIR` is invoked, `AIBrainPart` acquires the adjacent candidate in that direction (living non-player creature) and sets `PreferredTargetObj` and `PreferredTargetCell`.
  - In `AIPickGameObjectPatch`, modal prompts prioritize hostile/neutral candidate creatures and strictly exclude the player or existing companions.
- **Tactical Doctrine & Integration:**
  - `brain.py`: Defined `is_proselytizable(entity)` to filter out plants, fungi, slime, turrets, robots, and corpses while targeting beasts, animals, and humanoids.
  - Excluded companions from `enemies` list and adjacent melee threat radar to prevent friendly fire.
  - **Flora & Brainless Object Filtering:** Fixed issue where the agent attempted to proselytize a `brimestalk` (plant stalk). In `AIBrainPart.cs`, candidate acquisition and `AIPickGameObjectPatch` now strictly require `obj.Brain != null && !obj.HasPart("Plant") && !obj.HasPart("Fungus") && !obj.HasPart("Robot")`, and export an engine-verified `can_proselytize: true/false`. In `brain.py`, `PROSELYTIZE_EXCLUSIONS` was expanded to cover all stalks (`brimestalk`, `brinestalk`), starapples, ferns, roots, lichen, and fungi, and `is_proselytizable()` strictly rejects any entity with `can_proselytize: false`.
  - Verified with LM Studio: When presented with an adjacent `snapjaw brute`, LM Studio reasoned *"Recruit snapjaw brute as frontline tank to absorb damage and enable safe ranged combat"* and executed `USE_ABILITY:CommandProselytize:E`. All 11 verification tests pass.

#### Caster Melee Suicide & Cooldown Recharge Standoff Resolution
- **Incident Analysis:**
  The character (Apostle / Esper Mindflayer) was facing an adjacent glowpad and glowfish with 5/27 HP, wearing a cloth robe (0 AV), holding a wooden staff (1d2 damage), and suffering from active bleeding. `Teleport Other` and `Sprint` were ready, while `Stunning Force` and `Lase` charges were depleted. Instead of banishing the adjacent hostile or retreating, the character executed a melee bump-attack (`MOVE_NW`), taking counterattack and bleed damage, and died.
- **Root Causes Discovered:**
  1. **Generic Melee Bump Actions in Prompt:** In `query_llm_decision`, `MOVE_{d} (Melee Attack {ename})` was uniformly generated for all classes when enemies were adjacent. In the system prompt, Rule 2 instructed: *"If an offensive action (Missile Snipe, Lase, Sunder Mind, Ray, Charge, or Melee Attack) is listed in VALID ACTIONS, YOU MUST ATTACK."* The model interpreted `Melee Attack` as a mandatory attack obligation rather than retreating or casting `Teleport Other`.
  2. **Staff Advance in Fallback:** In `fallback_esper`, lines 1029-1033 intentionally commanded `MOVE_{s_dir}` (*"Advancing to strike stationary with staff"*) if an enemy was within 3 tiles and ranged powers were cooling down.
  3. **Absence of `WAIT` Recharge Choice:** In Caves of Qud, `Light Manipulation` passively regenerates laser charges from ambient light every few turns, and mental mutations cool down turn-by-turn. However, `WAIT` was never included in `action_choices` for LM Studio, forcing the model to move.
  4. **Target Direction Misalignment in C# Mod:** In `AIBrainPart.cs`, `USE_ABILITY` retained stale `player.Target` or `Sidebar.CurrentTarget` even when `PreferredDirection` pointed elsewhere, preventing touch-range abilities like `CommandTeleportOther` from acquiring the adjacent enemy in the intended direction.
- **Implementation & Resolution:**
  - **Archetype Distinction (`is_pure_caster_or_ranged`):** Pure casters and ranged specialists are strictly forbidden from voluntary melee bump-attacks. Melee attack is only generated as a desperate last resort if cornered with 0 open moves, 0 sprint, and 0 defensive cooldowns.
  - **Emergency Banishment Prioritization:** When adjacent to hostiles, `USE_ABILITY:CommandTeleportOther:<DIR>` and `USE_ABILITY:CommandForceBubble` take absolute precedence over bump-attacks.
  - **Standoff & Recharge Policy:** Added `WAIT (Hold safe standoff distance & recharge Light Manipulation laser charges / mental cooldowns)` to valid choices when distance is $\ge 2$, and backpedal kiting when distance $< 4$.
  - **Critical Bleeding Alert:** Added immediate high-priority warning alerting the AI when bleeding to prioritize emergency banishment and safe retreat.
  - **C# Mod Targeting Alignment:** In `AIBrainPart.cs`, when `PreferredDirection` is specified, `targetObj` and `targetCell` are synchronized to that directional vector, and touch-range abilities (`Teleport Other`, `Proselytize`) automatically acquire the object in the adjacent cell.
  - Verified on live death state: LM Studio immediately chose `USE_ABILITY:CommandTeleportOther:NW` (*"Banish immediate melee threat with Teleport Other for emergency defense"*). All 17 verification tests passed.

---

## 4. Current Codebase Specification (v1.0.0)

### Directory Structure
```
D:\QudAI\
├── brain.py                    # Master autonomous AI driver & hierarchical decision loop
├── build_templates.py          # 5 build archetypes, combat doctrines, stat/skill priority trees
├── chronicler.py               # Post-mortem death analyzer & ancestral memory generator
├── dry_run.py                  # 9-scenario multi-class verification test suite
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
| `state.json` | Game $\rightarrow$ Python | JSON (UTF-8) | Full turn state: HP, position, 5x5 grid, radar entities, attributes, skills, mutations, calling, ammo |
| `action.json` | Python $\rightarrow$ Game | JSON (UTF-8) | Dispatched action command (`MOVE_N`, `FIRE_MISSILE@x,y`, `USE_ABILITY:cmd:dir`, `AUTOLEVEL`, etc.) |
| `active.flag` | Python $\leftrightarrow$ Game | Text | Presence indicates autonomous AI is engaged; deletion pauses AI and restores manual control |
| `death.json` | Game $\rightarrow$ Python | JSON (UTF-8) | Exported upon player death containing cause, killer, killer level, recent damage, and recent actions |

### Decision Pipeline (Phases A, B, C)
1. **Phase A (Safe Mode)**: Runs when no enemies are visible within 10 tiles, no damage was taken, and no adjacent hostiles exist.
   - Allocates unspent AP/SP/MP (Twitch vote winner or class milestone).
   - Rests until HP $\ge 75\%$.
   - Reloads missile magazines from spare inventory ammo.
   - Explores least-visited frontier tiles using spatial coordinate tracking.
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

### Iteration 8: Build Guide Integration, Raytraced LOF & Pet Safety
* **Implementation Date**: September 2026
* **Key Achievements**:
  1. **Engine Difficulty & Threat Tier Export**: Updated `AIBrainPart.cs` to calculate relative difficulty tiers (`Trivial`, `Easy`, `Average`, `Tough`, `Very Tough`, `Impossible`), entity level, zone tier, and stationary status.
  2. **Glowpad & Distant Trivial Entity Policy**: Addressed the agent's tendency to halt exploration and cross entire swamps to kill every glowpad. Distant stationary trivial entities ($dist > 3$) are excluded from combat locking, allowing autoexplore to continue smoothly. Real threats and adjacent enemies are prioritized.
  3. **Bresenham Raytraced Line-of-Fire (LOF)**: Implemented 2D grid ray-tracing. Beam attacks (`Lase`, `Freezing Ray`, `Flaming Ray`) and missile weapons verify that friendly pets are not in the line of trajectory. If an ally is in the way, the AI redirects to `Sunder Mind` (pure mental attack with zero projectile collision), targets an unblocked enemy, or repositions.
  4. **9 Archetypes from Build Guide**: Harmonized `build_templates.py` to support Auspicious Beginnings, Praetorian Generalist, Limb-Off, Esper-ited Away, Uncle Iroh, Bullet Specter, Classic Punchkin, Gunkin, and Gas Giant.
  5. **10-Criteria Item Evaluator (`item_evaluator.py`)**: Implemented the scoring rubric and hard overrides from the guide (never discard sole light source, sole ranged weapon, recoiler, or uninspected artifacts).
  6. **15 Multi-Class Verification Tests**: Expanded `dry_run.py` to 15 comprehensive unit tests covering all 9 archetypes, LOF raytracing, companion protection, glowpad de-prioritization, and item scoring. All 15 tests pass cleanly.

---

### Iteration 9: Companion Absolute Immunity & Post-Proselytize State Resolution
* **Implementation Date**: September 2026
* **Key Achievements**:
  1. **Engine-Level Companion Rule 0 (`AIBrainPart.cs`)**:
     - Discovered root cause of friendly fire post-charm: when a creature was charmed, `player.Target` or `Sidebar.CurrentTarget` in the game engine remained set to the creature from before the charm succeeded.
     - `CheckIsEnemy()` previously evaluated `player.Target == obj` before party leader status. Inverted check: Rule 0 is now `var ctBrain = obj.Brain ?? obj.GetPart<Brain>(); if ((ctBrain != null && ctBrain.PartyLeader == player) || obj.IsLedBy(player)) return false;` strictly before any target or hostility check.
     - Added automatic purging of `player.Target` and `Sidebar.CurrentTarget` if pointing to a companion.
     - Added companion labeling `[COMPANION: {name}]` in `GetCellSummary()`.
  2. **Comprehensive Companion Immunity in Python (`brain.py`)**:
     - Implemented `filter_hostile_enemies(entities, companions)` which aggressively purges any entity whose coordinate matches a companion, whose name contains the companion name, or whose `is_companion` flag is set.
     - Integrated `filter_hostile_enemies` across `main()`, `query_decision()`, `query_llm_decision()`, and all 4 tactical class fallbacks (`fallback_melee`, `fallback_esper`, `fallback_gunslinger`, `fallback_nomad`).
     - Updated `get_adjacent_threats(surroundings, companions=companions)` to ignore `[COMPANION:` tiles and filter out companion names, preventing false close-contact alarms that previously caused the agent to backpedal in circles around its own pet.
     - Hardened `is_line_of_fire_clear`: If the target endpoint `(x1, y1)` itself is a friendly companion, immediately returns `(False, "Target coordinate IS friendly companion!")`, preventing any ranged weapon or beam ability from targeting a pet.
     - Updated 5x5 ASCII grid display: companions are now rendered as `C` (distinguishing `@` player, `C` companion, and `E` enemy).
  3. **Verification Suite Expansion (`dry_run.py`)**:
     - Added Test 16: Simulates a post-proselytize state with an adjacent charmed goat and stale engine flags. Verifies that `filter_hostile_enemies` purges the entity, `is_line_of_fire_clear` blocks targeting, `get_adjacent_threats` returns empty, the 5x5 grid shows `C`, and the decision engine cleanly selects `AUTOEXPLORE` instead of attacking or backpedaling.
     - All 16 verification tests pass with 100% success.

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
- **Stair & Chasm Navigation**: Smart traversal of up/down stairs, detecting shafts and safe exits.

### Milestone 10: Companion & Temporal Fugue Clone Coordination
- **Companion Orders**: For Espers with Beguile/Proselytize, command followers to tank or hold ground.
- **Temporal Fugue Safety**: When mental clones spawn, prevent friendly-fire missile discharges and crossfire traps.
- **Clairvoyance Targeting**: Fire missiles through walls when using phasing or clairvoyance.

### Milestone 11: Real-Time Stream Overlay (OBS Web Widget)
- **Local WebSocket Server**: Stream telemetry in real-time to an HTML5/CSS canvas.
- **On-Screen Display (HUD)**:
  - Live character portrait with calling and active doctrine.
  - HP bar, ammo gauge, and surrounding 5x5 ASCII minimap.
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
