# QudAI: Claude Code entry point

@AGENTS.md

## Claude's role in this repo
Lead/reviewer by default (see `docs/WORKFLOW.md`): write task cards, review diffs, make small high-risk edits,
keep the docs honest. Bulk implementation usually happens in Antigravity.

## Start of every session
1. Read `docs/HANDOFF.md` (current state, open issues, what changed last).
2. Open `docs/CODEMAP.md` before reading any large file; read only the functions the task touches.
   `AIBrainPart.cs` (~3,800 lines) and `brain.py` are expensive to read in full.
3. If the user names a task card (`docs/tasks/T-*.md`), work from that card only.

## End of every session
Update `docs/HANDOFF.md`, then run `python tools/check_docs.py`. Say what is unverified.
