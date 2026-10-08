# QudAI: Backlog (ideas that are not scheduled work yet)

> The project is expected to grow. This file is where growth is **captured without derailing the current stage**.
> An idea here is not a task. Agents do not start backlog items unless a human has promoted them (see section 1).
> Status per idea is tracked in the `Backlog` sheet of `QudAI_Roadmap.xlsx`. This file holds the details agents need.
> Confidence tags: `[verified in code @c50b3c2]` (read in the code), `[from docs]` (a doc says so, not checked), `[unknown]` (needs research).

## 1. How an idea becomes work

| Step | Status | Requirement |
|---|---|---|
| 1 | **Idea** | Captured here in your words, with what exists today and what is unknown. |
| 2 | **Researched** | A research card (`docs/tasks/RESEARCH_TEMPLATE.md`) has answered the engine questions. Findings are in `ENGINE_INTERNALS.md`, tagged. |
| 3 | **Defined** | Measurable exit criteria are written, dependencies are named, and a size estimate exists from measured usage (a small card cost about 4% of the hourly meter on 2026-10-04). |
| 4 | **Scheduled** | A numbered stage gets it, usually because the previous stage's exit criteria are met or close. |

Why: new features are where new loop bugs come from (equip/unequip loops, accidental dialogue confirms, chat spam). A stable base first, then a researched feature, keeps the cost of each step small.

## 2. Ideas

### B0. QudAI console (promoted by the human 2026-10-07, built as T-1.47)
- **Your words:** a small Windows tool that launches the brain, pauses and reactivates it, shows the logs, mod health at launch, last state, and lets me approve runs, all in one application.
- **Exists today:** `tools/qudai_console.py` with Control, Mod health, Live, Review and Items tabs `[verified in code]`; logic tested offline (Test 91); launch/engage/pause/stop of the real brain verified against a temp exchange folder `[verified 2026-10-07]`.
- **Not yet done `[unverified]`:** a real session next to the game; the layout will want adjusting after use.
- **Grow later (human: "as the need grows"):** item scores beside the inventory, model-lab results and a picker backed by them, `game_log.txt` tab, docs tab (HANDOFF/BACKLOG), run-length trend across generations, danger ledger view.

### B1. Cooking and recipes
- **Your words:** cooking, and how many recipes there are in the game that can alter gameplay.
- **Exists today:** `COOK_MEAL`, `MAKE_CAMP`, `BUTCHER`, `HARVEST` handlers in C#. `COOK_MEAL` consumes one ingredient, clears hunger, and fires the campfire's after-cooked hook **without** opening the recipe menu, so meals are used only as hunger relief, never for their effects `[verified in code @c50b3c2]`. Build templates buy the cooking skills early `[verified in code]`.
- **Unknown `[unknown]`:** where recipes are defined and how many exist; which give gameplay effects (buffs, stat changes, other); whether a specific recipe can be chosen headlessly; how ingredient choice works without the UI; which recipes are worth cooking in which situation.
- **Depends on:** a stable sustenance loop (Stage 1), inventory awareness (Stage 4).
- **Size (my guess):** research small; implementation medium to large depending on what the recipe system exposes.
- **Risks:** the current workaround deliberately avoids the recipe UI; meal effects could interfere with fights; ingredient hoarding versus carry weight.
- **First research card:** `docs/tasks/R-1-cooking-recipes-research.md`.

### B2. Random quests
- **Your words:** random quests that can be acquired.
- **Exists today:** nothing implemented. `PROJECT_HISTORY.md` lists three named quests as a plan (Red Rock watervine, Barathrum wire retrieval, Golgotha) `[from docs]`. The mod auto-answers Yes to every yes/no popup `[verified in code @c50b3c2]`, so an NPC offer that arrives as a yes/no popup could be accepted without the agent knowing `[unverified: hazard to test before adding any NPC conversation]`.
- **Unknown `[unknown]`:** how quests are stored and read (objectives, status); how the agent talks to NPCs without UI; how to tell a random quest from a story quest; quest types (fetch, kill, escort, delivery) and what each needs.
- **Depends on:** stable movement and pathing to arbitrary cells (Stage 1; `NAVIGATE_TO_CELL` exists), combat competence, inventory (Stage 4).
- **Size (my guess):** large, with several sub-types.

### B3. Lore snippets, relayed to Twitch chat (outside the planned voting)
- **Your words:** lore snippets, and a way to relay them to a Twitch chat.
- **Exists today:** `twitch_bot.py` is an IRC listener for viewer votes `[from docs; not reviewed]`. The Chronicler already produces readable death tales (`chronicles/*.md`), which could be relayed too `[verified]`.
- **Unknown `[unknown]`:** where lore text appears in the game (books, signs, conversations, journal entries) and how to capture it without UI; how to **send** chat messages (needs a bot account and an OAuth token with chat permission, which the listener may not have); rate limits and moderation.
- **Risks:** tokens must never be committed (AGENTS.md hygiene); chat spam; long lore passages are game content, so keep snippets short or have the model write in-character commentary instead of quoting. Check Freehold's guidance on streaming and content use `[unverified]`.
- **Depends on:** a run that stays up (M1) and the Twitch layer (Phase 9). Independent of the core agent otherwise.
- **Size (my guess):** medium after research.

### B4. True Kin and cybernetics
- **Your words:** we have not even delved into True Kin and cybernetics.
- **Exists today:** a `praetorian_*` combat template is in the build file `[verified in code]`. The docs plan "find Becoming Nooks and install implants" `[from docs]`. Nothing is implemented.
- **Unknown `[unknown]`:** how implants are installed (UI flow); what resource limits or pays for them; where Becoming Nooks are and whether they sit in settlements (where the mod must not vandalize or loot); which implants matter for each build.
- **Depends on:** progression (Stage 3), inventory and settlement behavior (Stage 4).
- **Size (my guess):** large; research first.

### B5. Already on the roadmap, parked in Stage 5 (Backlog)
Trading (task 7.3), water and hydration economy (7.2), world map navigation and the first quest chain (8.1 and 8.2), OBS stream overlay (9.2).

### B6. Opening chests and containers
- **Ethics policy (human, 2026-10-07):** owned containers stay untouched (he skipped the chests in Kuyukas's gunsmith workshop and the human confirmed that is right: "keep it ethical for now"). Stealing from owned containers is a later option for scoundrel-style builds, not for the current character. Open and unverified: why a given container was skipped is not exported (owned, empty and suppressed look the same); and the walk to a container can stall two tiles away when the container's own cell is not walkable (trace turns 1561-1566, 2026-10-07).
- **Item scoring and junk dropping (2026-10-06, promoted by the human, "then eventually town and merchants"):** stage 1 built in T-1.43 (catalog, scorer, equip and drop decisions, report); stage 2 (C# inventory export, `DROP_ITEM` and equip commands, wiring into `brain.py`) is next; selling to merchants is explicitly later.
- **Status (2026-10-06): promoted by the human, option 1 + "take everything unowned"; built in T-1.34 (`task/1.29-loot-chests`), awaiting a game test.** Research: docs/tasks/R-2-loot-and-chests-research.md. Unlocked or trapped chests are not distinguished (the data shows no lock part on a plain `Chest`); the first real run is the test.
- **Your words:** he walks by a ton of chests to be opened, and we have not addressed that yet (2026-10-05, during a dungeon run).
- **Exists today:** nothing opens containers. `CanSafelyLoot` deliberately refuses chests, crates, barrels, baskets and other "containers" so the agent never picks up furniture `[verified in code @4d25aea]`; the loop breakers also *suppress* adjacent chests as points of interest so autoexplore stops circling them `[verified in code]`; Python's non-hostile entity list names `chest` among things to ignore `[verified in code]`. AGENTS R7 forbids looting owned items and anything in peaceful settlements.
- **Unknown `[unknown]`:** how a container is opened without its UI (what the `Container`/`Chest` parts expose, and whether opening always shows a menu); which containers are trapped, locked, or owned; how loot inside is listed and taken (item picker versus direct transfer); what to take (weight, value, usefulness: needs the item scoring in `item_evaluator.py`); whether the opened state is visible so he does not reopen the same chest.
- **Depends on:** inventory and item awareness (Stage 4), a safe pickup rule that respects ownership (R7), and the popup handling being proven stable (the item picker is one of the patched popups).
- **Size (my guess):** research small to medium (the container parts and the take-loot API), implementation medium.
- **Risks:** a new UI flow means new loop bugs (open, close, reopen); taking owned items from a settlement; trapped or locked chests; picking up heavy junk and becoming burdened; the decision of when a chest is worth the detour during exploration.

### B7. Using traversal mutations on purpose
- **Status (2026-10-06): promoted by the human ("Do A and B, then C").** Step 1 done in T-1.26: research (below) and the settlement safety toggle. **Not done, needs a human decision:** `CommandDigDown`/`CommandDigUp` (excavate stairs, see ENGINE_INTERNALS 14.8) and Wings.
- **Your words:** a traversal tier, because dungeons are procedural, so claws helps to get through terrain (2026-10-06). The tier only affects which mutation is *bought*; nothing yet *uses* the ability.
- **Exists today:** the mutation ranking puts Burrowing Claws and Wings third (`mutation_policy.py`) `[verified in code]`. The engine has `PathAsBurrower`, `PathAsIfFlying`, a burrowed state and a Flying effect (ENGINE_INTERNALS 11.5) `[verified in code strings]`. The brain already breaks trees by melee (`TryBreakPathObstacle`, `ATTACK_WALL`).
- **Unknown `[unknown]`:** how Burrowing Claws is activated and what it does to walls, trees and the pathfinder (verified so far: a toggle ability `CommandToggleBurrowingClaws` plus a `Dig` ability `CommandDig`; the part has wall-hit and wall-penetration members, and `DigUp`/`DigDown` ability ids, ENGINE_INTERNALS 11.5; "You cannot travel long distances while burrowed"); how flight starts and ends with Wings, whether it lets him cross deep water and pits, and what it costs; how the pathfinder flags interact with `AutoAct`; whether either breaks our loop breakers or frontier logic.
- **Depends on:** a character that actually owns the mutation, and the frontier and burrow logic staying stable.
- **Size (my guess):** research small, implementation medium (a new movement mode).
- **Risks:** a new movement mode means new loop bugs; being unable to travel while burrowed; flying over hazards he cannot leave; fire and water interactions.

### B8. Merchants and trading, starting with Kuyukas the legendary gunsmith (human, 2026-10-07)
- **Your words:** merchants and selling are "down the road"; on 2026-10-07 the run reached a sleeping legendary gunsmith, Kuyukas, in a hidden workshop (stratum 11 of JoppaWorld.11.21.0.0). "Kuyukas, legendary gunsmith. Kuyukas snores loudly is the only prompt right now."
- **Exists today `[verified in game data]`:** Kuyukas is the `Gunsmith` blueprint (inherits `BaseMerchant`, level 18-20, 70 HP, stock `GunsmithInventory_Legendary`, one hired guard; the guards read as peaceful creatures such as worms of the earth). His conversation is flavour only ("Live and drink."): trading is the interaction, not a quest. His workbench is owned by the Merchants faction, which is why the loot code correctly skips the chests there. A sleeping creature has the `Asleep` effect, does not respond to conversation, and offers a peaceful `Wake` interaction (ENGINE_INTERNALS 14.13). The character carries about 62 water drams plus waterskins (currency, see memory note), and no trade code exists.
- **Verified in game 2026-10-07 (human):** a mouse click on the sleeping Kuyukas offered the Wake action; after waking he moved to another room (why is unexplained); Talk (`c`) then offered three choices: **Water Ritual**, **Let's trade**, and **Live and drink** to end. Water Ritual and Trade are inherited from `BaseConversation`: the ritual choice is added for any speaker with the `GivesRep` part, `WaterRitualBegin` has a `Drams` cost, and the ritual node can offer, depending on the speaker, secrets and gossip, tinkering and cooking recipes, a skill or skill point, a mutation, a gifted valued item, and joining the party (all `[verified in game data]` as possible choices; which ones Kuyukas offers `[unverified]`).
- **Ritual screens, by the human 2026-10-07 `[verified in game]`:** with Kuyukas the Water Ritual showed three popups (sharing the water, the Merchants' Guild increase of 125, a decrease for the Children of Mamon from 50 to -650) and then a fourth window, the ritual menu: "Kuyukas can award an additional 100 reputation" (standing with the Merchants' Guild was 125), with three choices: [1] "Share a secret with me" for -50 reputation, [2] "Would you gift me your jewel-encrusted sturdy Issachar rifle?" for -70 reputation (the $500 firearm from his stock), and [3] "Live and drink" to end (a Trade button is on the same window). So the ritual spends the Guild reputation it just granted: gifts and secrets are bought with it. See B9.
- **Trade screen and ritual, seen by the human 2026-10-07 (screenshots) `[verified in game]`:** the character (new run, "Okas", Hungry, 64/225 lbs, "$61") traded in drams: the footer reads "0.00 drams -> TRADE <- 0.00 drams" and his purse "$61" matches `water_drams` in the state, so the trade currency is fresh water, and the `$` figures are prices in drams. Kuyukas's stock: ammo (lead slug x127 and shotgun shells at $0.02, wooden arrows), artifacts ($35.71 to $238.66), a toolkit ($26.79), and 7 firearm lines (musket $39.29, masterwork musket $45.36, chrome revolver x3 $98.21, slender chrome revolver $107.14, Issachar rifle x5 $98.21, masterwork Issachar rifle $116.07, a jewel-encrusted sturdy Issachar rifle $500). His sell prices on the character's side are tiny (a weird artifact $1.12, lead slug $0.01, a torch $0.56, a floating glowsphere $112, an empty waterskin $2.80 each, a waterskin with 8 drams of honey $11.76). The Water Ritual message was "You share your water with Kuyukas ... and begin the water ritual", then "Your reputation with the Merchants' Guild increased by 125 to 125." The trade screen has its own key hints ([Space] vendor actions, [=] add one, [-] remove one, [Tab] toggle all, Ctrl+Tab sort, Ctrl+F filter).
- **Unknown `[unknown]`:** how the trade screen is driven without the UI (is there a headless buy/sell API, or does it need the popup patches?); how prices and the waterskin/dram currency work; what the sleeper's Wake menu key is in the human's setup; how the legendary stock looks; how selling interacts with the junk dropper and the protected quest/reputation items.
- **Depends on:** the inventory milestone (stage 2 verified in game: equip works, drops not yet seen), item scoring (a "sell" list instead of a "drop" list), and the popup handlers staying stable.
- **Size (my guess):** research small (the trade API), implementation medium; first a read-only "list his stock" export, then buy/sell.
- **Risks:** the AI auto-answers popups, so an open trade screen could buy or sell unintended items; owned items must never be taken without paying (ethics policy B6); selling protected items.

### B9. Export faction reputation (promoted by the human, 2026-10-07)
- **Your words:** after the Water Ritual with Kuyukas the Children of Mamon went from 50 to -650 while the Merchants' Guild rose by 125: "A few more of these and should be kill on sight." Asked for a faction-reputation export so the brain and the console can see it.
- **Exists today:** nothing exports reputation; the brain only learns a creature is hostile after the engine marks it (`is_enemy`), and cannot see why `[verified in code]`. The ritual awards the speaker's faction and moves factions that love, dislike or hate it (`WaterRitual.ModifyReputation`: primary, faction, attitude, friend and dislike awards; Merchants' Guild feels -100 about Mamon in `Factions.xml`) `[verified in game data]`; the human's screenshots show it live.
- **Unknown `[unknown]`:** the exact calls to read the player's standing per faction from the mod (candidates found by name in the DLL: `Faction.get_CurrentReputation`, `Faction.get_PlayerReputation`, `Factions.GetList`/`GetVisibleFactionNames`, `Reputation.GetFactionStanding`, `GetFactionRank`, `GetAttitude`, and `GetTradePerformance`, which suggests trade prices depend on reputation); which factions matter for the current build and zone; whether to export all visible factions or only those with a nearby member.
- **Depends on:** nothing; a read-only C# export plus a console panel. Feeds B8 (merchants: which trades cost standing) and any later rule that avoids rituals or fights.
- **Size (my guess):** research small, implementation small (a `faction_reputation` list in `state.json`, a console tab).
- **Risks:** a long list in `state.json` every turn (export only on change or the top few); the engine's reputation numbers versus the displayed ranks.

## 3. Adding an idea
Write it in your own words first. Then add: what exists today (tag how you know), what you do not know, what it depends on, and a rough size. Do not write an implementation plan until it is Researched.
