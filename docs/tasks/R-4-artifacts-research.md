# R-4: artifacts (examining and using unidentified items) research

- **Backlog item:** B15 (docs/BACKLOG.md)
- **Branch:** `docs/artifacts-research` (notes only)
- **Owner:** human drives the in-game experiments; Claude reads the engine and explains
- **Status:** First pass done 2026-10-09 (code and state only); in-game experiments still open
- **Budget:** one session

## Purpose
Answer what an "artifact" is, what examining one does, what it risks, and whether the brain can do it without a menu, so that B15 can become a defined task. No feature code.

## What the paused game showed (2026-10-09, `last_state.json`, Gen 30, level 5, Intelligence 17) `[verified in state]`
The pack held nine unidentified items. The mod exports each item's REAL blueprint although the game shows "weird artifact" or "odd trinket":

| game shows | real blueprint | weight |
|---|---|---|
| odd trinket | Slip Ring | 2 |
| weird artifact | Grappling Gun | 5 |
| weird artifact (three of them) | Nanopneumatic Jackhammer | 16 each |
| weird artifact x2 | Telescopic Monocle | 6 |
| weird artifact | Geomagnetic Disc | 2 |
| weird artifact | Telemetric Visor | 1 |
| weird artifact | GlitterGrenade1 | 1 |

All have `identified: false` (the mod's `Understood()`). So the brain can already read what they are, which a player cannot: any use of that knowledge is a policy choice (see below).

## Questions and answers
1. **What is an artifact?** `[verified in game data: Manual.xml, Data.xml]` an item "so technologically complex that few understand it"; unidentified ones use placeholder names (`BaseUnknown` "weird artifact", `UnknownOddTrinket` "odd trinket") and lose their `Examiner` until understood. Tonics count too.
2. **What is the interaction?** `[verified in code, IL of XRL.World.Parts.Examiner]` the item gets an inventory action **Examine** while it is not understood (the part adds it when `Understood()` is false). Handling it: refuses a broken item; needs working hands (`CanMoveExtremities`); reads the player's **Intelligence** and any `InspectorEquipped` bonus; refuses while confused ("You're too confused to do that"); if the item is **owned by someone else** it raises a Yes/No/Cancel popup ("examining risks damaging it", skipped by the tag `DontWarnOnExamine`); then EITHER the **Sifrah** examine minigame (`ExamineSifrah`) when the option `OptionSifrahExamine` is "Yes", OR a d100 roll (`Stat.RollResult` with `AdjustExaminationRoll` and `GetExamineDifficulty`) giving `ResultSuccess`, `ResultExceptionalSuccess`, `ResultPartialSuccess`, `ResultFailure` or `ResultCriticalFailure` (plus a fake failure while confused). It uses a turn (`UseEnergy`).
3. **What does it risk?** `[verified in code]` a critical failure can break the item unless it has `CantBreakOnExamine` (the manual: a small chance on each failure). Many item parts have their own `ExamineFailure` handler: `IGrenade` (grenades), `GeomagneticDisc`, `Displacer`, `TimeCube`, `RocketSkates`, `PortableWall`, `MissileWeapon`, `EquipStatBoost`, the `Mod*` weapon mods, `Tinkering_Mine`, `HelpingHands`, `StrideMason` and others. What each one does on failure was not read, so assume an explosion, a teleport or a discharge is possible `[unverified]`.
4. **Can it be driven headlessly?** `[partly verified]` the roll path has no menu. The blockers are the Sifrah minigame (a modal screen when `OptionSifrahExamine` is "Yes"; the default value was not found in the game data) and the owned-item popup (not an issue for items he carries). There is also `OptionSifrahExamineAuto`, which presumably resolves the minigame automatically `[unverified]`. The inventory-action event that triggers Examine was not decoded: the mod's EQUIP_ITEM uses `player.AutoEquip` directly, so a `player.FireEvent`/`InventoryActionEvent` call needs a small experiment `[unknown]`.
5. **What does success give?** `[verified in code]` `Understood()` becomes true (`Examiner.MakeUnderstood`), the item takes its real name and description; partial success gives a partial understanding (`MakePartiallyUnderstood`); `Examiner.IDAllHere` / `IDAll` identify groups. A character can also have the mutation **Psychometry** or the skill path **Tinkering** (`Tinkering.GetIdentifyLevel`), and **Dystechnia** blocks examining technology.
6. **What do these particular items do?** not read; their blueprints are in `data/items.json` (group `other` or `artifact`). The Nanopneumatic Jackhammer is a digging tool (BACKLOG B7), the Grappling Gun and Slip Ring are movement items `[inferred from the names, unverified]`.

## Open questions that need the human or a probe
- In game: examine one artifact by hand. Did a Sifrah minigame screen appear (this answers the default of `OptionSifrahExamine`), what did the result text say, and what happened on a failure?
- Which InventoryAction event name triggers Examine from code (decode `InventoryActionEvent` and the Examine handler's entry).
- What each `ExamineFailure` handler does (grenade, Geomagnetic Disc first, since the pack holds one of each).
- The exact roll table of `Stat.RollResult` and what `GetExamineDifficulty` returns for these items (the IL of `RollResult` was too tangled to read reliably in this pass).

## Suggested next steps
1. Human: examine one or two of the cheap items by hand and report the three observations above (the glitter grenade and the monocle are probably the safest).
2. Claude: decode the Examine entry point and the failure handlers named above.
3. Then a small stage-1 build: a C# `EXAMINE_ITEM:<id>` command (set the Sifrah option to its automatic or off state, fire the inventory action, report `identified` and the new name in `last_inventory_action`) and a Python rule that examines one unidentified item per safe moment (no hostiles, near full HP, a per-item attempt limit).

## Policy questions for the human
- **The blueprint is visible to the brain.** Should the brain use it (for example to avoid examining a grenade, or to decide a jackhammer is worth carrying) or behave like a player and learn only by examining? I would not let the brain use the real name of an unidentified item for decisions beyond safety.
- **Risk appetite:** examine only at full health and out of combat? Accept a small chance of losing an item? Accept a grenade going off?
- **Weight:** the pack carries 48 lb of jackhammers; nothing drops unidentified items today.
