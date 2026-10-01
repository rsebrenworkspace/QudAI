# Caves of Qud: Engine Internals, Modding Architecture & Reverse-Engineering Manual for Autonomous Agents

**Document Version:** 1.0.0  
**Target Engine:** *Caves of Qud* (Unity .NET Standard 2.1 / C# Harmony 2.x)  
**Author:** QudAI Development Team  
**Date:** September 2026  

---

## Table of Contents
1. [Executive Architecture & Headless Philosophy](#1-executive-architecture--headless-philosophy)
2. [Unity Engine Runtime, .NET Environment & Threading Model](#2-unity-engine-runtime-net-environment--threading-model)
3. [Modal Dialog Suppression & Headless Turn Cycle](#3-modal-dialog-suppression--headless-turn-cycle)
4. [UI Picker Interception Architecture (Direction, Target & GameObject)](#4-ui-picker-interception-architecture-direction-target--gameobject)
5. [The Event Dispatch System: MinEvent vs. Legacy FireEvent](#5-the-event-dispatch-system-minevent-vs-legacy-fireevent)
6. [Combat Mechanics, Ballistics & Missile Systems](#6-combat-mechanics-ballistics--missile-systems)
7. [Companion Faction Dynamics, Rule 0 & Friendly-Fire Immunity](#7-companion-faction-dynamics-rule-0--friendly-fire-immunity)
8. [Settlement Social Hierarchy & Peaceful Townsfolk Safeguards](#8-settlement-social-hierarchy--peaceful-townsfolk-safeguards)
9. [Navigation Systems: Native Autoexplore, Oscillation Breakers & Shorelines](#9-navigation-systems-native-autoexplore-oscillation-breakers--shorelines)
10. [Vertical Stratum Delving & Tactical Retreat Dynamics](#10-vertical-stratum-delving--tactical-retreat-dynamics)
11. [Character Progression Internals: Stats, Skills, Mutations & SP Savings](#11-character-progression-internals-stats-skills-mutations--sp-savings)
12. [Sustenance & Survival: Hunger Physics, Butchery, Camping & Cooking](#12-sustenance--survival-hunger-physics-butchery-camping--cooking)
13. [Zone Boundary Physics, Coordinate Systems & Ping-Pong Prevention](#13-zone-boundary-physics-coordinate-systems--ping-pong-prevention)
14. [Reverse-Engineering Tooling, Mod Deployment & Troubleshooting Guide](#14-reverse-engineering-tooling-mod-deployment--troubleshooting-guide)

---

## 1. Executive Architecture & Headless Philosophy

Building an autonomous agent for *Caves of Qud* presents unique engineering hurdles unlike standard turn-based or grid games:
1. **Permadeath & Emergent Complexity:** Tens of thousands of interacting objects, fluids, temperature systems, dismemberment mechanics, psychic glimmer, and intricate faction diplomacy. A single misstep (e.g. hitting a friendly pet, walking into deep acid, starving while resting) permanently ends a 20-hour run.
2. **Hybrid Hierarchical Decision Pipeline:**
   - **Phase A (Deterministic Safe Mode, 0ms latency):** Handles exploration, eating, cooking, resting, ammo top-offs, staircase delving, and skill learning without calling expensive LLM APIs.
   - **Phase B (Tactical LLM Reasoning, 2–4s latency):** Formats 5x5 ASCII surroundings, radar, status effects, and archetype combat doctrines for local language models (LM Studio) when in combat.
   - **Phase C (Class-Specific Deterministic Fallbacks, 0ms latency):** A fail-safe safety net that catches LLM timeouts, malformed outputs, or impossible commands according to dedicated archetype doctrines (Melee, Esper, Gunslinger, Sniper).
3. **The IPC Pipeline:**
   - Communication between the C# Harmony mod (`QudAIBrain`) and the Python driver (`brain.py`) uses file-based JSON IPC in `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI`:
     - `state.json`: Exported by the engine at the start of each player turn.
     - `action.json`: Written by Python; consumed and executed headlessly by the C# mod.
     - `active.flag`: Sentinels autonomous execution. Deleting it instantly pauses the AI and returns control to the human player.
     - `death.json`: Exported upon death for tombstone analysis and ancestral memory generation.

---

## 2. Unity Engine Runtime, .NET Environment & Threading Model

### 2.1 Environment Constraints
- **Target Assembly:** `Assembly-CSharp.dll` (located in `<SteamLibrary>\steamapps\common\Caves of Qud\CoQ_Data\Managed\`).
- **Framework:** .NET Standard 2.1 / Mono under Unity 2021+.
- **Harmony Version:** Harmony 2.x bundled natively with Qud modding support.

### 2.2 Threading & Deadlock Avoidance
- In vanilla *Caves of Qud*, player turns are often processed across coroutines and UI thread dispatches.
- **Critical Discovery:** Setting:
  ```csharp
  GameManager.runPlayerTurnOnUIThread = false;
  ```
  is strictly necessary when running automated player turn cycles. If left `true`, asynchronous file I/O or turn-pacing sleeps on background threads can deadlock Unity's main dispatcher.
- Energy Accounting: A standard Qud turn consumes 1,000 energy units:
  ```csharp
  player.UseEnergy(1000, "Pass");
  ```
  Every headless action must cleanly consume the appropriate energy cost or call `player.UseEnergy(1000)` to advance the simulation clock and trigger the world turn tick.

---

## 3. Modal Dialog Suppression & Headless Turn Cycle

### 3.1 The Popup Trap
Vanilla *Caves of Qud* relies heavily on blocking UI modal popups:
- Level-up announcements (`Popup.Show("You reached Level 2!")`).
- Mutation selection prompts.
- Asking for confirmation to drink strange liquids, trade, or enter dangerous areas.
- Death notifications.

When running headlessly, any unsuppressed modal window permanently captures input focus, halts turn execution, and leaves the agent permanently frozen waiting for human keyboard input.

### 3.2 The Fix: Harmony Pop-Up Suppression
`AIBrainPart.cs` patches `XRL.Core.PlayerTurn.Prefix`:
```csharp
Popup.bSuppressPopups = true;
Popup.Suppress = true;
```
Furthermore, the mod patches `XRL.UI.Popup.Show` and related dialog methods using Harmony prefixes that return `false` (skipping the original method) whenever `AIBrainPart.IsActive` is true.

---

## 4. UI Picker Interception Architecture (Direction, Target & GameObject)

Whenever a player activates a directional ability (e.g. `Charge`, `Dismember`, `Freezing Ray`, `Stunning Force`) or a ranged weapon, Qud's game loop calls modal picker classes:
1. `XRL.UI.PickDirection.ShowPicker(...)`
2. `XRL.UI.PickTarget.ShowPicker(...)` and `ShowFieldPicker(...)`
3. `XRL.UI.PickGameObject.ShowPicker(...)`

If unpatched, these methods spawn an interactive cursor on the screen and block until the user hits arrow keys and Space/Enter.

### 4.1 Headless Picker Interception Patches
`AIBrainPart.cs` contains Harmony patches for all three pickers:
- **`AIPickDirectionPatch` (`PickDirection.ShowPicker`)**:
  - Checks if `PreferredDirection` or `PreferredTargetCell` is set by the incoming command.
  - If set, returns the direction string (`"N"`, `"S"`, `"E"`, `"W"`, etc.) immediately and sets `__result`, skipping the GUI.
  - If not set, infers the direction to the closest hostile enemy automatically.
- **`AIPickTargetPatch` (`PickTarget.ShowPicker` / `ShowFieldPicker`)**:
  - Returns `PreferredTargetCell` directly as `__result`.
- **`AIPickGameObjectPatch` (`PickGameObject.ShowPicker`)**:
  - Automatically selects `PreferredTargetObj`, strictly filtering out friendly pets and companions.

---

## 5. The Event Dispatch System: MinEvent vs. Legacy FireEvent

One of the deepest pitfalls in Qud modding is the dual-event system.

### 5.1 The Evolution from `Event` to `MinEvent`
- **Legacy Qud:** Objects received actions via `player.FireEvent(Event.New("CommandName", ...))`.
- **Modern Qud (`MinEvent` Architecture):** High-performance mutations, activated abilities, and physical parts implement `IEventHandler` and process `CommandEvent` (derived from `MinEvent`).

### 5.2 The `CommandLase` / `LightManipulation` Discovery
- Calling:
  ```csharp
  player.FireEvent(Event.New("CommandLase", "User", player)); // SILENTLY FAILS!
  ```
  returns without doing anything because modern `LightManipulation` only listens to `CommandEvent`!
- **The Modern Implementation:**
  ```csharp
  CommandEvent.Send(player, cmd, targetObj, targetCell, 0, false, false, null);
  ```
- In `AIBrainPart.cs`, the ability executor tests both or uses `CommandEvent.Send` with `PreferredTargetCell` and `PreferredDirection` pre-populated, ensuring 100% execution across legacy skills and modern mutations.

---

## 6. Combat Mechanics, Ballistics & Missile Systems

### 6.1 The 90-Degree Fan Spray Discovery (`sweepwidth`)
- When decompiling `XRL.World.Parts.Combat.FireMissileWeapon`, the method signature accepts 10 parameters:
  ```csharp
  public static bool FireMissileWeapon(
      GameObject Attacker,
      GameObject Weapon,
      Cell TargetCell,
      ...
      int sweepwidth = 90,  // <-- CRITICAL ENGINE DEFAULT!
      int rapid = 0,
      ...
  )
  ```
- Because `sweepwidth` defaulted to 90 degrees, early autonomous agents equipped with desert rifles or pistols sprayed shots in a wide cone, missing distant targets and hitting walls or companions!
- **Fix:** In `AIBrainPart.cs`, `FireMissileWeapon` is invoked with `sweepwidth = 0` and `rapid = 0` for surgical, pinpoint ballistic accuracy.

### 6.2 Magazine Ammo Loaders
- Qud missile weapons use `MagazineAmmoLoader` parts.
- Loaded ammo resides in the weapon's magazine (`ammo.Count`), while reserve ammo resides in player inventory (`lead slug`, `arrow`, `chem cell`).
- The Python telemetry parses both `missile_ammo` (current magazine) and `inventory_ammo` (spare rounds). Tactical combat fallbacks enforce combat reloads (`RELOAD`) only when disengaged ($dist \ge 2$) or when magazines are completely dry.

### 6.3 Raytraced Line-of-Fire (LOF) & Companion Safety
- Missile trajectories and beam attacks (`Lase`, `Freezing Ray`, `Flaming Ray`) travel in direct lines across the 80x25 grid.
- `brain.py` implements a 2D integer **Bresenham line algorithm** (`is_line_of_fire_clear`):
  - Traces intermediate points between player `(px, py)` and target `(tx, ty)`.
  - If any intermediate tile contains a friendly companion, LOF is declared obstructed.
  - If target tile itself is a companion, targeting is aborted with a hard exception.
  - If LOF is blocked, the AI redirects to unblocked alternate targets, switches to non-colliding mental powers (`Sunder Mind`), or repositions sideways.

---

## 7. Companion Faction Dynamics, Rule 0 & Friendly-Fire Immunity

### 7.1 The Post-Charm Friendly Fire Incident
When an Esper character recruited a companion using `Proselytize` or `Beguile`:
1. `player.Target` or `Sidebar.CurrentTarget` in engine memory remained locked onto the newly charmed creature.
2. In early mod versions, `CheckIsEnemy()` evaluated `player.Target == obj` before checking party leader status, reporting the new pet as an enemy!
3. The C# mod iterated `ParentZone.GetObjects()`, which threw `InvalidOperationException: Collection was modified` whenever creatures moved or spawned, clearing the companion list to `[]`.
4. As a result, the AI thought it was in melee combat with a hostile, backpedaled, and blasted its own pet with concussive forces (`Stunning Force`) or lasers.

### 7.2 The 5-Layer Companion Immunity System
1. **Engine Rule 0 (`AIBrainPart.cs`):**
   ```csharp
   var ctBrain = obj.Brain ?? obj.GetPart<Brain>();
   if ((ctBrain != null && ctBrain.PartyLeader == player) || obj.IsLedBy(player))
       return false; // NEVER AN ENEMY
   ```
2. **Comprehensive Companion Part & Effect Scanning:**
   Checks effects: `Proselytized`, `Beguiled`, `Rebuked`, `Lovesick`, `LoveTonic`.
   Checks parts: `AllyProselytize`, `AllyBeguile`, `AllyRebuke`, `AllyPet`, `AllyClone`.
   Checks native collection: `player.GetCompanions()`.
3. **Safe Cell-by-Cell Zone Traversal (`GetSafeZoneObjects`):**
   Replaced all throwing `ParentZone.GetObjects()` loops with:
   ```csharp
   for (int x = 0; x < 80; x++)
       for (int y = 0; y < 25; y++) {
           var cell = zone.GetCell(x, y);
           if (cell?.Objects != null) { ... }
       }
   ```
4. **Target Sanitization:**
   If `player.Target` or `Sidebar.CurrentTarget` points to a companion, it is immediately set to `null`.
5. **Zero-Latency Python Whitelisting:**
   As soon as `USE_ABILITY:CommandProselytize:<DIR>` is dispatched, the target coordinates and creature name are added to `CHARMED_COMPANION_NAMES` and `CHARMED_COMPANION_COORDS` with 0ms latency, immunizing the creature before the next frame even serializes.

---

## 8. Settlement Social Hierarchy & Peaceful Townsfolk Safeguards

### 8.1 Peaceful Townsfolk vs. Hostile Factions
In starter settlements like Joppa, the town is populated by quest givers, preachers, farmers, and water merchants:
- `is_peaceful_npc(name, blueprint)` inspects names and blueprints for keywords:
  - `farmer`, `warden`, `elder`, `convert`, `zealot`, `merchant`, `trader`, `dromad`, `pariah`, `villager`, `citizen`, `settler`, `irudad`, `yrame`, `mehmet`, `argyve`, `tam`, `obsessionist`, `priest`, `preacher`.
- **Hostile Override Guard:** Explicit aggressive factions (`snapjaw`, `raider`, `cannibal`, `goatfolk`, `putus`, `templar`, `issachari`) override peaceful flags, ensuring combat is never suppressed against genuine enemies.

---

## 9. Navigation Systems: Native Autoexplore, Oscillation Breakers & Shorelines

### 9.1 Native Autoexplore Integration
Rather than implementing a slow, imperfect Python frontier explorer, QudAI harnesses Qud's internal pathfinding engine:
```csharp
XRL.World.Capabilities.FasterDMapAutoexplore.FindAutoexploreStep(out string step, out bool blackout);
```
- `step` returns the exact cardinal movement string (`"N"`, `"S"`, `"E"`, `"W"`, etc.) towards unrevealed tiles, floor loot, or containers.
- When the zone is fully traversed, `step` returns `"."` or `null`.
- In `state.json`, `zone_fully_explored = true` signals that autoexplore has finished.

### 9.2 Multi-Tile Oscillation Loop Breaker
When exploring houses or narrow rooms, the character could get trapped oscillating between an obstacle (sign, table, or door frame):
- `brain.py` tracks coordinate history in `recent_positions` (deque of size 10).
- If `pos_frequency >= 3` at any coordinate:
  1. If running `AUTOEXPLORE`, marks the zone as exhausted in `stuck_autoexplore_zones`.
  2. Filters `valid_moves` to only include unvisited coordinates (`not in recent_positions`).
  3. Sorts escapes by `visit_counts` to break out into unexplored frontier terrain.

### 9.3 Shoreline Water & Companion Swapping
- In waterlogged zones (Salt Marshes, rivers), deep liquid tiles block pathfinding.
- If a companion stands on the only dry shore tile, standard move generation would consider the character trapped.
- **Companion Move Priority:** Adjacent companion tiles are placed in a secondary `companion_moves` list. The character prioritizes open ground, but will bump-swap with a companion if no dry terrain is available, completely eliminating shoreline lockups.

---

## 10. Vertical Stratum Delving & Tactical Retreat Dynamics

### 10.1 Stratum Depths & Staircase Detection
- Caves of Qud coordinates use $(x, y, z)$ where:
  - $z = 10$: Surface world map parasang layer.
  - $z = 11$: Stratum 1 underground.
  - $z = 12+$: Stratum 2+ deep subterranean layers.
- Staircases are reported in `state.json` as `stairs_down` and `stairs_up` (including `Hole`, `Shaft`, `Ladder`, and `Stairs`).
- The agent persists known stair locations per zone in `KNOWN_STAIRS_DOWN` and `KNOWN_STAIRS_UP`.

### 10.2 Depth Gating Formula
To prevent Level 1 characters from plunging into deep dungeons and instantly dying, delving is strictly gated by character level:
$$\text{Required Level}(z) = \begin{cases} 1 & \text{if } z \le 10 \\ 3 & \text{if } z = 11 \\ 3 + (z - 11) \times 2 & \text{if } z \ge 12 \end{cases}$$
If standing on stairs down below the required level, the agent treats the zone as requiring further surface exploration to level up.

### 10.3 Tactical Underground Retreat Protocol
When delving underground ($z > 10$), the agent continuously monitors life safety:
- **Trigger Conditions:**
  - $HP < 35\%$ of maximum.
  - Damage sustained while $HP < 45\%$.
  - Detection of an `Impossible` difficulty hostile.
- **Action Sequence:**
  1. Aborts autoexplore and combat offensive.
  2. Paths towards `KNOWN_STAIRS_UP[zone_id]`.
  3. Ascends to the stratum above using `USE_STAIRS_UP`.
  4. Sets `RETREAT_TARGET_LEVEL = cur_level + 1`.
  5. Rests, recovers HP, and explores surface/higher strata until the target level is attained before attempting to re-delve.

---

## 11. Character Progression Internals: Stats, Skills, Mutations & SP Savings

### 11.1 The C# Leveling API (`GameObject.SetProperty` does NOT exist)
In modern Qud, `GameObject` does NOT possess a `SetProperty` method. Attempting to call it results in compiler error CS1061.
The correct engine API:
- **Attribute Points (AP):**
  ```csharp
  var stat = player.GetStat(statName);
  stat.BaseValue += 1;
  player.GetStat("AP").Penalty += 1;
  ```
- **Mutation Points (MP):**
  ```csharp
  var muts = player.GetPart<Mutations>();
  muts.LevelMutation(mut, mut.BaseLevel + 1);
  player.UseMP(1, "default");
  ```
- **Skill Points (SP):**
  ```csharp
  var skills = player.GetPart<Skills>();
  skills.AddSkill(skillClass);
  player.GetStat("SP").Penalty += cost;
  ```

### 11.2 Skill Trees & Prerequisite Gating
- `SkillFactory` organizes abilities into Parent Skills (e.g. `Axe`, `Shield`, `Tactics`, `CookingAndGathering`) and Subskills (e.g. `Axe_Dismember`, `Shield_Slam`, `Tactics_Hurdle`).
- **Prerequisite Enforcement:** The Python driver inspects `learnable_skills` and parent trees:
  - Parent skills must be unlocked before subskills can be purchased.
  - 0-cost subskills (e.g. `Axe_Expertise`, `Shield_Block`) are claimed immediately upon unlocking the parent skill.
- **SP Savings Doctrine:** If the character's next milestone skill costs 150 SP (e.g. `Customs`), the agent will NOT waste 75 SP on random filler skills; it saves its points until the priority milestone is affordable.

### 11.3 Autolevel Circuit Breaker
If unspent points cannot be allocated (e.g. missing stat prerequisites), the agent increments `autolevel_failed_attempts`. If 2 consecutive attempts fail, `suppress_autolevel=True` engages, preventing infinite turn freezes and falling back to exploration.

---

## 12. Sustenance & Survival: Hunger Physics, Butchery, Camping & Cooking

### 12.1 Hunger Physics & Starvation Traps
- Managed by `XRL.World.Parts.Stomach`.
- Hunger levels: `Satisfied` $\rightarrow$ `Hungry` $\rightarrow$ `Famished`.
- **The Starvation Trap:** In vanilla Qud, resting while `Famished` prevents HP regeneration and accelerates starvation damage.
- **The Solution:** Sustenance is placed at **Step 2 of Phase A** in `brain.py`, strictly ahead of resting at Step 3.

### 12.2 Engine Survival Mechanics
- **Butchering:** Animal corpses possess `Butcherable`. Calling `AttemptButcher(player)` yields raw meat and cooking ingredients.
- **Harvesting:** Wild plants possess `Harvestable`. Calling `AttemptHarvest(player)` harvests ingredients.
- **Camping & Cooking:**
  - With `CookingAndGathering` / `Survival_Camp`, dispatching `CommandSurvivalCamp` creates a campfire.
  - Telemetry detection: Check both `player.HasSkill("CookingAndGathering")` and activated abilities via `player.GetPart<ActivatedAbilities>()?.HasAbility("CommandSurvivalCamp")`.
  - At an adjacent campfire, `Campfire.Cook()` whips up a meal, satisfying hunger and conferring cooking metabolic buffs.
  - Stomach API: Call `player.GetPart<Stomach>()?.ClearHunger()`.
    > [!IMPORTANT]
    > In modern Caves of Qud, `player.pStomach` does **not** exist on `GameObject` (causes `CS1061`). Always use `player.GetPart<Stomach>()`.
  - Direct eating: `Event.New("Eat", "Eater", player)` consumes packaged food from inventory.
  - Food Telemetry: Packaged rations may have either the `Food` part or the `PreparedCookingIngredient` part (e.g. jerky, dried fruit, starapple wafers). AIBrainPart checks `item.HasPart<Food>() || item.HasPart<PreparedCookingIngredient>()`.
- **Mutation API Deprecation:**
  - In `BaseMutation`, the property `m.DisplayName` is obsolete (`CS0618`). Modern Qud requires calling `m.GetDisplayName()`.

---

## 13. Zone Boundary Physics, Coordinate Systems & Ping-Pong Prevention

### 13.1 Coordinate Systems & Edge Exits
- Each zone is a discrete 80-column $\times$ 25-row grid ($x \in [0, 79]$, $y \in [0, 24]$).
- Stepping beyond $x=0$ exits West; $x=79$ exits East; $y=0$ exits North; $y=24$ exits South.
- When transitioning into an adjacent zone, the character spawns on the extreme opposing border tile (e.g. transitioning East puts the player at $x=0$ in the new zone).

### 13.2 The Zone Hopping Ping-Pong Loop
- When a zone is marked explored, the agent searches for zone exits.
- If the player just entered at $x=0$, `surroundings["W"]` immediately reports `"[ZONE_EXIT: W]"`.
- Without hysteresis, the agent immediately steps West, hopping straight back into the previous zone, triggering infinite back-and-forth oscillation.

### 13.3 The Inward Border Navigation Solution
1. **Border Detection:** `is_on_border = (px in (0, 79) or py in (0, 24))`.
2. **Reverse Exit Tracking:** `LAST_ZONE_ENTRY` records `reverse_dir` (the exit leading back to the previous zone).
3. **Inward Vector Steering:** During the first 4 turns in a new zone (or if 2-cycle oscillation is detected), the agent discards `rev_exit` and forces movement towards the zone center $(40, 12)$.
4. **Backtrack Suppression:** In fully explored zones, reverse exits are suppressed until the agent has taken at least 6 turns scouting the area.

---

## 14. Reverse-Engineering Tooling, Mod Deployment & Troubleshooting Guide

### 14.1 Reverse-Engineering Tooling (`dnfile` vs. PowerShell)
- **PowerShell / .NET Reflection Failure:** Windows PowerShell 5.1 fails when reflecting Unity .NET Standard 2.1 assemblies, throwing `TypeLoadException` due to default interface methods.
- **Python `dnfile`:** The most reliable offline decompiler tool. It directly parses ECMA-335 metadata tables, method signatures, parameters, and type hierarchies without loading the assembly into the host CLR:
  ```python
  import dnfile
  pe = dnfile.dnPE(r"D:\QudAI\tools\Assembly-CSharp.dll")
  # Inspect TypeDef, MethodDef, Param tables cleanly
  ```

### 14.2 Mod Deployment Pipeline
- Repository source resides in `D:\QudAI\mod\QudAIBrain\AIBrainPart.cs`.
- Game mod directory resides in `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\QudAIBrain\`.
- **Deploy Command:**
  ```powershell
  python D:\QudAI\sync_mod.py deploy
  ```
- **Brace Balance Verifier:** Always verify opening and closing braces before launching the game:
  ```powershell
  python -c "t = open(r'D:\QudAI\mod\QudAIBrain\AIBrainPart.cs', encoding='utf-8').read(); assert t.count('{') == t.count('}'), 'Braces unbalanced!'"
  ```

### 14.3 Multi-Class Regression Suite (`dry_run.py`)
- Contains 25 comprehensive scenarios testing:
  - Low-HP resting and ammo top-offs.
  - Directional abilities (Melee Charge, Dismember, Freezing Ray, Stunning Force).
  - Raytraced LOF and companion friendly-fire immunity.
  - Peaceful townsfolk immunity.
  - Multi-tile and shoreline oscillation loop breaking.
  - Staircase gating, delving, and emergency retreat.
  - Skill prerequisite hierarchy, 0-cost subskills, and SP savings.
  - Zone hopping prevention and inward border steering.
  - Survival routines (butchering, harvesting, camping, cooking, eating).
  - 5-tile shoreline loop detection, spatial entropy thresholding, and centroid steering.
- Run verification before committing:
  ```powershell
  python D:\QudAI\dry_run.py
  ```

---

## 15. Oscillation Dynamics: 5-Tile Shoreline Loops, Spatial Entropy & Centroid Steering

### 15.1 The Mathematical Blind Spot of Fixed-Window Frequency
In vanilla pathfinding around water bodies, shoreline tiles curve around deep water or obstacles. The character often enters an $N$-tile cycle ($T_1 \to T_2 \to T_3 \to T_4 \to T_5 \to T_1 \dots$):
- **Window Limit Formula:** In any cyclic trajectory of period $N$, a sliding window of length $W$ contains at most $\lfloor W / N \rfloor$ visits to any single tile.
- **The Blind Spot:** With $W = 10$ and $N = 5$, each tile appears exactly $10 / 5 = 2$ times. A frequency threshold of 3 (`pos_frequency >= 3`) can **never** be satisfied, allowing the agent to oscillate infinitely without triggering cycle detection.

### 15.2 Dual-Layer Detection Engine
To guarantee detection of arbitrary polygonal cycles:
1. **Window Expansion:** Buffer length is expanded to $W = 24$ steps (capturing cycles up to length $N = 11$).
2. **Spatial Entropy / Subgraph Density Check:**
   $$\text{is\_oscillating} = (\text{pos\_frequency} \ge 3) \lor (\text{window\_len} \ge 10 \land \text{unique\_positions} \le 5)$$
   This checks the topological diameter of the trajectory: if 10 consecutive steps visit only $\le 5$ distinct coordinates, an oscillation loop is proven regardless of tile visit order.
3. **Engine-Side Autoexplore Interlock (`AIBrainPart.cs`):**
   ```csharp
   int uniquePositions = autoexplorePosHistory.Distinct().Count();
   bool isCycling = (repeatVisits >= 3) || (autoexplorePosHistory.Count >= 10 && uniquePositions <= 5);
   if (isCycling) {
       isZoneFullyExplored = true;
       return; // Yield control to Python driver for frontier escape
   }
   ```

### 15.3 Cycle Centroid Steering Physics
When an oscillation is detected, escaping cannot simply backtrack into recently traversed tiles:
1. **Frontier Escapes:** First check valid candidate moves $m$ where destination $(x + dx, y + dy) \notin \text{recent\_positions}$. If found, select the least-visited frontier tile.
2. **Centroid Steer Fallback:** If all immediate moves lie within recently visited territory (e.g. pinned along a curved shoreline), calculate the geometric centroid of recent positions:
   $$\bar{x} = \frac{1}{K} \sum_{i=1}^K x_i, \quad \bar{y} = \frac{1}{K} \sum_{i=1}^K y_i$$
   Shorelines wrap convexly around water or cliffs; the centroid points toward the center of the lake or obstacle. Moving to maximize Euclidean distance $(n_x - \bar{x})^2 + (n_y - \bar{y})^2$ steers the character away from the obstacle basin and outward onto open dry land.

---
*End of Engine Internals Manual.*
