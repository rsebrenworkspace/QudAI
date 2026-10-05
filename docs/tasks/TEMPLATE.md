# T-<id>: <short title>

- **Roadmap task:** <id> (QudAI_Roadmap.xlsx, Tasks sheet)
- **Branch:** `task/<id>-<slug>`
- **Owner:** <Antigravity | Claude | You | Both>
- **Status:** Not started | In progress | In review | Done

## Goal
One or two sentences. What is true after this task that is not true now?

## Context
Why this matters. Link the HANDOFF issue number(s) and relevant docs. State confidence tags for any claims.

## Files you may edit
List them. Everything else is out of scope. If you need another file, stop and note it under *Result*.

## Constraints
Relevant rules from AGENTS.md (R1-R8). Anything else the implementer must not do.

## Approach (suggested, not binding)
A sketch. The implementer may deviate but must say why in *Result*.

## Acceptance criteria
- [ ] Concrete, checkable statements.
- [ ] Includes at least one test or in-game check (multi-turn for loop/stall bugs).

## Verification commands
```
python -m py_compile brain.py build_templates.py chronicler.py skill_database.py
python dry_run.py
python tools/check_docs.py
# C# braces check + sync_mod.py deploy if C# changed (see AGENTS.md section 3)
```

## In-game check (human)
What to do in the game, and which log lines or files to look at.

## Result (implementer fills in)
- **What changed:**
- **What was verified (and how):**
- **What was NOT verified:**
- **Surprises / dead ends (also add to docs/DECISIONS.md if reusable):**
- **Usage:** meter before: ___  after: ___  (see WORKFLOW section 6)

## Review (lead fills in)
Findings, approve/reject, follow-ups.
