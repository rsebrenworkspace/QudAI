# R-<n>: <topic> research

- **Backlog item:** B<n> (docs/BACKLOG.md)
- **Branch:** `research/<n>-<slug>` (notes only; nothing from `scratch/` is merged)
- **Owner:** human drives the experiments; Claude Code or Claude (chat) explains and suggests the next step
- **Status:** Not started
- **Budget:** stop after ___ sessions or ___% of the hourly meter, whichever comes first, and write up what you have

## Purpose
Answer specific engine questions so the idea can become a defined task. This card writes **no feature code**.

## Questions (specific and answerable)
1. ...
2. ...

## Methods (pick the cheapest that answers the question)
- **Search the data:** grep the game's XML blueprints (the log lists 15 object files under the game's `StreamingAssets\Base` folder) and conversation/quest XML for the term.
- **Decompile and read:** the probes in `scratch/` (reflection or `dnfile`) against `Assembly-CSharp.dll`. AGENTS.md R1: ask the engine, do not guess.
- **Experiment in game:** hand-feed one command or observe state, as with the manual `COOK_MEAL` test. Throwaway character only.

## How the human and the model work together (the exploration lane)
- Before each experiment, the human says what they expect to happen.
- After it, the model explains what the result means and what it rules in or out, **before** proposing the next step.
- Every command comes with a one-line explanation of what it does.
- A wrong prediction is worth recording: it marks a gap in the mental model.

## Output (all of it)
- **Findings** appended to `ENGINE_INTERNALS.md`, each tagged `[verified in code @commit]`, `[verified in game DATE]`, or `[unverified]`, with the class, method, or file it came from.
- **Open questions** that need a different method.
- **Suggested next card(s)** and a rough size, plus anything that changes the backlog entry (dependencies, risks).
- Update the idea's status in `QudAI_Roadmap.xlsx` (Backlog sheet): Idea -> Researched.

## Constraints
- AGENTS.md rules and git safety rules apply. Probes and dumps stay in `scratch/` (git-ignored); only notes are committed.
- No decompiled game source and no copies of game files in the repo. Short quotes of class and method *names* are fine.
- Do not change the mod or the driver in a research card.

## Result (fill in)
- **Answers (with tags):**
- **What surprised us:**
- **Still unknown:**
- **Next cards:**
- **Model:** ___  **Usage:** meter before: ___  after: ___
