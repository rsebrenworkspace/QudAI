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
