# Read the project docs before working

Before doing anything in this repo, read these files in order:

@../../AGENTS.md
@../../docs/HANDOFF.md

Read `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` and `ENGINE_INTERNALS.md` when the task touches those areas
(see the read order in AGENTS.md).

Before you finish a session:
- Update `docs/HANDOFF.md` (what changed, what is unverified, what is broken, next step).
- Update `docs/ARCHITECTURE.md` if you changed a patch, command, or `state.json` field.
- Run `python tools/check_docs.py`.
