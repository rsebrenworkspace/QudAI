# R-3: quests research

- **Backlog item:** B2 (docs/BACKLOG.md)
- **Branch:** `research/3-quests` (notes only)
- **Owner:** Claude Code read the game files and the DLL on the human's request (2026-10-07); the human drives any in-game experiment
- **Status:** First pass done (data and code reading only; nothing tried in game except what the human saw)

## Purpose
Answer: is questing procedural except for the main story, and is there a process to it? No feature code.

## Answers (tags: `[data]` = game XML, `[code]` = read in `Assembly-CSharp.dll`, `[game]` = seen by the human)

1. **There are two layers.**
   - **Authored quests, 28 of them, 84 steps, in `StreamingAssets/Base/Quests.xml` `[data]`.** Each has a name, a `Level` (1 to 40, the level the game expects), optional faction reputation rewards and an optional C# "system" class. They start and finish from conversations: 32 `StartQuest=` and 53 `CompleteQuest` hooks in `Conversations.xml` `[data]`. The early chain is Joppa's "What's Eating the Watervine?" (level 1: Travel to Red Rock, Find the Vermin, Get a Corpse, Return with the Corpse, **Find Mamon Souldrinker**, Recover the Amaranthine Prism), then Argyve's knickknack quests (levels 3, 5, 7), then the Barathrum and Grit Gate quests (levels 10 to 25), then Tomb of the Eaters (30), and the endgame (levels 35 to 40: Landing Pads, The Golem, We Are Starfreight, Reclamation). "Main story" and these side chains are the same kind of object: hand-written, fixed steps.
   - **Dynamic (procedural) village quests `[code and data]`.** `DynamicQuestFactory` fabricates a template at world generation from the population `Dynamic Village Quests` in `PopulationTables.xml`, a pick-one of three: `FindASiteDynamicQuestTemplate` (go to a generated site), `FindASpecificItemDynamicQuestTemplate` (find or deliver a named item; the item is fabricated with a name mutation from the village's spice) and `InteractWithAnObjectDynamicQuestTemplate` (e.g. pray at a statue; `QuestVerb`/`QuestEvent` properties). Each template fabricates its own quest giver: a named villager of a history-generated village (`VillageDynamicQuestContext`, filters `NamedVillager`, `ParticipantVillager`, and the property **`GivesDynamicQuest`**). A `Village Zero` variant gives a main-quest hook and a "Blank Recoiler" reward. Targets are chosen from generated locations in range of the village and must pass `IsValidQuestDestination` (ruins and the like, tier-checked).
   - There are also two special managers for relics and sultan dungeons (`LocateRelicQuestManager`, `VisitSultanDungeonQuestManager`), generated from the world's history `[code, names only]`.
2. **The process for a dynamic quest `[code]`:** world generation picks a template per village, fabricates giver, item/site/object and reward (`DynamicQuestReward`: reputation, a game object, a choice from a population, another quest, or a village-zero hook); the quest is stored in `DynamicQuestsGameState`; the giver offers it in conversation; accepting adds a `Quest` to the player's log; steps finish on events (`QuestStepFinisher`, `FinishQuestStepWhenSlain`, items with `CompleteQuestOnTaken`); the giver (or a delivery target) closes it and pays the reward.
3. **"I'm looking for work." `[data and code]`** The inherited `BaseConversation` has a choice `AskForWork` for NPCs that are quest signposts (`IfQuestSignpost="Checkpoint"`): it answers "Speak to =questgivers=." and names, with directions, the villagers who have a quest (`QuestSignpost`, `DynamicQuestSignpostConversation`). This is the engine's own pointer to the dynamic quests, and is the cheapest hook for an automated agent: ask it, read who and where.
4. **How a quest is opened by an item `[code]`:** `QuestStarter` (a part on an object, trigger `Taken`, `Created`, `OnScreen`, `EndTurn` or `Equipped`) starts a named quest; 46 blueprints carry the `AddsRep` part and others carry `CompleteQuestOnTaken`, which is why the item scorer already protects them.
5. **Engine API found by name `[code, names only]`:** `QuestsAPI.allQuests`, `Quest.Finish/FinishStep/IsStepFinished/ReadyToTurnIn`, `QuestManager.OnQuestAdded/OnQuestComplete/OnStepComplete`, `QuestLog`, `QuestsStatusScreen`. How to read the player's active quests and steps from the mod was not tried.

## Early quest rewards and the XP curve (added 2026-10-07)
- `[code, decoded IL]` The XP needed to reach level L is `floor(15 x L^3) + 100` (level 1: 0). Level 2: 220, 3: 505, 4: 1,060, 5: 1,975, 6: 3,340, 7: 5,245, 8: 7,780, 9: 11,035, 10: 15,100, 11: 20,065. `[game]` the live character at level 4 with 1,900 XP fits (between 1,060 and 1,975).
- `[data]` Quest steps carry an `XP=` value; the quest's `Level` is the level the game expects. Authored quests by level and total step XP: L1 What's Eating the Watervine? 1,000 (50 Travel to Red Rock, 100 Find the Vermin, 100 Get a Corpse, 750 Return with the Corpse; plus 200 Joppa reputation); L3 Fetch Argyve a Knickknack 75; L3 O Glorious Shekhinah! (Six Day Stilt pilgrimage) 1,500 for one step; L5 Fetch Argyve Another Knickknack 150; L7 Weirdwire Conduit... Eureka! 500 (find 200 feet of wire in the rust wells, east of Joppa); L10 A Canticle for Barathrum 1,250, A Signal in the Noise 1,250, More Than a Willing Spirit 2,000 (+100 Barathrumites reputation); L15 Decoding the Signal 12,750; L20 Raising Indrix 4,250, The Earl of Omonporch 7,000, The Assessment 10,000; L25 Pax Klanq, I Presume? 10,250; L30 Tomb of the Eaters 20,000; L40 If, Then, Else 27,500. Quests with no step XP (A Call to Arms, Grave Thoughts, Landing Pads, the L35-40 story) pay in other ways (reputation, items, systems); item rewards given by conversation were not tabulated.
- Consequence `[derived]`: the watervine quest alone is about two thirds of the XP needed for level 4, and the quests up to level 10 add up to about 7,700 XP, half of what level 10 needs (15,100); the 12,750 XP of Decoding the Signal (level 15) would clear it by itself. For a weak character, travel-only steps (the pilgrimage, Red Rock) pay XP without a fight but cross unknown zones.

## Where the Six Day Stilt is (added 2026-10-07)
- `[data]` World cells are `JoppaWorld.<x>.<y>`, each made of 3 x 3 zones (`.<sx>.<sy>`), plus the stratum `.<z>` (10 is the surface). Joppa is `JoppaWorld.11.22.1.1.10` (`EmbarkModules.xml`; the current character's zones agree). The Stilt's cell is `x=53, y=4`: the pilgrim and teleporter data points at `JoppaWorld.53.4.0.0.10` (the "Ezra recoiler" destination, a loot item worth 65), and `Worlds.xml` defines the cell `TerrainSixDayStilt` as a 3 x 3 block of zones named "the Stiltgrounds" with the Six Day Stilt itself in the middle zone (`.1.1`).
- So it is 42 world cells east and 18 north of Joppa: about 126 zone crossings east and 54 north on foot (zones are 80 x 25 tiles), on the order of 10,000 steps, through regions the character has never seen. `[code]` `TravelToStiltSystem` finishes the step "Make a Pilgrimage to the Six Day Stilt" (1,500 XP) when the player's zone has the terrain `TerrainSixDayStilt`: arriving in the Stiltgrounds is what counts; the Sacred Well offering is flavour in the quest text. `[unverified]` whether the odd trinket is consumed by Argyve's quest.
- World-map or fast travel is on the roadmap (8.1) and not built; the brain walks zone by zone.

## What surprised us
- The authored list is short (28). Most of what looks procedural to a player is the village layer, and it is fixed at world generation, not rolled when you ask.
- The first authored quest includes "Find Mamon Souldrinker", the leader of the Children of Mamon, the faction the human's Water Ritual with Kuyukas pushed to -650 `[game, human]`. That quest step was not read in detail: the quest may now involve a hostile target.

## Still unknown
- Which quest givers exist in the current world, and where (they depend on the generated villages); how the player's quest log is read from the mod; what the quest popups look like (the mod auto-answers Yes to yes/no popups `[verified in code @c50b3c2]`, so an offer could be accepted without a decision).
- Whether "I'm looking for work" appears for Kuyukas or only for checkpoint NPCs.

## Next cards (suggested, not started)
1. R-3b: a read-only export of the player's quest log (`QuestsAPI.allQuests`, steps, status) into `state.json`, plus the console showing it. Small, no behaviour change.
2. R-3c: try "I'm looking for work" at a village by hand and note the exact text and the giver's offer.
3. Only then a design for what the agent does with a quest (accept, route to the target with `NAVIGATE_TO_CELL`, combat).

## Result
- **Model:** Claude Sonnet 5.5 `claude-sonnet-5-5`. **Usage:** not measured.
