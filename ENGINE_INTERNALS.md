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

### 3.3 Confirmation Dialog Interception (`Popup.ShowYesNo` & `ShowYesNoCancel`)
Many core mechanics prompt confirmation modals during player turns:
- **Rapid Advancement at Level 4/5:** `"Your genome enters an excited state! Would you like to spend 4 mutation points to buy a mutation before rapidly mutating?"`
- **Mutation Point Purchases:** `"Are you sure you want to spend 4 mutation points to buy a new mutation?"`
- **Skill Tree Progression:** Confirmations when unlocking high-tier disciplines.

`Popup.ShowYesNo` does **not** check `Popup.Suppress`. When unhandled, it blocks the main thread waiting for mouse clicks or Y/N keys.
**The Solution:** `AIPopupShowYesNoPatch` and `AIPopupShowYesNoCancelPatch` hook `XRL.UI.Popup.ShowYesNo` and `ShowYesNoCancel`. When the AI is active (`FlagFile` exists), the patch sets `__result = DialogResult.Yes`, invokes `callback?.Invoke(DialogResult.Yes)`, logs the action, and returns `false`, enabling completely autonomous headless progression.

---

## 4. UI Picker Interception Architecture (Direction, Target, GameObject & Options)

Whenever a player activates a directional ability, ranged weapon, or makes in-game choices, Qud's game loop calls modal picker classes:
1. `XRL.UI.PickDirection.ShowPicker(...)`
2. `XRL.UI.PickTarget.ShowPicker(...)` and `ShowFieldPicker(...)`
3. `XRL.UI.PickGameObject.ShowPicker(...)`
4. `XRL.UI.Popup.PickOption(...)` (and `ShowOptionList(...)`)

If unpatched, these methods spawn interactive cursors or selection menus on the screen and block until the user hits arrow keys, Enter, or Space.

### 4.1 Headless Picker Interception Patches
`AIBrainPart.cs` contains Harmony patches for all picker categories:
- **`AIPickDirectionPatch` (`PickDirection.ShowPicker`)**:
  - Checks if `PreferredDirection` or `PreferredTargetCell` is set by the incoming command.
  - If set, returns the direction string (`"N"`, `"S"`, `"E"`, `"W"`, etc.) immediately and sets `__result`, skipping the GUI.
  - If not set, infers the direction to the closest hostile enemy automatically.
- **`AIPickTargetPatch` (`PickTarget.ShowPicker` / `ShowFieldPicker`)**:
  - Returns `PreferredTargetCell` directly as `__result`.
- **`AIPickGameObjectPatch` (`PickGameObject.ShowPicker`)**:
  - Automatically selects `PreferredTargetObj`, strictly filtering out friendly pets and companions.
- **`AIPickOptionPatch` (`Popup.PickOption`)**:
  - Intercepts all menu and choice pickers (`PickOption` and `ShowOptionList`):
    1. **Mutation Acquisition:** When 3 random mutation choices are presented (via 4 MP purchase, Rapid Advancement, or Unstable Genome), evaluates the options against `AIPlayerTurnPatch.PreferredMutation` (sent by Python/Twitch) and the archetype's priority order (`MutationPriorities`). Automatically selects the highest-priority mutation.
    2. **Physical Advance:** When selecting which physical mutation to rapidly advance, picks the highest-priority physical mutation on the character.
    3. **Mutation Variants:** When a newly acquired mutation has cosmetic or physical variants (e.g., `BaseMutation.SelectVariant` for Quills, Horns, Wings), automatically selects option 0.
    4. **General Menus:** Falls back to `DefaultSelected` or option 0, invoking `OnResult` and setting `__result` to bypass any modal blocking.

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

### 11.4 Mutation Cap Mechanics & Spendability Invariants
- **Engine Mutation Cap Scaling:** In *Caves of Qud*, mutation ranks are hard-capped by character level or tier (`m.GetMutationCap()`). For instance, a Level 2 character has a mutation cap of 2.
- **The `m.CanLevel()` Engine Pitfall:** In vanilla Qud, `BaseMutation.CanLevel()` returns `true` for all standard levelable mutations (as opposed to non-levelable defects or static mutations like Sense Psychic), even when the mutation has already reached its cap!
- **The Infinite Turn-Passing Freeze:** If the driver issues `AUTOLEVEL_MUTATION:<Class>` or `AUTOLEVEL` while all mutations are at their cap:
  1. `AllocateMutation` checks `m.Level < m.GetMutationCap()`, rejects the upgrade, and spends no MP.
  2. The C# turn handler passes 1,000 energy units (`Pass`), ending the player's turn.
  3. The next turn, `mp` remains unspent, and the driver repeats the same failed command indefinitely.
- **The Headless Solution:**
  1. **Engine Export Invariant:** In `AIBrainPart.cs`, line 780:
     ```csharp
     bool canLvl = m.CanLevel() && (mLevel < mCap);
     ```
  2. **Driver MP Spendability Guard:** In `brain.py`:
     ```python
     can_level_any_mut = any(m.get("can_level", False) and m.get("level", 0) < m.get("cap", 99) for m in muts)
     can_spend_mp = (mp >= 4) or (mp > 0 and can_level_any_mut)
     has_points_to_spend = (ap > 0) or (sp >= 50) or can_spend_mp
     ```
     When MP is present but unspendable ($< 4$ MP and all mutations capped), the driver safely saves the MP for future level-ups without stalling the exploration pipeline.

---

## 12. Sustenance & Survival: Hunger Physics, Butchery, Camping & Cooking

### 12.1 Hunger Physics & Starvation Traps
- Managed by `XRL.World.Parts.Stomach`.
- Hunger levels: `Satisfied` $\rightarrow$ `Hungry` $\rightarrow$ `Famished`.
- **The Starvation Trap:** In vanilla Qud, resting while `Famished` prevents HP regeneration and accelerates starvation damage.
- **The Solution:** Sustenance is placed at **Step 2 of Phase A** in `brain.py`, strictly ahead of resting at Step 3.

### 12.1b Corpse drops and fire (verified from `Corpse.ProcessCorpseDrop` IL and blueprints, 2026-10-04)
- `Corpse` part fields: `CorpseChance`, `BurntCorpseChance`, `VaporizedCorpseChance` (each with a `...Blueprint` and `...RequiresBodyPart`). `ProcessCorpseDrop` compares `Physics.LastDamagedByType` with the strings `"Fire"`, `"Light"` and `"Vaporized"` and rolls the matching chance (`in100`). `[verified in code]` that these three strings are compared; the exact branch mapping (Fire/Light -> burnt, Vaporized -> vaporized) is read from the call order and is `[unverified]`. Lase is light/laser damage, which matches the human-reported "enemies reduced to ashes".
- Creatures drop a corpse only some of the time: Baboon `CorpseChance="40"`, Salthopper `8`; blueprint values seen range 0-25 and up. Not every kill leaves anything to butcher.
- `GameObject.GetPart(string)` exists (instance method returning the part object; signature read from the IL, `[verified in code]`), and `Corpse.CorpseChance` is a public field; the mod reads it by reflection (`CorpseChanceOf`) and exports it as `corpse_chance`. `[verified in code]`; that the value matches the engine's runtime roll is `[unverified]` until a game run.
- Burnt corpse = `Charred Corpse`: has a `Food` part ("It's charred.") but **no `Butcherable`**. A normal `Corpse` item has `Food Satiation="Meal" Gross="true" IllOnEat="true"` (edible but makes you ill).
- **Where the parts live:** the `Corpse` part is on the *living creature* (it spawns the corpse when the creature dies); `Butcherable` is on the dead *corpse item*. Testing `HasPart("Corpse")` therefore matches every live animal and pet, which made `corpses_nearby` wrong until T-1.13. `[verified in game blueprints]` Salthopper (creature) has `Corpse`; `Salthopper Corpse` has `Butcherable`.
- `Butcherable` (on the creature's corpse blueprint, e.g. `Salthopper Corpse` has `OnSuccess="@Salthopper Corpse"`) is what `AttemptButcher` needs, and the player needs the `CookingAndGathering_Butchery` skill.

### 12.1c Fire, flammability and campfires (verified from `Assembly-CSharp.dll` metadata and blueprint XML, 2026-10-04)
- **"Is it burning right now":** `GameObject.IsAflame()` (public, no parameters) and `Physics.IsAflame`; creatures get the `Burning` effect (`XRL.World.Effects.Burning`, has `GetBurningAmount`). `[verified in code]` that the members exist. That `IsAflame()` is true for a lit `Campfire` object is `[unverified]`, so the mod also treats any object with a `Campfire` part as fire.
- **Flammability data:** `Physics.FlameTemperature` (int field), `Physics.Temperature`, `Physics.WasAflame`, `Physics.InflamedBy`; `GameObject.MakeNonflammable()`, `GameObject.Temperature`, `TemperatureChange(...)`. Blueprint values seen: most things are `99999` (not flammable); flammable values include `250`, `350`, `600`, `1000`. The base `Physics` default is `[unverified]` (not set in the `Object`/`PhysicalObject` blueprints; read the `Physics` constructor if it matters).
- **Plants burn:** `Dogthorn Tree` inherits `Tree` > `Plant` > `PhysicalObject`; `Plant` sets `Physics Category="Plants"`. The mod uses `Physics.Category == "Plants"` as its "flammable terrain" test (T-1.12). `BasePlantWall` has `FlameTemperature=350`; oil, asphalt, honey and acid puddles also have `350`.
- **Campfire:** blueprint `Campfire` (`Inherits="Item"`): `Physics FlameTemperature="10000"`, `AnimatedMaterialFire`, `LightSource Lit Radius=3`, `Campfire ExtinguishBlueprint="Campfire Remains"`. `Campfire` has `CanExtinguish` and `FindExtinguishingPool`. A lit campfire next to plants set the area ablaze and killed a character (2026-10-04, human-reported).
- **Open (needed for HANDOFF issue 32, reacting to being on fire):** how the player extinguishes `Burning` (entering water? what do `Burning.ApplyTo`/`Remove` check?). Not yet inspected; do not guess.

### 12.1h Immobile wall creatures: the jilted lover (2026-10-06, `[verified in game blueprints]` + IL signature)
- `Jilted Lover` (`Creatures.xml`, inherits `MutatedVine`): `Brain Hostile="false" Wanders="false" Mobile="false" LivesOnWalls="true" MinKillRadius="1" MaxKillRadius="1"`, 5 HP, `Corpse CorpseChance="2"`, natural weapon `Lovers_Thorns` (1d4 plus a `Grabber` part), `tag PlacementHint OnWall`, `WallColor AsBackground` (it is drawn as a wall tile). It appears in `Flowerfields` and `DesertCanyon` creature tables and in groups.
- `GameObject.IsMobile()` exists (instance, no parameters, returns bool). The mod uses `Brain != null && !IsMobile()` as "cannot move". `[verified in code]` for the signature; that it returns false for this creature at runtime is `[unverified]`.

### 12.1g Extinguishing `Burning` (2026-10-06, `[verified in code]` for what exists; the numbers are `[unverified]`)
- `Burning` (an `Effect`) takes damage every turn (`TakeDamage`, damage text "from the fire", tiers "1-2" to "5-6" by `get_Temperature`; `GetBurningAmount`) and calls `RemoveEffect` once the object is no longer `IsAflame()`. It also pulls `Temperature` toward `get_AmbientTemperature`. So it ends by cooling, not by a timer.
- `LiquidVolume.ProcessExposure` calls `IsAflame`, `GetLiquidTemperature` and `TemperatureChange`, and there is a `GetLiquidCooling` method: contact with liquid cools the creature. Which liquid depths and how fast is `[unverified]`; the brain only uses deep water (`[SWIM: ...]` cells), the case it can recognise.
- `Campfire.Extinguish` and `TorchProperties` are about objects, not creatures. `Swimming` has nothing about temperature.

### 12.1f Swapping places with companions (verified from `Assembly-CSharp.dll` IL and blueprints, 2026-10-05)
- Moving into an ally is gated by `GameObject.CanBePositionSwapped()`. It returns false for the player; for objects with the `Noswap` property/tag; for immobile objects (`IsMobile`); under a restraining effect (an `Effect` type check); for a creature whose `Brain` is `MovingTo` a goal, or `IsFleeing`; and in some combat-object cases. `GameObject.ProcessMoveEvent` honours a `ForceSwap` parameter. `[verified in code]` that these checks exist; the exact boolean logic is `[unverified]`.
- **Observed in game (2026-10-05, human console): swapping with a recruited `horned chameleon and hired guard` works** (`MOVE_S` swapped places every time). My first guess that the swap was being refused was wrong; the hallway loop had another cause (HANDOFF issue 42). `[verified in game]`
- Only 12 blueprints carry `Noswap` (BaseUrchin, Jilted Lover, Prickler, Qudzu, Sprouting Orb, Livid Creeper, FungusPuffer, Irritable Palm, Red Death Dacca, Tongue Tyrant, TinkerTurret, Haddas). `Horned Chameleon` does **not**, so a recruited chameleon refusing to swap is due to its state (moving to a goal, an effect), not its blueprint. `[verified in game blueprints]`
- `GameObject` also has `DirectMoveTo`, `SystemMoveTo`, `TeleportTo`, `CellTeleport` (signatures not yet inspected).

### 11.5 Mutation pool and the purchase picker (verified from `Mutations.xml` and `Player.log`, 2026-10-06)
- `StreamingAssets/Base/Mutations.xml` defines 32 Physical and 27 Mental mutations (59 normal), 12 PhysicalDefects and 8 MentalDefects (20 defects), and 3 morphotypes (Chimera, Esper, Unstable Genome). Names are in `mutation_policy.py` and Test 68. `[verified in game data]`
- Buying a mutation (Rapid Advancement at level 4-5, or 4 MP) shows `Popup.ShowYesNo` ("Your genome enters an excited state! Would you like to spend 4 mutation points to buy a mutation before rapidly mutating?") and then `Popup.PickOption` with `Intro "Choose a mutation."` offering **three** options. Option text is `"<Name> - <description>"`; a second picker (variants, `Intro ""`) shows `"<Name> (1)"`. The mod's picker previously logged only the chosen option, never the other two. `[verified in game, Player.log 2026-10-06]`
- **Traversal facts (strings in `Assembly-CSharp.dll`, 2026-10-06; behaviour not tested):** the engine has pathing flags `PathAsBurrower` and `PathAsIfFlying`, a "burrowed" effect with `CommandEndBurrowing` ("Stop Burrowing"; "You cannot do that while burrowed"; "You cannot travel long distances while burrowed") and a `Flying` effect ("You begin flying!", described as "Isn't affected by terrain", "Can't be attacked in melee by non-flying creatures"). This is the basis for ranking Burrowing Claws and Wings as a traversal tier. The exact digging rules of Burrowing Claws and how flight is granted by Wings are `[unverified]`.
- **Burrowing Claws internals (member names in `Assembly-CSharp.dll`, 2026-10-06; behaviour not tested):** part `XRL.World.Parts.Mutation.BurrowingClaws` has methods `CheckDig`, `GetWallHitsRequired`, `GetWallBonusPenetration`, `GetWallBonusPercentage`, `GetClawsDamage`, `OnRegenerateDefaultEquipment` and fields `DigUpActivatedAbilityID`, `DigDownActivatedAbilityID`, `EnableActivatedAbilityID`, `PathAsBurrower`; it handles `CommandToggleBurrowingClaws`. The separate part `XRL.World.Parts.Digging` owns `CommandDig`. `XRL.World.Effects.Burrowed` has `MovePenalty`, `Emerge`, `EndAbilityID` ("Stop Burrowing"). Strings: "You cannot do that while burrowed", "You cannot travel long distances while burrowed", "You cannot dig on the world map". A character with the mutation showed the abilities `Burrowing Claws` (`CommandToggleBurrowingClaws`, a toggle) and `Dig` (`CommandDig`). See `docs/ABILITIES.md`.
- Whether the three options are drawn from all 59 (excluding owned ones) is `[unverified]`; defects were never observed offered.

### 12.1e Low-health warning popup (verified from `Assembly-CSharp.dll` IL, 2026-10-05)
- `XRLCore.PlayerTurn` shows a blocking "press space" popup, `Popup.ShowSpace("{{R|Your health has dropped below {{C|<N>%}}!}}", "Sounds/UI/ui_notification")`, when HP falls below a percentage threshold; `TerrainTravel.HandleLeavingCell` (world-map travel) uses the same string. The popup is **not** covered by `Popup.Suppress` in practice (the human saw it with the AI engaged), and the mod has no `ShowSpace` patch. `[verified in code]` for the call; the exact comparison is `[unverified]`.
- The threshold is the **static public int `XRL.Core.Globals.HPWarningThreshold`**. `Options.UpdateFlags` fills it from the game option `OptionDisplayHPWarning` (default string `"40%"`): `GetOption(...).TrimEnd('%')` then `Int32.TryParse`. `XRLCore.HPWarning` is a public instance **bool** ("warning shown" state), not the threshold. `[verified in code]`
- Mod fix (T-1.17): zero `Globals.HPWarningThreshold` every turn while `active.flag` exists (`UpdateFlags` would otherwise reset it to 40), restore the player's own value when the AI is paused. The in-game option `Display HP warning` is a manual alternative.

### 12.1d Food skill chain (from `skill_database.py`, a static copy of engine data; not re-verified against the DLL this session)
- `CookingAndGathering` 100 SP (no attribute minimum); `CookingAndGathering_Butchery` 50 SP, Intelligence 15; `CookingAndGathering_Harvestry` 50 SP, Intelligence 15; `CookingAndGathering_MealPreparation` 0 SP, Intelligence 15. Butchery and Harvestry have parent `CookingAndGathering`. A character cannot butcher without Butchery. `Survival` is 100 SP and its child `Survival_Camp` ("Make Camp") is 0 SP, Intelligence 15. `Tactics` 50 SP, `Tactics_Hurdle` 0 SP. `[unverified]` against the engine; exporting real eligibility from C# is HANDOFF Next step 8.

### 12.2 Engine Survival Mechanics
- **Butchering:** Animal corpses possess `Butcherable`. Calling `AttemptButcher(player)` yields raw meat and cooking ingredients.
- **Harvesting:** Wild plants possess `Harvestable`. Calling `AttemptHarvest(player)` harvests ingredients.
### 12.2 Engine Survival Mechanics
- **Butchering:** Animal corpses possess `Butcherable`. Calling `AttemptButcher(player)` yields raw meat and cooking ingredients without UI prompts.
- **Harvesting:** Wild plants possess `Harvestable`. Calling `AttemptHarvest(player)` harvests ingredients without UI prompts.
- **Camping & Cooking — The Interactive UI Trap:**
  - **The Campfire Menu Modal Trap:** In vanilla Qud, `Campfire.Cook()` is explicitly an interactive UI function. It calls `The.Core.ShowInventoryActionMenu()`, rendering a modal window with options:
    `[m] Whip up a meal.`
    `[i] Choose ingredients to cook with.`
    `[r] Cook from a recipe.`
    `[f] Preserve your fresh foods.`
    Calling `Campfire.Cook()` halts automated gameplay and blocks waiting for human keyboard input!
  - **The Make Camp Direction Prompt Trap:** Similarly, calling `Survival_Camp.AttemptCamp(player)` invokes `PickDirectionS("Make Camp")` and `ShowYesNoCancel()`, asking the player for directional input.
  - **The Programmatic / Headless Solution:**
    1. **Programmatic Camping:** Check if a campfire is already present nearby. If not, pick an empty adjacent cell (or player cell) and create the campfire directly:
       ```csharp
       Cell targetCell = player.CurrentCell.GetLocalAdjacentCells()?.FirstOrDefault(c => c != null && c.IsEmpty()) ?? player.CurrentCell;
       var campfire = targetCell.AddObject("Campfire");
       campfire?.SetIntProperty("PlayerCampfire", 1);
       campfire?.SetStringProperty("PointOfInterestKey", "PlayerCampfire");
       MessageQueue.AddPlayerMessage("{{G|You deploy a campfire.}}");
       ```
    2. **Programmatic Cooking:**
       - Consume 1 ingredient from inventory: `if (ingredient.Count > 1) ingredient.Count--; else ingredient.Destroy();`.
         > [!NOTE]
         > In Caves of Qud's `GameObject`, `SplitFromStack()` takes 0 arguments (calling `SplitFromStack(1, player)` causes `CS1501`). Decrementing `Count` directly or calling `Destroy()` when `Count <= 1` is the cleanest and most robust method.
       - Clear hunger & reset stomach counters: `stomach.ClearHunger(); stomach.ResetCookingCounter();`.
       - Silently notify campfire without opening menus: `campPart.AfterCooked();`.
       - Log message: `MessageQueue.AddPlayerMessage("{{G|You whip up a simple meal at the campfire and satisfy your hunger.}}");`.
       - **Strict Rule:** NEVER call `Campfire.Cook()` or `Survival_Camp.AttemptCamp()`.
- **Stomach API:** Call `player.GetPart<Stomach>()?.ClearHunger()`.
  > [!IMPORTANT]
  > In modern Caves of Qud, `player.pStomach` does **not** exist on `GameObject` (causes `CS1061`). Always use `player.GetPart<Stomach>()`.
- **Direct Eating:** `Event.New("Eat", "Eater", player)` consumes packaged food from inventory.
- **Food Telemetry:** Packaged rations may have either the `Food` part or the `PreparedCookingIngredient` part (e.g. jerky, dried fruit, starapple wafers). AIBrainPart checks `item.HasPart<Food>() || item.HasPart<PreparedCookingIngredient>()`.
- **Mutation API Deprecation:**
  - In `BaseMutation`, the property `m.DisplayName` is obsolete (`CS0618`). Modern Qud requires calling `m.GetDisplayName()`.

### 11.4 The 4 MP New Mutation Mechanic & Headless Progression
- **Mechanic Overview:** Mutated Humans gain 1 Mutation Point (MP) per level. Existing mutations have rank caps based on character level (`player.Stat("Level") / 2 + 1`). At low levels, core mutations hit their cap quickly (e.g. Rank 3 cap at Level 4), leaving MP to accumulate.
- **The Level 4 Milestone:** At Level 4 (or upon accumulating 4 MP), a mutant can unlock an entirely new mutation ability for 4 MP. In addition, Rapid Advancement triggers on certain levels (Level 4/5 for Mutants/Chimeras), prompting `Popup.ShowYesNo` ("Your genome enters an excited state! Would you like to spend 4 mutation points to buy a mutation before rapidly mutating?").
- **Headless Execution Architecture:**
  - `brain.py` checks `can_spend_mp = (mp > 0 and can_level_any_mut) or (mp >= 4)`. When `mp >= 4`, `build_templates.get_mutation_allocation_recommendation` evaluates missing core archetype mutations and proposes `AUTOLEVEL_BUY_MUTATION:{preferred}`.
  - In `AIBrainPart.cs`, `BuyNewMutation(player, target)` calls `Qud.API.MutationsAPI.BuyRandomMutation(player, Cost: 4, Confirm: false, MutationTerm: null)`.
  - When the engine generates the 3 random mutation choices via `XRL.UI.StatusScreen.BuyRandomMutation`, it invokes `Popup.PickOption`.
  - `AIPickOptionPatch` intercepts `Popup.PickOption`, matches against `PreferredMutation` or archetype priority doctrines, selects the optimal choice, and returns `false`.
  - If the chosen mutation has variants (e.g., Quills, Horns), `BaseMutation.SelectVariant` calls `Popup.PickOption`, which `AIPickOptionPatch` automatically resolves to variant 0.
  - `AIPopupShowYesNoPatch` automatically confirms YES to Rapid Advancement and mutation confirmation dialogs, preventing any modal screen halts during 24/7 autonomous Twitch streams.

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

### 14.5 "Unexplored" is not "explorable" (verified in code and live state, 2026-10-05)
- In `state.json`, `unexplored_cells`, `nearest_unexplored_*` and `unexplored_centroid_*` are computed over every cell with `Cell.Explored == false`. In caves and dungeons most of those are solid rock behind revealed walls and can never be revealed (the level-5 hallway had 1704 of them; from (27,4) the "nearest unexplored" cell was (25,2), behind rock; the centroid (40,11) lay inside rock). They say nothing about reachability. Use `frontier_targets` (T-1.18), which filters explored walkable cells that border unexplored cells through `AutoAct.TryFindPathStep`.
- `Cell.Explored` (property), `Cell.IsPassable(GameObject, bool)`, `Zone.ZoneID` (property) and `Zone.Width/Height` (fields) exist in `Assembly-CSharp.dll`. `[verified in code]`. Whether `TryFindPathStep` routes through deep water (swimming) is `[unverified]`; the lake episode suggests `TryFindEdgeStep` does.

### 14.6 The engine pathfinder routes through breakable trees (inferred 2026-10-05; `[unverified]` for the exact rule)
- `BasePlantWall` carries the part `ShouldAttackToReachTarget` `[verified in game blueprints]`; frontier targets and `NAVIGATE_TO_CELL` steps repeatedly led into cells holding a `SolidTree` (`Solid=true`, `Occluding=true`, 25 inherited hit points) and the step then failed (trace t783-812). The mod now attacks such blockers (`TryBreakPathObstacle`). Whether `AutoAct.TryFindPathStep` deliberately plans through them or only fails to treat them as walls is not established.

### 14.7 Activated abilities: registry and AI roles (2026-10-06)
- Every activated ability the game can give is registered by a part calling `AddActivatedAbility` / `AddMyActivatedAbility`; the string constants in that method give the display name, the `Command*` string and the category. 145 such abilities were extracted into `data/abilities.json` by `tools/build_ability_registry.py`. `[verified in code @this branch]` The command is a literal in most cases; `command_source: derived` marks the few built at run time (guessed as "Command" + name, not confirmed).
- The engine has typed AI role events `AIGet{Offensive,Defensive,Movement,Passive,Retreat}AbilityListEvent`; the `Command*` strings in their `HandleEvent` methods give each ability's role (`engine_roles`). `[verified in code]`
- Real commands that differ from their names: `CommandMassiveCharge` is Horns' "Triple Horn", `CommandLifeDrain` is Syphon Vim, `CommandCryokinesis` is "Chill", `CommandPyrokinesis` is "Toast", Teleportation is `CommandTeleport`, the Phasing toggle is `CommandTogglePhase` (`CommandPhaseIn`/`CommandPhaseOut` are separate), Decapitate is a toggle (`CommandToggleDecapitate`). `[verified in game data]`
- No activated ability named Chain Fire exists; Disarming Shot is a passive Pistol skill; Cleave, Bludgeon and Backhand are not activated abilities. `[verified in game data]`

### 14.8 Burrowing Claws (2026-10-06, `[verified in code strings]` unless marked)
- `BurrowingClaws` registers `CommandToggleBurrowingClaws`, `CommandDigUp`, `CommandDigDown`. The toggle's state is read with `IsMyActivatedAbilityToggledOn` and drives a `Digging` event (the digging mode that lets the claws destroy walls). Level text: walls are destroyed "after N penetrating hits".
- `CommandDigDown`/`CommandDigUp` ("Excavate down/up") create `StairsDown`/`StairsUp` objects ("a passage up"). Refused with hostiles nearby ("You can't excavate with hostiles nearby.") and under the sky ("You can't excavate the sky!").
- The `Burrowed` effect ("Traveling underground", `CommandEndBurrowing`, move-speed shift, "You cannot travel long distances while burrowed.") is a separate state. The live character had the toggle ON and travelled normally, so the toggle is not that effect. `[verified in game state 2026-10-06]`
- Observed: with the toggle on, `NAVIGATE_TO_CELL` turns that leave the position unchanged for 2-3 turns (94 in one run) while no `ATTACK_WALL` was issued, i.e. the engine digging on its route (`PathAsBurrower`). `[verified in game 2026-10-06]` by the message log: nine consecutive "You hit (x1/x2) for 50 damage with your claw!" lines, then "The shale is destroyed!". One wall took about 9 hits at claws level 3.
- Whether the engine refuses to dig owned or settlement walls is `[unknown]`; the policy therefore turns the claws off in towns (R7).

### 14.9 Autoexplore objects, chests, autoget and death drops (2026-10-06, `[verified in code]`; see docs/tasks/R-2-loot-and-chests-research.md)
- The engine's autoexplore treats unowned, not-yet-explored containers as goals (`GameObject.ShouldAutoexploreAsChest`) and runs the open-and-take half itself in `ActionManager.RunSegment` (`FindAutoexploreObjectToOpen`, `FindAutoexploreObjectToProcess`, `ShouldTakeAll`, `TakeObject`). Objects name their adjacent action through `AutoexploreObjectEvent` (`Action`, `Command`, `AllowRetry`, `AutogetOnlyMode`).
- `GameObject.CanAutoget` needs a takeable, real, visible, non-temporary object without `NoAutoget` that is not `DroppedByPlayer`.
- Death drops: `Inventory` handles `DropOnDeath`/`GetDropInventory`, `Body` honours `NoDropOnDeath`. Where items land and which ones drop is `[unverified]`.
- The mod only takes autoexplore's movement step and suppresses objects it cannot step into (int properties `Autoexplored`, `AutoexploreSuppressed`, `AutoexploreSuppression`); that is the likely reason chests are never opened. `[inferred]`

### 14.10 Items, equipping and dropping (2026-10-06, `[verified in code]` unless marked)
- `Qud.API.EquipmentAPI` (public static): `DropObject(GameObject)` (fires the `CommandDropObject` inventory action), `EquipObject(equipper, item, BodyPart)`, `EquipObjectToPlayer`, `UnequipObject`, `ForceUnequipObject`, `GetPlayerCurrentCarryWeight()`, `GetPlayerMaxCarryWeight()`. `GameObject` also has `AutoEquip(GameObject GO, bool Forced, bool ForceHeld, bool Silent)`, `EquipObject(item, string slot or BodyPart, silent, energy)`, `ForceEquipObject`, `TryUnequip`, `GetInventory()`, `GetEquippedObjects()`, `GetCarriedWeight()`, `GetMaxCarriedWeight()`, `Understood()` (identified), `SplitStack(count, owner, noRemove)`, `RemoveFromContext(IEvent)`, `Cell.AddObject(GameObject, ...)`.
- The player's drop (`Inventory` handling of `CommandDropObject`) asks "How many do you want to drop?" through a number popup for a stack of more than one, then `SplitStack`, the `BeginDrop`/`BeginBeingDropped` events, a `PerformDrop` event, and sets or removes the int property `DroppedByPlayer`. The popup is why the mod drops whole items itself. `GameObject.CanAutoget` is false for `DroppedByPlayer` objects, so a dropped item is not picked up again. The mod's manual drop (remove from the pack, add to the cell, set `DroppedByPlayer`) is `[unverified in game]`.
- `GameObject.Weight` as exported by the mod is the STACK's total weight: a stack of 12 torches reports weight 12, 2 goat jerky report 0, witchwood bark x3 reports 3. `[verified in game 2026-10-06]`. The brain divides by the count to get a per-unit weight. (`GetWeight()` returns a double; not compared.)
- Every concrete item inherits a default improvised `MeleeWeapon` part from `Item`; real weapons are recognised by ancestry (`MeleeWeapon`, `MissileWeapon`, `Armor`, `Shield`, `Grenade`). `Physics.Category` is the game's own inventory category. Weapon skills in the data: Axe, Cudgel, LongBlades, ShortBlades, Whip, Chain (melee) and Pistol, Rifle, HeavyWeapons (firearms and bows). Armor slots (`WornOn`): Body, Back, Arm, Head, Face, Feet, Hands, Floating Nearby, Roots, Tread; shields Hand or Arm.
- `EquipStatBoost.Boosts` carries stat and defence boosts as `Stat:value;Stat:value` (for example `Strength:1;Agility:1`, `DV:4;MA:-1`, `Speed:30`). Teleporting gear (recoilers) has a part whose name contains `Teleport` (19 loot items). Placed unique items carry `StaticObjectsTable:` tags (4 loot items, the Great Machine pieces).
- Items that matter beyond their stats `[verified in game data]`: 46 blueprints carry `AddsRep` (faction reputation trophies such as Girshling Fangs, with a `Faction` and a `Value`); `CompleteQuestOnTaken` (2), `QuestStepFinisher` (1), `QuestStarter` (1), `FactionDeed` (2) and `SultanMask` (6) mark quest and relic items. The catalog flags them `protect` (41 loot items); the junk logic never drops them.

### 14.11 Navigation weights and avoiding things (2026-10-06, `[verified in code]`; the effect in game is `[unverified]`)
- Path costs come from two events: `GetNavigationWeightEvent` (the cost of a cell, asked of the objects in it) and `GetAdjacentNavigationWeightEvent` (the cost an object adds to the cells next to it). Handlers found: `Combat` (hostile creatures), `Physics` (walls, `WallDigNavigationWeight`, `AutoexploreNavigationWeight`), `LiquidVolume`, the gases, `Hidden`, mines, stairs, `Sticky`, `SlowDangerousMovement`, `Impaler`, and two generic parts: `AvoidMovingOnto` (field `Weight`, `RespectPhase`; walls use `Weight="40"`) and `AvoidMovingNearby` (the same fields, and it also answers the adjacent event). `MinWeight(n)` raises a cell's cost to at least n, so weights do not add up. `Cell.FlushNavigationCache()` (public) clears the cached costs.
- A jilted lover (`Brain Hostile="false"`, `Mobile="false"`, kill radius 1) is not hostile to the pathfinder, so the engine walks past it; the mod now attaches `AvoidMovingNearby` to immobile hostiles so it does not.

### 14.12 Proselytize on an immobile hostile (2026-10-07, `[verified in code]`; the success rate in game is `[unverified]`)
- `Persuasion_Proselytize.AttemptProselytization` refuses only for: no tongue, frozen, `HasCopyRelationship`/original player body, no telepathic contact when tongueless, an existing `Proselytized` effect, and `GameObject.CheckInfluence` (fires `CanBeInfluenced`, which only the `CannotBeInfluenced` part answers). It then rolls a mental attack (`PerformMentalAttack`, `1d8-6`, Level and Ego based) and costs the turn plus the cooldown. Nothing in it checks mobility.
- The `Jilted Lover` / `MutatedVine` / `MutatedPlant` blueprints do NOT carry `CannotBeInfluenced` (only the Wraith-Knight Templar, templar mechs and vehicle golems in Creatures.xml do), so Proselytize on a jilted lover is a legal attempt: a mental-attack dice roll, not a guaranteed waste like Intimidate or Teleport Other. `Proselytized.Apply` only takes effect for blueprints where `GameObject.SupportsFollower` is true (a per-blueprint flag; its source was not traced), so whether a recruited lover would stay put as an ally is `[unverified]`.
- Trace evidence from older runs (turns 734 and 759 of the second run, before the immobile fix): the outcome of the two attempts is not visible in the trace.

### 14.13 Sleeping creatures: why "snoring", and how to wake one (2026-10-07, `[verified in code]`; the in-game menu path is `[unverified]`)
- A sleeping creature carries the `Asleep` effect (`XRL.World.Effects.Asleep`, display "asleep"). The "X snores loudly" message comes from `Asleep.GetSleepMessage` (the strings `snore` and ` loudly.`). The effect handles `IsConversationallyResponsiveEvent`, so a sleeper does not talk; there is nothing to say to him until he is awake.
- The effect adds an action to the creature's interaction menu in `HandleEvent(GetInventoryActionsEvent)`: display `Wake`, key `wake`, command `WakeSleeper`, offered only when `CanWake` is true. `CanWake` is true for ordinary creatures; for robots in "sleep mode" it also needs the `Tinkering_Repair` or `Tinkering_Tinker1` skill ("You can't figure out how to wake ...").
- Performing it (`HandleEvent(InventoryActionEvent)`, command `WakeSleeper`) checks `CanWake` and `CheckFrozen`, plays `sfx_interact_creaturesleeping_wake`, prints "You gently shake X awake.", removes the effect and spends the actor's energy (`UseEnergy`). No opinion or hostility call appears in that handler, so it is the peaceful way. `[verified in code]` for the handler's call list; the opinion effect on the NPC afterwards is `[unverified]`.
- Damage also wakes a sleeper ("Will wake up dazed if damage is taken"): never the way to do it for a peaceful NPC (rule R7).
- Hostile or noisy neighbours were not traced: whether sleepers wake on their own (`TurnsAsleep`, `quicksleep` fields exist) was not read.

### 14.15 Quests (2026-10-07, first pass; full notes in docs/tasks/R-3-quests-research.md)
- `[data]` `Quests.xml` holds 28 authored quests (84 steps) started and finished by `StartQuest=`/`CompleteQuest` hooks in `Conversations.xml`. `[code and data]` Procedural village quests come from `DynamicQuestFactory` and the `Dynamic Village Quests` population (FindASite, FindASpecificItem, InteractWithAnObject templates), fabricated at world generation, offered by villagers with the property `GivesDynamicQuest`, stored in `DynamicQuestsGameState`. `[data and code]` The inherited conversation choice `AskForWork` ("I'm looking for work.", `IfQuestSignpost`) names the quest givers and their direction. Reading the player's quest log from the mod was not tried `[unverified]`.

### 14.16 XP curve and quest XP (2026-10-07, `[verified in code]`; the curve fits the live character)
- `Leveler.GetXPForLevel(level)` returns 0 for level 1 and otherwise `floor(15 x level^3) + 100`: levels 2 to 10 need 220, 505, 1,060, 1,975, 3,340, 5,245, 7,780, 11,035 and 15,100 XP. A level 4 character at 1,900 XP fits. Quest steps in `Quests.xml` carry `XP=` values; see docs/tasks/R-3-quests-research.md for the table (the Joppa watervine quest pays 1,000, the Six Day Stilt pilgrimage 1,500 for one step).

### 14.17 Water Ritual options by speaker (2026-10-07, first pass: `[verified in code]` for the rules, `[inferred]` for which Joppa NPC offers what; the human is checking in game)
- All options are inherited from `BaseConversation`; no conversation file overrides them (`Conversations.xml`). The ritual choice exists only for speakers with the `GivesRep` part; the first ritual awards reputation to the speaker's faction (and moves the factions that love or hate it, which is how the Children of Mamon fell). Each later option spends reputation (`GetReputationCost`, shown as "[N reputation]") and some also spend skill points.
- Options and what decides them (`WaterRitual*` parts): `BuyItem` (a gift: `Source="Valued"` is the speaker's most valuable item, `GetMostValuableItem`; `Source="Faction"` a faction item); `LearnSkill` (a skill the speaker sells, gated by the xtag `SellSkill`, costs reputation AND skill points: "You don't have enough skill points."); `GainMutation` and `RandomMutation` (mutations the speaker sells); `BuySecret`/`SellSecret` (gossip, a sultan's life, a location: the dromad caravan came from this; `numSecrets`, `NoSecrets`); `TinkeringRecipe` and `CookingRecipe` (`numRecipes`, `SellCookingRecipe`, cost `SellCookingRecipeCost`); `JoinParty` (blocked by the xtag `NoJoin`, and by level); `FungusColonize`, `HermitOath`.
- Joppa NPC blueprints in `Creatures.xml` `[data]`: Irudad (blueprint `ElderBob`, `GivesRep`, Joppa), Mehmet (`GivesRep`, Joppa), Warden Yrame (`GivesRep`, Wardens; xtag `SellSkill="false"`; items Chain Mail, Vibro Blade, Waterskin, Leather Boots), Warden Esthers (`GivesRep`, Wardens; `SellSkill="Shield"`; items Carbide Plate Armor, Carbide Shield, Cudgel4, Carbide Boots and Gauntlets, Scarlet Shawl). Argyve, Nima Ruda and Tam have no `GivesRep` of their own `[inferred: not checked through every ancestor]`, so they probably offer Trade only. Catalog values: Vibro Blade 300, Carbide Plate Armor 190 (45 lb, AV 5, DV -5), Carbide Boots and Gauntlets 150 each, Carbide Shield 50, Cudgel4 80, Chain Mail 25, Spectacles 35. The "valued item" rule (most valuable carried item) is `[inferred]` from the method name; where each Warden lives was not read.

- **Seen in game 2026-10-07 (human, a level 1 character) `[verified in game]`:** Mehmet: Harvestry skill for -50 reputation, the cooking recipe Apple Matz. Elder Irudad: Harvestry -50, Apple Matz -50, join -536. Warden Yrame: join -488, a secret -50 (no skill, matching `SellSkill="false"`, and no gift line, so the "most valuable item" gift rule above is NOT confirmed). Argyve: no ritual, three "..." prompts and then the quest "Fetch Argyve a Knickknack".
- **Join cost formula `[verified in code and by both data points]`:** `WaterRitualJoinParty.Awake` sets the cost to `max(50, 200 + 12 x (speaker level - player level))`, where 12 is `int(50 x 0.25)` (the static field after REPUTATION_LOVED holds 50). With the player at level 1: Yrame (level 25) = 488, Irudad (level 29) = 536, as seen. Each level the player gains lowers it by 12; e.g. at level 5 Yrame costs 440, at level 10 380; Esthers (level 30) costs 548 at level 1. Costs are paid from the speaker's faction reputation. The reputation a ritual awards is scaled by a ritual `Performance` value times 100 (`WaterRitual.ModifyReputation`); the amounts are not decoded (Kuyukas gave 125 with "an additional 100" shown as still available).

- **Screenshots of a fresh level 1 character's Joppa rituals, 2026-10-07 `[verified in game]`:** every ritual's primary award was +125 with the speaker's own faction. In order: Mehmet: Joppa -140 to -15; also "because they dislike Mehmet" unshelled reptiles -50 (to -525) and goatfolk -50 (to -525), "despise" svardym -100 (to -575). Warden Yrame: Wardens -150 to -25; "admire" Joppa +100 (to 85); "despise" the villagers of Kiwan -100 (to -100). Elder Irudad: Joppa 85 to 210; "despise" trees -100 (to -400). The side effects are `WaterRitualAttitudeAward` steps: admire +100, dislike -50, despise -100 (decoded names `Friend`/`Dislike`/`Hate`); the game's own text says named ritual speakers get dynamic faction relationships, so who each NPC's friends and enemies are is generated per world `[from game text]`, while the NPCs, their skills and items are authored (static).
- **Quests seen from conversation `[verified in game]`:** the watervine farmer and Mechanimist convert ("Wanderer and friend! Have you journeyed yet to the Stilt, and seen the Sacred Well?") gave "an odd trinket" and the quest "O Glorious Shekhinah!" (1,500 XP, level 3 in `Quests.xml`). Argyve asked for "a knickknack from one of the caves" and, with the trinket already in the pack, the log showed "You have received a new quest, Fetch Argyve a Knickknack!" and in the same moment "You have finished the step, Find a Knickknack" (75 XP remain for returning it). Whether one trinket serves both quests, or the first hand-in consumes it, was not observed `[unverified]`.

### 14.18 The underground biome under each parasang (2026-10-07, `[verified in game data]`, `Worlds.xml`)
- Each world-map terrain defines its own strata below the surface, so stairs (or a dug passage) lead to the biome of the terrain above: watervine "subterranean salt marsh" (levels 11 to 15), desert canyon "subterranean desert canyon" (11 to 15), salt dunes, hills, mountains, jungle, deep jungle, fungal, flower fields, banana grove, water ("subterranean river"), reef, ruins and baroque ruins (down to 30 and 40); the default is generic "subterranean caves" down to level 49. Special cells replace it: Joppa and the Joppa ruins have a three-level "waterlogged tunnel" (11 to 13, with stairs both ways), Rust Wells have Rustwells 1 to 3, Red Rock has Redrock 1 to 3 plus a bottom level at 14 (the girshlings), Grit Gate "lower tunnels" (11 to 29), Golgotha "trash chutes" and the Cloaca, the Asphalt Mines shafts, the Spindle's catacombs.
- Only the zones named by a cell's special definition get the special strata (Red Rock's dungeon is under its middle zone, `x=1,y=1`); the other zones of the same cell inherit the terrain's ordinary caves. **The underground river road `[verified in game data: the builders line up]`:** Joppa's cell (11,22) has a three-level "waterlogged tunnel" in its middle zone (levels 11 to 13, `Joppa Tunnel`, stairs up and down) and at level 14 the zone (1,1) starts a river (`RiverStartMouth`, `RiverNorthMouth`, stairs up) beside the zone (1,0) with north and south mouths; the cell between, `TerrainJoppaRedrockChannel` (11,21), has level-14 river zones (1,0), (1,1) and (1,2), each with north and south mouths; Red Rock's cell (11,20) has at level 14 the zone (1,2) with the same mouths (a hall zone, `Waterlogged Tunnel Connection`) beside the zone (1,1) that is `Bottom Redrock`, the girshlings. So a level-14 river corridor runs from under Joppa north to the Red Rock bottom, about 7 zone crossings; the stairs down from Joppa's tunnel levels are the way onto it (where Joppa's entrance is was not read `[unverified]`). Creatures `[data]`: Joppa Tunnel levels (11 to 13): cave spiders, bats, bears (15 percent), snapjaw parties, giant centipedes, chameleons, amoebas; the level-14 `Waterlogged Tunnel` zones: 2 to 3 knollworms and 1 to 2 plated knollworms (always), eyeless crabs (always), 2 to 8 giant centipedes, albino apes and quillipedes (25 percent each); the bottom zone adds a caver corpse.
- `CommandDigDown` (Burrowing Claws) makes a `StairsDown` and is refused under the sky and with hostiles near (14.10 area); digging therefore makes a way into this underground biome from almost any surface zone, but it does not change what is generated there.

### 14.19 Reading the player's quest log from the mod (2026-10-07, `[verified in game]`)
- `The.Game` is an `XRLGame`; its public instance fields `Quests` and `FinishedQuests` are both `StringMap<T>`, a game collection that is enumerable but throws `NotSupportedException` from the non-generic `IDictionary.Values` and `.Keys`. Plain enumeration works (each item is a `KeyValuePair`-like pair, unwrapped by reflecting its `Key` and `Value`). Quest members read by reflection: `ID`, `Name`, `Level`, `Finished`, `QuestGiverName`, `QuestGiverLocationName`, `QuestGiverLocationZoneID`, `StepsByID`; step members: `Name`, `Text`, `XP`, `Flags` (with the `FLAG_FINISHED`, `FLAG_FAILED`, `FLAG_OPTIONAL`, `FLAG_HIDDEN` constants). Seen live: the watervine quest with `Travel to Red Rock` finished and Argyve's knickknack quest, giver zone `JoppaWorld.11.22.1.1.10`.

### 14.20 How Proselytize decides (2026-10-08, `[verified in code]` unless marked)
- The game's own ability text (`ActivatedAbilities.xml`): "You persuade an intelligent creature to join you. **Ego + character level attack vs. MA + character level.**" Skill cost 300 SP, minimum Ego 23 (`Skills.xml`); cooldown 25 (`Persuasion_Proselytize` static constructor).
- `Persuasion_Proselytize.AttemptProselytization` gates (before any energy is spent): you need a tongue and the target must not be frozen, not a copy or your own original body, not already proselytized (a prompt asks when it is already a follower), and `GameObject.CheckInfluence` must pass (it fires `CanBeInfluenced`; only the `CannotBeInfluenced` part answers, e.g. templar robots and golems). Hostility is not a gate: hostile and neutral creatures are both valid.
- The attack: `Mental.PerformAttack(handler, you, target, null, "Proselytize", "1d8-6", type 2, ..., AttackModifier = your Ego modifier, DefenseModifier = penalty)`; it fails at once when the target has no `MA` stat (not a mental creature). The target's difficulty is its mental armor (`Stats.GetCombatMA`) plus the penalty, where **penalty = max(target level - your level, 0)**, +1 if the target already has the `Proselytized` effect, +1 if it has `Rebuked`, plus the `Beguiled.LevelApplied` if it is `Beguiled`. So a target at or below your level adds nothing, each level above adds one, and your Ego modifier (Ego 22 gives +3) is the bonus. The exact success probability was not decoded `[unverified]`: it also depends on the target's MA, which the mod does not export.
- On success the `Proselytized` effect makes it a follower, but only for blueprints where `GameObject.SupportsFollower` is true (the follower mechanics of every creature were not checked). On failure the message is "unconvinced by your pleas"; the turn (1000 energy) and the cooldown are spent either way.
- In game `[verified in logs]`: `ability_stats.json` records 26 Proselytize attempts across runs and no outcomes; companions seen recruited so far include knollworms, a giant dragonfly, goats, an amoeba and Joppa's cat Ctesiphus.

### 14.21 The wish mechanic (2026-10-08, `[verified in code]` for what is stated; the effect of most commands was not read)
- Keys `[verified in Commands.xml]`: `CmdWish` is Ctrl+W (a text prompt, "Your wish is my command!") and `CmdWishMenu` is Shift+W; `CmdXP` ("Gain 250,000 XP"), `CmdExplore` ("Reveal the whole map") and noclip are also in the Debug category. The player-turn handler dispatches them with no visible gate.
- Code: `XRL.Wish.WishManager.AskWish()` asks for a string and calls `XRL.World.Capabilities.Wishing.HandleWish(The.Player, text)`; both `HandleWish` methods are `public static`. `Wishing.HandleWish(GameObject who, string wish)` is one very large method (about 57 KB of IL) that matches the text against many names; `WishManager.HandleWish(string)` is a second, reflection-based dispatcher for `[WishCommand]` methods. So a mod could call `Wishing.HandleWish(The.Player, "spawn:SecurityTurret")` directly.
- `WishCommands.xml` (the Shift+W menu) documents only 14, among them `item:<Blueprint>` (spawn an item), `xp:25000`, `godmode` (toggle), `calm` (calm creatures), `swap`, `fastforwardtomb`, `checkpointon` and plain `wish`.
- **Verified in game 2026-10-08 (human):** typing just the blueprint name at the prompt, `SecurityTurret`, spawned one musket turret. The prefix form `spawn:SecurityTurret` did **not** work: `Player.log` shows `Unknown blueprint ... SecurityTurret` and `failed to generate object from blueprint SecurityTurret` from `Cell.AddObject` called by `Wishing.HandleWish` (twice). My reading of the IL that `spawn:` loops 16 times placing creatures in random cells of the zone is `[inferred; the attempt failed]`; it probably expects something other than a creature blueprint (a population table name?). The prompt takes one line: pasting two lines at once did nothing useful.
- Names present in the handler (so recognised): `spawn:`, `item:`, `xp:`, `xpmul:`, `goto:`, `go:`, `godown:`, `testhero`, `testhero:`, `clearcooldowns`, `calm`, `godmode`, `hungry`, `famished`, `thirsty`, `ill`, `skillpoints`, `gainmp`, `statbonus:`, `statpenalty:`, `stat:`, `effect:`, `zonetier`, `clearzone`, `reveal...`, `startquest:`, `completequest:`, `finishqueststep:`, `finishallquests`, `factionrep`, `reputation`, `opinion:`, `restock`, `fast`, `slow`, `die`, `ignoreme`, `shove`, `explodingpalm` and many diagnostic tests. What each does, and the exact argument syntax, was not read: the human reports results.
- Consequences for the project: wishes are fast, repeatable test set-up (a turret nest, a Very Tough creature next to you, a level, a quest state, an item) but they make a run an experiment, so its death must not feed the lessons: the Lab tab logs lab runs, and the Memory tab can archive what a wished run leaves behind. A mod command that fires a wish for the console would need the same care as every command (R4: a command that spends no energy makes the game re-export the same state) and a lab-only gate; not built (BACKLOG B13, later stages).

### 14.22 A turret is not "alive" (2026-10-08, `[verified in game]`)
- The mod's one-line diagnostic for a wished musket turret in game: `[QudAI Turret] SecurityTurret: HasTag=True GetTag=True byName=True IsAlive=False hitpoints=5`. So `GameObject.HasTag("Turret")` works (the tag and its value are present), but **`GameObject.IsAlive` is false for a turret that has 5 hit points**. Any code that starts with `if (!obj.IsAlive) return false;` silently ignores turrets, and probably other constructs (robots, machines): the mod's `CheckIsEnemy` did, so a turret was exported `is_enemy: false` and never selected as a target (Gen 22 to 25). Use `hitpoints > 0` for "can still be shot".
- **What `IsAlive` is `[verified in code, decoded from the IL]`:** `(IsCreature || HasTagOrProperty("LivePlant") || HasTagOrProperty("LiveFungus") || HasTagOrProperty("LiveAnimal")) && IsOrganic`. So it means organic life: every inorganic creature (turrets, robots, golems and other constructs) is "not alive" while having hit points, a brain and attacks. `GameObject.hitpoints > 0` is the test for "still there and can be hit".
- `ConversationScript` is not a mark of a person: 814 of the 845 concrete creatures in the game data have one (a species default such as Goats, Insects, Snapjaw, Spiders). The parts that do mark someone who serves are `GivesRep` (reputation NPCs, the water ritual) and `GenericInventoryRestocker` (merchants and village trades), about 120 creatures; quest givers carry the properties `GivesDynamicQuest`, `NamedVillager` and `ParticipantVillager` (14.15).
- Ability targeting `USE_ABILITY:<Cmd>:<DIR>@x,y` aimed at the turret's cell worked: `Executing CommandLase towards 'W' at cell 61,4 on target {{c|musket turret}}` and a level 1 Esper's Lase killed it (human, 2026-10-08).

### 14.14 Trade prices: the trade performance formula (2026-10-07, `[verified in code]`, and it reproduces the human's screenshot exactly `[verified in game]`)
- Trade is priced in drams of fresh water. `TradeUI.GetMultiplier(item)` is 1.0 for currency items (`IsCurrency`) and otherwise the static `TradeUI.Performance`, set in `ShowTradeScreen` from `GetTradePerformanceEvent.GetFor(actor, trader)`. A vendor PAYS `base Commerce.Value x Performance` and CHARGES `value / Performance` (so a round trip keeps Performance squared).
- `GetTradePerformanceEvent.GetFor` returns `clamp(factor x (0.35 + 0.07 x (EgoMod + linear)), 0.05, 0.95)` where `EgoMod = actor.StatMod("Ego")` (0.25 flat when the actor has no Ego, 1.0 when actor or trader is null), and `linear` and `factor` start at 0 and 1.0 and are adjusted by the `GetTradePerformance` event's handlers (the trader's faction rating adds to `linear`).
- `Reputation.GetTradePerformance(int rep)` (the rating) is: rep <= -600 gives -3, <= -250 gives -1, < 250 gives 0, < 600 gives +1, otherwise +3. The thresholds are `RuleSettings.REPUTATION_HATED -600`, `DISLIKED -250`, `LIKED 250`, `LOVED 600`.
- Check against the 2026-10-07 screenshots: Ego 22 gives StatMod 3 (the log line "Allocated 1 AP to Ego (Now: 22)"), Merchants' Guild reputation 125 gives rating 0, so Performance is 0.35 + 0.07 x 3 = 0.56, and every price on the trade screen matched 0.56 (torch 1 pays $0.56, glowsphere 200 pays $112, toolkit 15 is charged $26.79 = 15 / 0.56).
- Consequences `[verified in code]`: each 2 points of Ego add 0.07; reaching Liked (250) with the vendor's faction adds 0.07, Loved (600) adds 0.21; the ceiling is 0.95. Spending reputation in a Water Ritual only matters here if it crosses a threshold. Which faction's rating the handlers use for a given trader, and any other handlers that adjust `linear` or `factor`, were not read `[unverified]`.

### 14.4 Tooling notes (2026-10-04)
- **Reading IL string constants:** in `dnfile`, scan a method body for `0x72` (`ldstr`) with `raw[i+4] == 0x70`; the string offset is the token's low 24 bits (`int.from_bytes(raw[i+1:i+4], 'little')`); `pe.net.user_strings.get(offset).value` returned the string (in this `dnfile` version `get_us(...)` raised errors). Example: `scratch/inspect_corpse.py`. Field/method tokens: `0x7b/0x7c` (ldfld/ldsfld), `0x28/0x6f` (call/callvirt); table `4` = Field, `6` = MethodDef, `10` = MemberRef.
- **Blueprint XML** lives in `CoQ_Data/StreamingAssets/Base/ObjectBlueprints/*.xml` (`Creatures.xml`, `Items.xml`, `Furniture.xml`, ...). Resolve `Inherits` chains by hand: many parts (e.g. `Physics Category`) are set on a base blueprint.
- **Dead end:** compiling the mod locally with the game's Roslyn (`Microsoft.CodeAnalysis*.dll`) from Windows PowerShell fails (`Could not load type System.Span`; the assemblies target Unity's Mono) and no .NET SDK is installed. Verify C# by launching Qud and reading `build_log.txt` (`Success :)`).
- **Mod folder note:** the loaded mod is listed as `QUDAITEST` (the `Title` in `workshop.json`); the compiled assembly is `ModAssemblies/QudAIBrain.dll`.

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
   > **Correction (2026-10-04, `[verified in code @8ca794c]`):** the current code sets `isZoneFullyExplored = false` and `isAutoexploreStuck = true` when `isCycling`. `isZoneFullyExplored` becomes `true` only at the very end of `ExecuteAutoexplore`, when neither native autoexplore nor `AutoAct.TryFindPathStep` toward the nearest unexplored cell finds a step; any successful step resets it to `false`. So `zone_fully_explored` means "native autoexplore has nothing reachable left", **not** "every cell is revealed" (`unexplored_cells` can stay high behind water or rock), and `autoexplore_stuck` means "the last autoexplore step failed or cycled".

### 15.3 Cycle Centroid Steering Physics
When an oscillation is detected, escaping cannot simply backtrack into recently traversed tiles:
1. **Frontier Escapes:** First check valid candidate moves $m$ where destination $(x + dx, y + dy) \notin \text{recent\_positions}$. If found, select the least-visited frontier tile.
2. **Centroid Steer Fallback:** If all immediate moves lie within recently visited territory (e.g. pinned along a curved shoreline), calculate the geometric centroid of recent positions:
   $$\bar{x} = \frac{1}{K} \sum_{i=1}^K x_i, \quad \bar{y} = \frac{1}{K} \sum_{i=1}^K y_i$$
   Shorelines wrap convexly around water or cliffs; the centroid points toward the center of the lake or obstacle. Moving to maximize Euclidean distance $(n_x - \bar{x})^2 + (n_y - \bar{y})^2$ steers the character away from the obstacle basin and outward onto open dry land.

---

## 16. Safe Swimming Dynamics, Liquid Classification & Hazard Avoidance

### 16.1 The Root Cause of Shoreline Oscillation Traps
In previous iterations, the C# telemetry layer (`AIBrainPart.cs`) contained a coarse check:
```csharp
if (!hasBridge && cell.HasSwimmingDepthLiquid())
{
    names.Insert(0, "[BLOCKED: deep water]");
}
```
This marked every tile of deep water as impassable stone. In `brain.py`, `get_valid_moves` completely dropped any direction mentioning `deep water`.
When rivers, salt marsh lakes, or subterranean pools divided a zone:
1. The AI treated the water as an impenetrable barrier.
2. The agent was constrained exclusively to the shoreline rim.
3. Native autoexplore ping-ponged along the 5-tile shore loop.
4. When hunger hit, the agent could not swim across the water to reach stairs, exits, or food sources, starving in place.

### 16.2 In-Engine Liquid Architecture & Classification
Caves of Qud distinguishes liquid danger at the `Cell` level:
- `cell.GetDangerousOpenLiquidVolume()`: Returns a `GameObject` representing lethal or burning liquids (acid, lava, magma). If null, the liquid is non-lethal.
- `cell.HasSwimmingDepthLiquid()`: Returns `true` if the cell contains liquid deep enough to trigger swimming mechanics.
- `cell.GetSwimmingDepthLiquid()`: Returns the specific deep liquid object (`GameObject`), providing liquid display names (e.g. "pool of fresh water", "salty water", "slime").
- `cell.IsPassable(player, false)`: Returns `true` for deep liquid cells unless a solid wall or boulder is also present inside that tile.
- `XRL.World.Effects.Swimming`: Automatically applied by the engine when a non-flying creature moves into deep liquid. Imposes a movement speed penalty (mitigated by the `Endurance_Swimming` skill).

### 16.3 Telemetry Protocol & Hazard Discrimination
In `AIBrainPart.cs`, cells are classified with strict hierarchy:
```csharp
bool hasBridge = cell.Objects != null && cell.Objects.Any(o => o != null && (o.DisplayName ?? "").ToLower().Contains("bridge"));
if (!hasBridge && cell.GetDangerousOpenLiquidVolume() != null)
{
    var dangerousLiq = cell.GetDangerousOpenLiquidVolume();
    string liqName = dangerousLiq != null ? StripQudFormatting(dangerousLiq.DisplayName ?? "dangerous liquid") : "dangerous liquid";
    names.Insert(0, $"[HAZARD: {liqName}]");
}
else if (!cell.IsPassable(player, false))
{
    names.Insert(0, "[BLOCKED: impassable terrain]");
}
else if (!hasBridge && cell.HasSwimmingDepthLiquid())
{
    var swimLiq = cell.GetSwimmingDepthLiquid();
    string liqName = swimLiq != null ? StripQudFormatting(swimLiq.DisplayName ?? "deep water") : "deep water";
    names.Insert(0, $"[SWIM: {liqName}]");
}
```

### 16.4 Driver Pathfinding & Traversal Weights
In `brain.py`:
1. **Passability Filter:** `get_valid_moves` excludes `[blocked`, `[hazard`, `acid`, `lava`, and `magma`. All safe deep liquids (`[SWIM: ...]` and `deep water`) are valid.
2. **ASCII Grid Rendering:** Deep water tiles render as `'~'` (swimming liquid) rather than `'#'` (wall), preserving `'!'` for lethal acid/lava.
3. **Dry Land vs. Swimming Weighting:**
   $$\text{cost} = (\text{visit\_count}, 1 \text{ if is\_swimming else } 0)$$
   When unvisited dry land is available, the agent walks on land to avoid the swim speed penalty. When dry land is explored or blocked, the agent steps into the water and swims across.
4. **Target Navigation:** `get_best_move_towards(cur_pos, target_pos, valid_moves, surroundings)` considers Chebyshev distance and Euclidean distance first. If an objective (stairs down, exit, enemy) lies across a river, the agent swims directly toward it.

### 16.5 In-Water Invariants: Camping, Cooking & Sustenance
When in swimming depth liquid (`is_swimming: true` or `Effects.Swimming`):
- `can_make_camp = false`: The player cannot spawn a campfire underwater in deep liquid.
- `can_cook = false`: Campfire cooking cannot occur while swimming.
- `can_butcher = false` & `can_harvest = false`: Field processing is disabled while swimming.
- `can_rest = false`: Resting is prevented while swimming to prevent drowning or turn traps.
- `can_eat = true`: If the character is Hungry or Famished while swimming, they eat directly from inventory (`EAT`) without needing a campfire.

### 16.6 Macro-Frontier Water Traversal & Native Autoexplore Decoupling
Vanilla Caves of Qud's native pathfinder (`FasterDMapAutoexplore.FindAutoexploreStep`) does not generate paths through deep water tiles. Consequently, when a zone contains a body of water or wide river dividing landmasses (e.g. northern and southern shores in the Salt Marshes):
1. `FindAutoexploreStep` returns `null` once the immediate dry-land segment is visited, which sets `isZoneFullyExplored = true` in `AIBrainPart.cs`.
2. A purely local 1-tile frontier search penalizes swimming moves vs dry-land moves `(visit_count, 1)` vs `(visit_count, 0)`, causing the agent to cycle dry-land shoreline tiles endlessly.
3. **Macro-Frontier Resolver (`find_zone_unexplored_frontier`):** The driver scans `visible_entities` in telemetry for unvisited entities and cluster centers across the water obstacle ($\ge 3$ tiles away).
4. **Cross-River Step Execution:** When a macro-frontier target is found, `get_best_move_towards(cur_pos, frontier_target, valid_moves, surroundings)` prioritizes geometric convergence over swim penalties, commanding `MOVE_...` directly into the water.
5. **State Reset on Water Entry:**
   - In `AIBrainPart.cs`, executing a manual move resets `autoexplorePosHistory` so that water crossings do not trip the multi-tile oscillation detector.
   - When the agent lands on the opposing shore, any valid step from `FindAutoexploreStep` clears `isZoneFullyExplored = false`, immediately restoring full native autoexploration of the newly discovered landmass.
6. **Hierarchical Exploration Ordering:**
   1. Native `AUTOEXPLORE` (when zone has unvisited dry land and is not stuck).
   2. Macro-frontier navigation (`find_zone_unexplored_frontier`) across water/obstacles.
   3. Local unvisited frontier tiles (`unvisited_local`, `visit_count == 0`).
   4. Zone exit border transition (when standing on exit tile).
   5. Global zone exit navigation (`get_zone_exit_target`) once the entire zone is verified fully explored.
   6. Least-visited fallback.

### 16.7 Native Autoexplore Exit Decoupling & Active Water Interception
1. **Suppression of Premature Zone Exits:** In vanilla Caves of Qud, `AutoAct.FindAutoexploreStep(bool bCanExploreZoneExits, ...)` takes a boolean flag. When set to `true`, native autoexplore automatically paths to an adjacent zone exit when all reachable local tiles are cleared, abandoning the zone without exploring water-isolated islands or opposite banks. In `AIBrainPart.cs`, this flag is strictly set to `false`. When reachable land tiles are exhausted, native autoexplore returns `null`, setting `isZoneFullyExplored = true` so the driver can execute water traversal rather than wandering into another zone.
2. **Coastline Pacing Entropy Detector:** Extended `autoexplorePosHistory` oscillation detection in `AIBrainPart.cs` to trip on long coastlines:
   $$\text{isCycling} = (\text{repeatVisits} \ge 3) \lor (\text{count} \ge 10 \land \text{unique} \le 5) \lor (\text{count} \ge 16 \land \text{unique} \le \text{count} / 2)$$
   Walking back and forth along an 8-tile shoreline trips in 16 steps, yielding immediately to the driver.
3. **Active Water Interception in Driver:** In `brain.py`, `can_use_native_autoexplore` is dynamically computed:
   - If the step toward the unexplored frontier requires swimming (`is_swim_move(best_frontier_m)`) and there are no unvisited dry-land tiles adjacent to the player, native autoexplore is bypassed immediately.
   - The driver commands the water crossing move directly (`MOVE_W`, `MOVE_NE`, etc.), plunging the player into the liquid and navigating directly across the body of water.
4. **Oscillation Frontier Breakout:** When an oscillation cycle is detected along a shoreline, the loop breaker checks `find_zone_unexplored_frontier` first, escaping the shoreline cycle toward the unvisited frontier across the water.

### 16.8 Unexplored Sector Grid Telemetry & Elimination of Micro-Tile Touching
1. **The Flaw in Entity-Based Frontier Searching:**
   In earlier iterations, the driver attempted to find unexplored sectors by scanning `visible_entities` for coordinates where `visit_counts[(x, y)] == 0`. Because `visible_entities` lists all objects visible on screen (every watervine, brinestalk, puddle of salt, rock, and tree), and `visit_counts` only tracks tiles the player's avatar has physically stepped on, 95% of visible entities had 0 visits. Consequently, once native autoexplore finished, the driver attempted to path to and physically step on every single visible object in the zone. If an object sat on an impassable tile (rock, wall), the player bumped against it indefinitely, triggering anti-oscillation repeatedly and taking over 800 turns to leave a zone.
2. **In-Engine Fog-of-War Grid Telemetry (`unexplored_cells`):**
   In Caves of Qud, each `Cell` has a boolean `Explored` property indicating whether fog of war has been lifted. In `AIBrainPart.cs`, `ExportTurnState` sweeps the $80 \times 25$ zone grid (~0.02ms) to compute:
   - `unexplored_cells`: The exact count of unrevealed cells in the zone.
   - `unexplored_centroid_x`, `unexplored_centroid_y`: The geometric center of the unrevealed sector.
3. **Macro-Sector Water Traversal vs. Instant Exit:**
   - If `unexplored_cells >= 35`: A massive unvisited landmass exists across a river or lake (e.g. 200–800 unrevealed tiles). The driver navigates directly toward `(unexplored_centroid_x, unexplored_centroid_y)` across the water.
   - If `unexplored_cells < 35`: The zone's fog of war is fully cleared. Native autoexplore has already looted and uncovered the map. The driver **immediately navigates to the zone exit border** (`get_zone_exit_target`) and transitions out of the zone in ~10 turns.
4. **Result:** Zone completion drops from 800+ erratic turns to ~60–100 clean, natural turns with zero spurious anti-oscillation triggers.

### 14.23 How a melee hit becomes damage (2026-10-08, `[verified in code]`, decoded from the IL with `scratch/il.py`; constants marked unverified)
- `Stat.RollDamagePenetrations(armor, bonus, max)` runs **three trials**. Each trial rolls `1d10 - 2` and, if the result is 8 (a natural 10), adds 8 and rolls again. The trial is a penetration if `roll + min(bonus, max) > armor`. So a hit has 0 to 3 penetrations.
- `Combat.MeleeAttackWithWeaponInternal` then rolls the weapon's damage dice **once per penetration** and adds them up. So armour does not subtract damage: it removes whole rolls of the dice. Expected penetrations per hit (3 trials): AV 4, bonus 0 gives 1.2; AV 4, bonus 3 gives 2.1; AV 6, bonus 0 gives 0.6; AV 8, bonus 0 gives 0.24.
- This explains the damage ledger: the puma's claws are 1d3 each, yet its two claws cost us about 8 per turn (dice alone say 4). `[verified in game 2026-10-07 for the ledger numbers]`
- **Our own combat numbers, as the mod reads them `[verified in game 2026-10-08]`:** `player.Stat("AV")` and `Stat("DV")` are the engine's current values with worn gear included: chain mail (catalogue AV 3, DV -1) took DV from 0 to -1 exactly and AV from 1 to 3 (the +2 instead of +3 fits it replacing a body item worth AV 1 from the starting kit, so base AV 0 `[unverified inference]`). `player.GetPrimaryWeapon()` returns the natural weapon when bare-handed: fist, damage `1d2-1`. A wielded staff reads 1d2, a bronze long sword 1d3 (the catalogue's tier-0 `Long Sword`). `MeleeWeapon.GetNormalPenetration(player)` was -1 in all three cases with Strength 15, so the weapons add nothing and the strength modifier is `(15 - 16) // 2 = -1` (one data point for the divisor, consistent with rounding down).
- **Parties `[verified in code @ PopulationTables.xml, 2026-10-08]`:** creatures arrive in groups from named tables. `BaboonParty` is 3 to 4 `Baboon` (90 percent), 0 to 1 `Hulking Baboon`, 0 to 1 `Shrewd Baboon` (50 percent), 5 percent a hero: about 3.9 creatures. `BigBaboonParty` is 8 to 16 baboons: about 13.4. `SnapjawParty1` is 1 to 3 scavengers (100 percent) plus 1 to 3 (75 percent), hunters, a brute, a warrior, a warlord: about 4.4 creatures plus a 10 percent chance of a second party. A hills sector (`HillsPerSector`, weights 8700 nothing, 900 `SnapjawParty1`, 400 baboons) rolls a snapjaw party in 9 percent of sectors and a baboon party in 4 percent (small or big, half each). Baboons also carry 5 Small Stones and the part `AIThrowAndScoot`: they throw and step back. `[unverified]` how the engine reads a group with no `Style` (the builder assumes pickone).
- **Golems are vehicles, not enemies `[verified in game 2026-10-08]`:** `Hover Golem` and the other golems use `<mixin Name="BaseVehicleGolem"/>`, which sets **level 50, 500 hit points (the infrastructure golem 1,000), faction Barathrumites**, `CannotBeInfluenced`, a `Vehicle` part and `Autonomous`. A wished hover golem exported `is_enemy` false, level 50, `Impossible`, 500 HP, and the character walked away from it. So the IsAlive audit does not make golems enemies (they are not hostile); a real hostile robot to test it needs the Robots faction, e.g. `Scrapbot` (level 10, 30 HP) or `Waydroid`.
- **`Calm` `[verified in game 2026-10-08, one creature]`:** a wished `Scrapbot` (blueprint: `Brain Hostile="false" Calm="True"`, faction Robots, which dislikes the player at -475) exported `is_enemy` false and the character walked away. `Hostile="false"` alone does NOT make a creature peaceful (396 creatures have it, baboons among them, and baboons kill us), so the catalogue now carries `calm` (28 creatures: Scrapbot, Ctesiphus, Salamander, Saltwurm, Engine Crabs, ...) and `likely_hostile` excludes them. What `Calm` does inside the engine was not read. `Waydroid` (level 10, 24 HP, Robots, `Hostile="false"` only) is the next candidate for a hostile non-organic creature.
- Not read yet: what the `bonus` sums (the locals added at the call are a combat skill value, the strength modifier, a weapon bonus and event-supplied `PenBonus`/`CapBonus`), the strength modifier divisor `(score - 16) / 2` `[unverified]`, and where the player's AV comes from. `Leveler.RollHP`/`AddHitpoints` belong to the player's level-ups (Toughness modifier, `Max`); no code was found that adds hit points to a spawned creature for its `Level`, so the catalogue's base hit points may be the real ones `[unverified]`.

### 14.24 Identifying artifacts: the Examiner part (2026-10-09, `[verified in code]` from the IL unless marked; details in docs/tasks/R-4-artifacts-research.md)
- An unidentified item (`Understood()` false) gets the inventory action **Examine** from its `Examiner` part. The handler refuses a broken item and a confused or handless player, reads Intelligence and the `InspectorEquipped` property, asks Yes/No/Cancel for an item owned by someone else (skipped by the tag `DontWarnOnExamine`), then runs either the **Sifrah** examine minigame (option `OptionSifrahExamine` equal to "Yes"; `OptionSifrahExamineAuto` also exists) or a d100 roll (`Stat.RollResult`, `AdjustExaminationRoll`, `GameObject.GetExamineDifficulty`) with outcomes success, exceptional success, partial success, failure, critical failure (and a fake failure while confused). It spends a turn. Critical failure can break the item unless the tag `CantBreakOnExamine` is present.
- Item parts with their own `ExamineFailure` handler (the effect of each was not read `[unverified]`): `IGrenade`, `GeomagneticDisc`, `Displacer`, `TimeCube`, `RocketSkates`, `PortableWall`, `MissileWeapon`, `EquipStatBoost`, `ModFlaming`, `ModFreezing`, `ModElectrified`, `ModDisplacer`, `ModRelicFreezing`, `Tinkering_Mine`, `HelpingHands`, `StrideMason`, `AutomatedExternalDefibrillator`, `DismemberAdjacentHostiles`, `RandomLongRangeTeleportOnDamage`.
- Success calls `Examiner.MakeUnderstood` (partial: `MakePartiallyUnderstood`; `IDAllHere` and `IDAll` identify groups). The mutations Psychometry and Dystechnia and the Tinkering skill (`GetIdentifyLevel`) touch the process.
- `[verified in state 2026-10-09]` the mod's inventory export carries each unidentified item's real `blueprint` while the game shows "weird artifact": a pack held a Grappling Gun, three Nanopneumatic Jackhammers, two Telescopic Monocles, a Geomagnetic Disc, a Telemetric Visor, a Glitter Grenade and a Slip Ring, all with `identified` false.
- `[unknown]` the default of `OptionSifrahExamine`, the roll table of `Stat.RollResult`, the event that triggers Examine from code, and what each `ExamineFailure` does.

### 14.25 Cursed items and how to take one off (2026-10-09, `[verified in code]` from the IL unless marked)
- The part `Cursed` (description rule "Cannot be removed once equipped.") is an active part (`IActivePart`). While it `IsReady` it refuses to let the wearer unequip the item with the message "You can't remove <item>." Only six blueprints carry it: Psychal Fleshgun, Gentling Collar, Gentling Mask (AV 1, Ego -1), Inhibitor Cuff, BarathrumiteSafetyBand, Cyclopean Prism (`RevealInDescription="true"` on the mask: the description says so once the item is understood). The parts `RemoveCursedOnUnequip` and `CursedCybernetics` exist; what the first does beyond reacting to the unequip event was not read `[unverified]`. A separate "WaterRitualCurse" (a story curse for killing a bonded kith) is unrelated.
- `IActivePart.IsReady` fails (so the curse does nothing) when the item is **EMPed** (`IsEMPed`), **broken** (`IsBroken`) or **rusted** (`IsRusted`), when a reality distortion makes it unusable, or when a locally defined failure applies (a powered item with no charge or liquid; the mask has no `ChargeUse`, so this does not apply to it).
- `Body.Rebuild` unequips equipment (`TryUnequip`); the property `CursedBodyRebuildAllowUnequip` is read there, so a rebuild of the body (what a mutation or anatomy change does) can take a cursed item off `[inferred from the property name, not read in detail]`.
- **EMP did NOT work `[verified in game 2026-10-09, two attempts]`:** a wished `EMPGrenade1` thrown one tile away (the character inside the radius), and again thrown at the character's own tile (the game asked to confirm targeting self), left the Gentling Mask unremovable both times. `[inferred from the IL, not tested]` why: `ElectromagneticPulsed.Apply` pulses the inventory, body parts, equipped items and cybernetics of an object, but only when `ShouldPulse` accepts it (`IsEMPSensitive()` or a registered `ApplyEMP` event), and the pulse reaches a creature's worn items through the creature; an ordinary character with no electronics is not EMP-sensitive, so its worn gear is never reached. Whether the mask itself is EMP-sensitive was not read (`GameObject.IsEMPSensitive` calls `IActivePart.Check`; blueprints can set `IsEMPSensitive="false"` on a part).
- Candidate ways in game, from the data `[unverified until tried]`: an **EMP grenade** (`EMPGrenade1`, `EMPGrenade2`, `EMPGrenade3`: part `EMPGrenade` radius 2, 4, 6 and duration 1d2+4, 2d2+5, 3d2+6 turns; whether it reaches worn equipment was not read), **rust** (creatures with the part `RustOnHit`; only metal items rust, a paper-and-acrylic mask does not), or **breaking** the item. Losing the limb it is worn on would also drop it `[inferred]`.

### 14.26 Diggable rock (2026-10-09, `[verified in data]` from `Walls.xml`)
- `Marl` (AV 6, 300 hit points), `Shale` (AV 10, 200), `Sandstone`, `Halite` (rock salt, AV 10, 500) and the other sedimentary rocks inherit `BaseSedimentaryRock` and are ordinary solid objects with hit points, so a melee attack wears them down: with the nanopneumatic jackhammer (2d4) shale went in 4 swings `[verified in game 2026-10-09]`. The engine's edge pathfinder routes through them `[verified in game: ExitDiag steps into Marl]`. Nothing here is special to a digging tool; a weak weapon only takes longer.

### 14.27 Throwing (2026-10-09, signatures `[verified in code]` from `Assembly-CSharp.dll`, blueprints `[verified in data]`; behaviour not tested in game)
- The engine throws with `GameObject.PerformThrow(GameObject Weapon, Cell TargetCell, GameObject ApparentTarget, MissilePath MPath, int Phase, int? RangeVariance, int? DistanceVariance, int? EnergyCost) -> bool`. `Combat.ThrowWeapon(Attacker, Defender, TargetCell, Path, IList<GameObject> Weapons) -> bool` is the AI's wrapper; `Brain.TreatAsThrownWeapon(GameObject)` and `Kill.TryThrownWeapon` belong to creature AI.
- Which item: `GameObject.GetFirstThrownWeapon(Predicate<GameObject>, Predicate<ThrownWeapon>)` and `GetThrownWeapons(...)`; `IsEquippedAsThrownWeapon()`; the body has a `Thrown Weapon` slot (`BodyPart.Thrown`, `Body.GetFirstThrownWeapon`). Range: `GetBaseThrowRange(GameObject Thrown, GameObject ApparentTarget, Cell TargetCell, int Distance) -> int`. The path comes from the same static the missile code uses: `MissileWeapon.CalculateMissilePath(Zone, x0, y0, x1, y1, bool IncludeStart, bool IncludeCover, bool MapCalculated, GameObject Actor) -> MissilePath`. `GameObject.GetPhase() -> int`.
- The part `ThrownWeapon` marks a throwable item. Throwing knives and spears carry `Penetration`, `Damage` and `Attributes` on it (`1d2` to `1d6`, skill ShortBlades) `[Items.xml]`.
- **Geomagnetic Disc** (`Items.xml`): parts `ThrownWeapon`, `GeomagneticDisc Damage="2d6" ChargeUse="100" Bounces="5"`, `EnergyCellSocket`, `AIOffensiveEnergyCellReload`; tags `PathAsIfFlying`. It uses an energy cell charge per throw (`ChargeUse`), bounces up to 5 times through `FindPath` targets (`GeomagneticDisc.DoThrow(Actor, Paths, ..., Targets, LastTarget, Phase, Bonus, ...)`), and its examine complexity is 6. **Verified in game 2026-10-10 (human screenshot of the message log):** thrown at hostile salthoppers it hit for 10, 5, 8 and 8 ("The salthopper takes N damage from your geomagnetic disc") and killed two: it bounced between targets, so it holds a charge. **`PerformThrow` returns false for it even though it hit, and the disc stays in the thrown slot afterwards:** the disc handles the event `BeforeThrown` itself (`GeomagneticDisc.FireEvent`: it asks `IsReady`, flood-searches for hostiles within its range, calls `DoThrow`, and signals `SignalLowPower` or `SignalFailure` when it cannot), which cancels the normal throw. A caller therefore cannot read the return value as success; the mod judges by the hostiles' hit points.

### 14.28 Foamcrete (2026-10-10, `[verified in data]` `Walls.xml`; the failed swings `[verified in game 2026-10-10]`)
- `Foamcrete` is a wall with AV 40 and 100 hit points (heat and cold resistance 75), an ordinary solid object with hit points, so the mod's `[BREAKABLE]` tag applies to it, yet the nanopneumatic jackhammer (2d4, penetration 4) did no damage in 34 swings (`HP 100 -> 100/100`): the wall's armor value is far above what the weapon can penetrate (14.23). Having hit points is therefore NOT the same as being breakable by a given weapon; only the engine's damage report says which. The Qud ruins built of it include one-cell-wide winding mazes with an arconaut and a shrine to Antithrishid, the Mahogany Terror of Nalep, in `JoppaWorld.10.15`.

### 14.29 Psychic glimmer and psychic hunters (2026-10-10; the human's description `[human]`, the code `[verified in code]` from `Assembly-CSharp.dll`, the details of the formula `[unverified]`)
- **Human, 2026-10-10:** "Psychic Glimmer is a thing. The more you use psychic abilities the more your glimmer goes up. Once it reaches a level another psychic can appear who wants your psyche. They are tough foes." Gen 31 died this way: "Your head was exploded by Shwubas-No-Longer, Ptoh's Osprey in the Psychic Torus." with no hostile in the last exported state, at 16/42 HP, on the surface.
- **The code:** `GameObject.GetPsychicGlimmer(List<GameObject> domChain) -> int` returns a creature's glimmer; `GameObject.SyncMutationLevelAndGlimmer()` keeps it in step with mutation levels (so, in the code, glimmer follows the LEVELS of mental mutations; whether plain use of abilities also raises it was not read `[unverified]`); `PsychicHunterSystem` (a game system) has `CheckPsychicHunters`, `CreatePsychicHunter`, `CreateSeekerHunters`, `CreateExtradimensionalSoloHunters`, `CreateExtradimensionalSoloDeviant`, `CreateExtradimensionalCultHunters`, `PlaceHunter`, `GetNumPsychicHunters`, `GetThrallRoll`, `PsychicPresenceMessage` ("a psychic presence ... foreign to this place and time") and wish helpers (`SeekerWish`, `CultWish`, `SoloWish`).
- **When it happens:** `CheckPsychicHunters` runs on entering a zone that is not the world map, once per zone (the zone ID is recorded), rolls the zone's `AmbushChance` and then a second percentile roll that takes the player's glimmer and the number of hunters already created; on success `CreatePsychicHunter` places one. If a reality-stabilizing field covers the player, the message is "Some dimensional interlopers attempt to enter this region of spacetime, but the ambient normality field keeps them at bay." (no hunter).
- **Items `[verified in data, Items.xml]`:** `GlimmerAlteration` adds glimmer (Leyline Puppeteers +10, with a neutron-flux requirement; Otherpearl +40, and objects you find come more often from other dimensions); `RealityStabilization` (the Ontological Anchor bracelet) is the normality field that keeps hunters away.
- **Human, 2026-10-10 `[human, mechanism not read]`:** certain hunters (the kind that killed Gen 31) deal damage for every tile the player moves, so far from a wall or an exit every step hurts and retreating may not be viable.
- **What the brain knows:** nothing. The state does not export glimmer, hunters are not marked, and the creature catalogue's flags do not include them.

---
*End of Engine Internals Manual.*

