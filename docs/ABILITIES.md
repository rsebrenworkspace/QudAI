# QudAI: Ability control audit (2026-10-06)

> Question (human): "how many abilities can we control from automation?" Answer, in three honest levels. Confidence tags:
> `[verified in code]`, `[verified in game logs]`, `[verified in game data]`, `[unverified]`.

## 1. How an ability gets used today

1. **Export** (`AIBrainPart.cs`, state export): every **enabled** `ActivatedAbility` is sent as `{name, command, cooldown, usable, active}`; `active` is the toggle state. `[verified in code]`
2. **Decide** (`brain.py`): Phase A (safe) and the fallbacks/LLM (combat) pick `USE_ABILITY:<command>[:<dir>]` for abilities whose name or command matches a known keyword family. `is_ability_ready` checks enabled, usable, cooldown, active and "0 charges". `[verified in code]`
3. **Execute** (C# `USE_ABILITY`): resolves the command by command string, display name or `Command<Name>`; picks a target (enemy in the requested direction, nearest enemy with line of sight, or the adjacent proselytize target); refuses offensive rays through a companion (R8); sends `CommandEvent.Send(player, cmd, target, cell, ...)` **and** `player.FireEvent(Event.New(cmd, "User", player))`; spends a turn. The C# side does **not** re-check usability or cooldown; it trusts Python. `[verified in code]`
4. **Pickers** are answered by Harmony patches: direction (`PickDirection.ShowPicker`), target cell/object, yes/no. `[verified in code]`

## 2. The three levels

| Level | Count | Meaning |
|---|---|---|
| Visible to Python | **every enabled ability** (11 on the level-5 Esper) | Name, command, cooldown, usable, toggle state are exported. |
| Python has decision logic | **about 20 families** | See section 3. Anything else is simply never chosen. |
| Proven to fire in real runs | **5 abilities** in the two newest `Player.log` files (+ the decision trace) | Lase 47, Stunning Force 15, Intimidate 3, Teleport Other 3, Proselytize 2. Cooldowns in his saved state (Stunning Force 32, Teleport Other 53, Intimidate 25, Lase "0 charges") show they really fired in the game. `[verified in game logs]` |

The generic C# path can send **any** command, so "can be controlled" is true in principle for all of them; "has ever been used successfully" is the short list above.

## 3. Families with Python logic (from the `find_ready_ability` keyword lists and C# actions)

Proselytize/Beguile, Sunder Mind, Stunning Force, Lase (Light Manipulation), Freezing Ray, Flaming Ray, Cryokinesis/Pyrokinesis/Spit Poison/Electrical, Syphon Vim, Force Bubble/Wall, Teleport Other, Teleportation/Phasing (escape), Intimidate, melee strikes (Dismember, Cleave, Slam, Shield Slam, Swipe, Decapitate, Bludgeon, Backhand, Flurry), Charge/Lunge, Disarming Shot, Chain Fire, Sprint (`ACTIVATE_SPRINT`), Make Camp (`MAKE_CAMP`), Butcher, Harvest. Ambient Light is kept on by C# (`EnsureLightSource`), not by Python. `[verified in code]`

**Never seen in a real run (logic exists, no evidence it works):** Sunder Mind, Force Bubble/Wall, Teleportation/Phasing, Freezing/Flaming Ray, Cryokinesis/Pyrokinesis, Syphon Vim, melee strikes, Charge, Disarming Shot, Chain Fire. Sprint was chosen 0 times in 6263 traced turns. `[verified in game logs/trace]` (the logs cover only the newest characters).

## 4. The level-5 Esper's 11 abilities

| Ability (command) | Python logic? | Evidence |
|---|---|---|
| Sprint (`CommandToggleRunning`) | yes (`ACTIVATE_SPRINT`) | never chosen |
| Make Camp (`CommandSurvivalCamp`) | yes (C# `MAKE_CAMP`) | earlier characters |
| Intimidate | yes | fired 3x |
| Proselytize | yes | fired 2x |
| Lase (`CommandLase`) | yes | fired 47x |
| Stunning Force | yes | fired 15x |
| Teleport Other | yes | fired 3x |
| Clairvoyance | **no** (deliberately in `NON_COMBAT_KEYWORDS`) | none |
| Ambient Light (toggle) | C# only | kept on |
| **Burrowing Claws** (`CommandToggleBurrowingClaws`, toggle) | **no** | none |
| **Dig** (`CommandDig`) | **no** | none |

## 5. Findings and risks

1. **Burrowing Claws and Dig are unused, and probably worth using.** Engine facts: the `BurrowingClaws` part has `GetWallHitsRequired`, `GetWallBonusPenetration`, `GetWallBonusPercentage`, `CheckDig`, and ability ids `DigUpActivatedAbilityID`, `DigDownActivatedAbilityID`, `EnableActivatedAbilityID` plus a `PathAsBurrower` field; the toggle applies a `Burrowed` effect (move penalty, "Stop Burrowing", "You cannot do that while burrowed", "You cannot travel long distances while burrowed", "You cannot dig on the world map"). `[verified in code]` that these members and strings exist. `[unverified]`: what exactly Dig up/down does (descend or ascend a stratum without stairs?), whether the claws make our melee wall-breaking (`ATTACK_WALL`, `TryBreakPathObstacle`) faster (the member names suggest so), and how the engine pathfinder behaves while burrowed.
2. **Matching is by substring on the display name** (R3 drift risk). `Lase (4 charges)` matches the melee `charge` keyword, so the melee fallback can mistake Lase for a charge. `[verified in code, reproduced]`
3. **No C# usability check**: a stale or wrong Python decision fires into a cooldown (wasted turn, no error).
4. **Double firing**: `CommandEvent.Send` and `FireEvent` are both sent for one use; cooldowns probably prevent a double effect, but this is `[unverified]`.
5. **The LLM sees only a whitelist** of combat families, so unknown abilities (the claws, Dig) are never offered by accident, which is good, but also means new abilities need explicit work.
6. **Toggles are special**: `active` is exported, but only Sprint has toggle logic. A toggled-on ability the brain does not know about (Burrowing Claws) could lock actions ("cannot do that while burrowed").

## 6. Done in T-1.25 (2026-10-06)

- Registry of every activated ability: `data/abilities.json` (145, from the game's own data; `command_source` says whether a command was spelled out in code or derived).
- Matching by exact command through `data/ability_families.json` and `ability_registry.py`; the `charge` false match is fixed (Test 69). Families with `auto_use: false` (Teleportation, Phasing toggle, burrowing, Decapitate toggle, Clairvoyance, Ambient Light) are documented, not wired.
- Found while doing it `[verified in game data]`: there is no activated "Chain Fire" or "Disarming Shot" (the latter is a passive Pistol skill), and Cleave/Bludgeon/Backhand are not activated abilities. `CommandMassiveCharge` is Horns' "Triple Horn", `CommandLifeDrain` is Syphon Vim, `CommandCryokinesis` is "Chill", `CommandPyrokinesis` is "Toast".
- C# usability pre-check and `last_ability_use`; Python stats in `memory/ability_stats.json`.
- Section 5 items 2 and 3 are fixed; item 5 was wrong (the LLM list was a blacklist) and is now a whitelist.

## 7. Still open



1. Decide with the human whether to promote BACKLOG B7 (use traversal abilities on purpose); a research card first (what Dig up/down and the toggle do, headless).
2. Replace substring matching by an explicit command-to-family table (engine command names are stable: `CommandLase`, `CommandStunningForce`, ...), and fix the `charge` false match.
3. Add a C# usability pre-check and log a refusal instead of spending a turn silently.
4. Collect evidence for the never-seen families by logging each ability use and its cooldown change (cheap), so "works" can be measured instead of assumed.
1. BACKLOG B7 (use traversal abilities on purpose) needs a human promotion and a research card.
2. Wiring Teleportation (`CommandTeleport`) and the Phasing toggle needs in-game tests of the cell picker and untoggle logic.
3. Auto-disabling a command that is attempted many times and never fires (needs real `ability_stats.json` data first).
4. Abilities without a cooldown cannot be shown as "fired" by the cooldown rule.
