# R-1: Cooking and recipes research

- **Backlog item:** B1 (docs/BACKLOG.md)
- **Branch:** `research/1-cooking-recipes` (notes only)
- **Owner:** human drives the experiments; Claude Code explains and suggests the next step
- **Status:** Not started. Not urgent: Stage 1 comes first. This card exists so the question is ready when you want to explore it.
- **Budget:** two sessions or about 10% of the hourly meter, then write up what you have

## Purpose
Find out how cooking and recipes work in the game, how many recipes exist, which ones change gameplay, and whether the agent can pick a specific recipe without opening the UI. This card writes no feature code.

## What we already know
`COOK_MEAL` in the mod consumes one ingredient, clears hunger, and fires the campfire's after-cooked hook, deliberately skipping the recipe menu (`[verified in code @c50b3c2]`; the in-game recipe menu is the modal that stalled headless play, see `ENGINE_INTERNALS.md` on `Campfire.Cook` and `ShowInventoryActionMenu`). So today meals relieve hunger and nothing more.

## Questions
1. Where are recipes defined (XML blueprints, a C# class, or both)? How many exist?
2. Which recipes have gameplay effects (buffs, stat changes, anything else), and what are those effects?
3. What does the engine need to cook a *specific* recipe from specific ingredients, and can that be called without the UI?
4. How are ingredients represented (the code treats `PreparedCookingIngredient` and `Food` parts)? What makes an ingredient useful for a given recipe?
5. Do effects last long enough to matter, and could any of them hurt (for example a meal that changes combat behavior)?

## Suggested experiments (the human leads; predict first, then run)
1. **Search the data.** Search the game's blueprint XML for words such as `recipe`, `ingredient`, and `meal`. *Predict:* how many files mention them, and whether recipes live in XML at all.
2. **Read the engine.** Using your existing decompile probes, look for how `Campfire` and the cooking code choose and produce a meal. *Predict:* the name of the class that holds the recipe list.
3. **Cook one meal by hand** in the game and watch the message log and your stats. *Predict:* what changes.
4. **Compare** with what `COOK_MEAL` does today (hunger cleared, nothing else). Note the difference.

## Output
Append to `ENGINE_INTERNALS.md`, tagged with how each fact was learned and where it came from. List the recipes that matter if there are few, or the categories if there are many. End with "worth building?" and a rough size, then update the Backlog sheet: Idea -> Researched.

## Constraints
AGENTS.md rules and git safety rules apply. Probes and dumps stay in `scratch/`. No decompiled source or game files in the repo. No changes to the mod or driver.

## Result (fill in)
- **Answers (with tags):**
- **What surprised us:**
- **Still unknown:**
- **Next cards:**
- **Model:** ___  **Usage:** meter before: ___  after: ___
