# R-2: loot from defeated enemies, items on the ground, and chests (research)

- **Backlog item:** B6 (docs/BACKLOG.md), promoted by the human 2026-10-06 ("Items, chest and getting the character to see if there is loot on defeated enemies")
- **Branch:** `research/2-loot-and-chests` (notes only; no feature code, nothing from `scratch/` is merged)
- **Owner:** Claude Code did the headless part (below); the in-game experiments need the human
- **Status:** Headless research done 2026-10-06; three human experiments pending; implementation not started

## Purpose
Answer how the engine already handles chests, ground items and death drops, so the work can be a small change instead of a new UI flow.

## Findings
`[verified in code]` means read from `Assembly-CSharp.dll` with the probes in `scratch/`. Nothing here has been run in game yet.

1. **The game's own autoexplore already handles chests and items.** `FasterDMapAutoexplore` keeps a list of "autoexplore objects" (`AutoexploreObjects`, `MarkAutoexploreObjects`). `IsAutoexploreObject` accepts an object when `GameObject.ShouldAutoexploreAsChest` is true (it reads the int property `Autoexplored`, `Understood`, the content count and `Owner`: not yet explored, understood, has contents, unowned), or when the object can be interacted with in a solid cell.
2. **The execution half lives in `ActionManager.RunSegment`**, the engine's autoexplore loop. It calls `FindAutoexploreObjectToOpen` (strings `Open`, `Opener`), `FindAutoexploreObjectToProcess`, `CanAutoget`, `ShouldTakeAll`, `TakeObject`, `AttackDirection` and `SetAutoexploreSuppression`, and checks `CheckHostileInterrupt`. So the engine's loop itself opens a container, takes its contents, picks up ground items and attacks adjacent hostiles.
3. **Objects declare what to do when autoexplore stands next to them** through `AutoexploreObjectEvent` (fields `Action`, `Command`, `AllowRetry`, `AutogetOnlyMode`; methods `Check`, `CheckForAdjacent`, `GetAdjacentAction`). Handlers found: `GameObject`, `Examiner` and the ammo and energy-cell parts (`Autoget`), `LiquidVolume` (`CollectLiquid`), Butchery (`Butcher`), Harvestry (`Harvest`), `Tinkering_Mine` (`DisarmMine`), `Tinkering_Disassemble`, `PluckablePolyp`, `Brain` (hostile adjacent: attack), `WantToAutoexplore`.
4. **`GameObject.CanAutoget`** is true for takeable, real, non-hidden, non-temporary objects without the `NoAutoget` tag or property that are not `DroppedByPlayer` (the player's own dropped items are never re-picked).
5. **What the mod does today (the likely cause of "walks past a ton of chests").** `ExecuteAutoexplore` (AIBrainPart.cs) asks `FasterDMapAutoexplore.FindAutoexploreStep` for a *movement step* and calls `player.Move(step)`. It never runs the engine's adjacent-action half. When the step leads into a chest the move does not succeed, and the mod then marks that object `Autoexplored`, `AutoexploreSuppressed` and `AutoexploreSuppression` (the "Autoexplore Blocked: Suppressed blocking object" branch) so it is not targeted again. A second path does the same for objects next to a cycling character ("Suppressed adjacent POI"). Both only spare objects that `CanSafelyLoot` allows, which excludes every container. `[verified in code]` for what the code does; that this is *why* chests stay unopened is `[inferred]`.
6. **Ground items today.** `CanSafelyLoot` allows only Armor, MeleeWeapon, MissileWeapon, Shield and Commerce-type items, nothing owned, nothing in settlements, weight 15 or less. `GET_ITEM` and the start of `Execute` pick up an allowed item *when he is standing on it* and then fire `CommandAutoEquip` (auto-equip, no scoring). Nothing walks him to an item except native autoexplore's own goals. `item_evaluator.py` (a 10-criteria scoring rubric) exists but `brain.py` does not import it.
7. **Death drops.** A dead creature's inventory is dropped through `Inventory`'s handling of `DropOnDeath` / `GetDropInventory`, and `Body` honours `NoDropOnDeath` for equipment. `Corpse.ProcessCorpseDrop` adds the corpse (ENGINE_INTERNALS 12.1b). So loot lands on or next to the dead creature's cell. `[verified in code]` that these members exist; which items drop and exactly where is `[unverified]`.
8. **Fire and Light may matter for loot too** (a burning creature's flammable items). `[unverified]`, not checked.

## Open questions (need the human, a throwaway character, in game)
- **E1, what a bump does.** Stand next to a chest and press a movement key into it. *Predict first:* does it open the container UI, or nothing? This shows what the mod's `player.Move` into a chest does.
- **E2, what the engine's own autoexplore does.** Next to an unopened chest with no hostiles in sight, press the game's autoexplore key. *Predict first:* does it open the chest and take everything, take some, or show a menu? Does it walk to ground items and pick them up?
- **E3, death drops.** Kill a snapjaw that carries a weapon. Where does the weapon land (its cell, a neighbour)? Does anything stay in a corpse container?

## Suggested next steps (not started; the human chooses)
- **Option 1 (smallest, engine-led):** in `ExecuteAutoexplore`, run the engine's adjacent-action half (`FindAutoexploreObjectToOpen` / `FindAutoexploreObjectToProcess`, then perform the action the engine names) instead of suppressing the object, restricted by ownership and settlement rules (R7).
- **Option 2 (hand the job to the engine in safe moments):** when no hostile is in sight and he is outside a settlement, let the engine's own autoexplore run (`AutoAct`) and take control back on any interrupt.
- **Option 3 (our own container logic):** write open and take code with item scoring. The largest, and the one most likely to create new UI loops.
- Whatever is chosen, decide the **take policy** first: everything unowned that fits the weight limit, only gear that beats current gear, or food and ammo only. Keep R7 (no owned items, nothing in settlements).

## Result
- **Surprise:** the engine already contains the whole chest and loot flow. The mod disables it by suppressing the objects it cannot step into.
