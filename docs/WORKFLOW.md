# QudAI: Multi-model workflow

Two AI tools work in this repo: **Claude (Claude Code)** and **Antigravity (Gemini)**. They never talk to each other.
The only shared channels are **git**, **this doc set**, and the human. Everything below exists to make that enough.

## 1. Roles

| Who | Default role | Does | Does not |
|---|---|---|---|
| **Claude (lead)** | Planner / reviewer | Writes task cards, reviews diffs and logs, designs hard parts (arbiter, intents, Chronicler), makes small high-risk edits, keeps docs and `check_docs.py` honest | Bulk edits across many files (expensive) |
| **Antigravity (implementer)** | Builder | Implements task cards, runs `dry_run.py`, builds and deploys the mod, does mechanical refactors | Change rules in `AGENTS.md`, or close a task without its acceptance check |
| **Human** | Integrator, runs the game | Runs the game, supplies `Player.log`, decides priorities, merges | |

Roles are defaults. If the lead's budget is healthy, Claude may implement a small task. If a task needs the running game,
the human does that step and records the result.

## 2. Ground rules

1. **One writer per branch.** Never have both tools editing the same branch at once.
2. **One task per branch**, named `task/<id>-<slug>` (e.g. `task/1.1-energy-guard`). Commit before starting a session so anything can be reverted.
3. **Work from a task card** (`docs/tasks/T-<id>-<slug>.md`, copy `docs/tasks/TEMPLATE.md`). No card, no code, except trivial fixes.
4. **Tests and logs settle disagreements**, not opinions and not which model sounds surer. Both tools are wrong sometimes.
5. **Docs change in the same commit as code** (AGENTS.md section 4). Update `docs/HANDOFF.md` last.
6. **Tag confidence**: `[verified in game DATE]`, `[verified in code @commit]`, `[unverified]`.
7. **Never mix a refactor with a behavior change** in one commit. Pure moves (splitting files) get their own commit with no logic edits.

## 3. Task card lifecycle

1. **Lead writes the card** from the roadmap (`QudAI_Roadmap.xlsx`, Tasks sheet; same IDs).
2. **Implementer** creates the branch, works only on the files the card lists, runs the card's verification commands,
   and fills in the card's *Result* section (what changed, what was verified, what was not).
3. **Human** runs any in-game check the card requires and records the outcome on the card.
4. **Lead reviews** `git diff main...task/<id>` plus the logs, checks the card's acceptance list, and either approves or writes
   findings into the card.
5. **Merge**, update `docs/HANDOFF.md`, mark the task Done in the spreadsheet.

If a task fails twice, apply AGENTS.md R1 (Three Strikes): stop patching heuristics, inspect the engine, and write down what was learned in `ENGINE_INTERNALS.md`.

## 4. Session protocols

**Start:** read `AGENTS.md` -> `docs/HANDOFF.md` -> the task card -> only the code the card lists (use `docs/CODEMAP.md`).
**End:** update the card's Result, update `docs/HANDOFF.md`, run `python tools/check_docs.py`, commit.

## 5. Review checklist (lead)

- Does every changed command still spend a turn (R4)? Does anything new read or write state owned by the other side (R2)?
- Any new Python mirror of an engine rule (R3)? Any new 1-step movement heuristic (R6)?
- Does the diff touch files the card did not list? Why?
- Is there a test (multi-turn for loop bugs) or an in-game check recorded?
- Did docs and `check_docs.py` move with the code? Any `[unverified]` claims presented as fact?
- Hard-coded paths, tokens, or decompiled code added? (Block the merge.)

## 6. Usage-budget protocol (Claude plan is shared between chat and Claude Code, and not published as a number)

- Before and after each task, note the usage meter (`/status` in Claude Code, if available in your version). Record it in the card's Result section under *Usage*. After ~5 tasks you will know what a typical task costs.
- Read functions, not files: `docs/CODEMAP.md` first. Ask for diffs, not full-file dumps.
- Keep sessions to one task. Start a fresh session for the next one.
- Put planning and review on Claude, bulk edits on Antigravity, unless the numbers say otherwise.
- If Claude's budget runs out mid-week: Antigravity continues from the task cards; the lead resumes at the next reset and reviews the accumulated branches.

## 7. Prompts that work (copy/paste)

**Claude, writing a card:** "Write a task card for roadmap task 1.4 using docs/tasks/TEMPLATE.md. Read only the functions named in docs/CODEMAP.md that relate to IPC."
**Antigravity, implementing:** "Read AGENTS.md, then docs/tasks/T-1.1-energy-guarantee.md. Implement only that card on a new branch. Do not edit files it does not list. Fill in its Result section when done."
**Claude, reviewing:** "Review `git diff main...task/1.1-energy-guard` against docs/tasks/T-1.1-energy-guarantee.md and the review checklist in docs/WORKFLOW.md. List problems first, then approve or reject."

## 8. Hand-off between tools mid-task

Write down, in the card: what is done, what is half-done, what you tried that failed, and the exact next step. The next tool starts from the card, not from chat history.
