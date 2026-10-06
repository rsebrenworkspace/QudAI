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

## 3. Adding an idea
Write it in your own words first. Then add: what exists today (tag how you know), what you do not know, what it depends on, and a rough size. Do not write an implementation plan until it is Researched.
