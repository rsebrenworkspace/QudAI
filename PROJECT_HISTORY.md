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
  - Expanded `close_threats` and tactical engagement ceiling from 10 to 18 tiles to maintain combat lock across full screen view distance.
  - Added `proselytize`, `beguile`, and `berate` to `NON_COMBAT_KEYWORDS`.
  - Filtered touch-only abilities (`Teleport Other` restricted to adjacent, `Intimidate` to distance $\le 2$).
  - Highlighted `Light Manipulation` (`Lase`) as the primary offensive beam attack in `build_templates.py` and labeled it `PRIMARY OFFENSIVE ATTACK` in LLM action formatting.
  - Added automatic direction vector injection in `query_llm_decision` if the LLM returns `USE_ABILITY:CommandLase` without direction.
  - Overhauled stationary enemy handling in `fallback_esper` to hold ground and recharge laser charges rather than wandering off.

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
3. **Phase C (Deterministic Fallback Matrix)**:
   - **Melee (`axe_berserker`, `praetorian_tank`)**: Charges enemies at dist 2–4; executes Dismember / Shield Slam or bump-attacks adjacent threats; only retreats if surrounded by $\ge 3$ hostiles and HP $< 35\%$.
   - **Mental (`esper_mindflayer`)**: Pops Force Bubble or Teleports when pressed close; casts Sunder Mind or Cryokinesis / Pyrokinesis at range; maintains distance $\ge 6$.
   - **Gunslinger (`akimbo_gunslinger`)**: Holds 3–6 tiles; fires Chain Fire and Disarming Shot; step-and-shoots if enemy closes in; tactical reloads when disengaged.
   - **Sniper (`rifle_nomad`)**: Freezes pursuers with Freezing Ray; snipes at distance $\ge 2$; sprint-kites when dry.

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
